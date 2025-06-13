from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel, HttpUrl
from typing import Dict, Any
from pathlib import Path
from fastapi.responses import FileResponse
import logging # Import logging

# Assuming downloader.py and processor.py are in the same directory (backend)
from .downloader import get_video_info
from .processor import generate_temp_filepath, download_stream, run_ffmpeg_mux, cleanup_files, FFMPEG_EXE_PATH

# Configure basic logging for the app
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(module)s - %(message)s')
logger = logging.getLogger(__name__)

# Check if FFMPEG_EXE_PATH is the placeholder and try to find ffmpeg in PATH if so
effective_ffmpeg_path = FFMPEG_EXE_PATH
if FFMPEG_EXE_PATH == "C:\\ffmpeg\\bin\\ffmpeg.exe" or not Path(FFMPEG_EXE_PATH).exists():
    logger.info(f"Default FFMPEG_EXE_PATH '{FFMPEG_EXE_PATH}' is placeholder or not found. Attempting to find ffmpeg in PATH.")
    import shutil
    found_ffmpeg = shutil.which("ffmpeg")
    if found_ffmpeg:
        logger.info(f"Found ffmpeg in PATH: {found_ffmpeg}")
        effective_ffmpeg_path = found_ffmpeg
    else:
        logger.warning("ffmpeg not found in PATH. Muxing will likely fail unless FFMPEG_EXE_PATH is correctly set manually or ffmpeg is installed and in PATH.")
        # effective_ffmpeg_path remains the placeholder, run_ffmpeg_mux will handle its non-existence if called

app = FastAPI(title="VidGrabber API", version="0.2.0") # Version bump

# Add CORS middleware (from previous step, assuming it's needed for frontend)
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for local development
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

class VideoUrlRequest(BaseModel):
    url: HttpUrl

@app.get("/")
async def read_root():
    return {"message": "Welcome to VidGrabber API. Use POST /api/process_and_download_video to process videos."}

# Old endpoint - can be deprecated or removed later if not needed
@app.post("/api/download")
async def old_process_video_url(request: VideoUrlRequest) -> Dict[str, Any]:
    logger.warning("Accessed deprecated /api/download endpoint. Use /api/process_and_download_video.")
    # This endpoint is superseded by /api/process_and_download_video for muxing.
    # Returning the raw info as before, but with a deprecation warning in logs / potentially in response.
    video_url_str = str(request.url)
    video_data = get_video_info(video_url_str) # This now returns video/audio URLs for muxing
    if not video_data:
        raise HTTPException(status_code=500, detail="Failed to retrieve video information: No data returned.")
    if video_data.get("error"):
        status_code = 400
        if "Unsupported URL" in video_data["error"]: status_code = 400
        elif "not found" in video_data["error"].lower() or "unable to extract" in video_data["error"].lower(): status_code = 404
        elif "private video" in video_data["error"].lower(): status_code = 403
        raise HTTPException(status_code=status_code, detail=video_data["error"])
    return video_data


@app.post("/api/process_and_download_video")
async def process_and_download_video(request: VideoUrlRequest, background_tasks: BackgroundTasks):
    """
    Processes a video URL: downloads separate video & audio, muxes them,
    and returns the final video file for download.
    Temporary files are cleaned up in the background.
    """
    video_url_str = str(request.url)
    logger.info(f"Processing request for URL: {video_url_str}")

    # --- 1. Get Video Info (Stream URLs, Title, etc.) ---
    video_info = get_video_info(video_url_str)
    if video_info.get("error"):
        logger.error(f"Failed to get video info: {video_info['error']}")
        # Use status codes from downloader if available and more specific
        status_code = 400
        if "Unsupported URL" in video_info["error"]: status_code = 400
        elif "not found" in video_info["error"].lower() or "unable to extract" in video_info["error"].lower(): status_code = 404
        elif "private video" in video_info["error"].lower(): status_code = 403
        raise HTTPException(status_code=status_code, detail=f"Failed to get video info: {video_info['error']}")

    video_stream_url = video_info.get("video_url")
    audio_stream_url = video_info.get("audio_url")
    suggested_filename = video_info.get("suggested_filename", "downloaded_video.mp4")

    if not video_stream_url or not audio_stream_url:
        logger.error(f"Could not find both video and audio streams. Video URL: {video_stream_url}, Audio URL: {audio_stream_url}")
        raise HTTPException(status_code=404, detail="Could not find separate video and audio streams for muxing. The video might be video-only, audio-only, or suitable formats are unavailable.")

    logger.info(f"Found video stream: {'Available' if video_stream_url else 'Not Available'}")
    logger.info(f"Found audio stream: {'Available' if audio_stream_url else 'Not Available'}")

    # --- 2. Define Temporary File Paths ---
    temp_video_path = generate_temp_filepath(prefix="vid", extension=".mp4") # Assuming mp4 video
    temp_audio_path = generate_temp_filepath(prefix="aud", extension=".m4a") # Assuming m4a audio
    muxed_output_path = generate_temp_filepath(prefix="muxed_", extension=".mp4")

    files_to_cleanup = [temp_video_path, temp_audio_path, muxed_output_path]

    try:
        # --- 3. Download Video Stream ---
        logger.info(f"Downloading video to {temp_video_path}")
        if not download_stream(video_stream_url, temp_video_path):
            logger.error("Failed to download video stream.")
            raise HTTPException(status_code=500, detail="Failed to download video stream.")

        # --- 4. Download Audio Stream ---
        logger.info(f"Downloading audio to {temp_audio_path}")
        if not download_stream(audio_stream_url, temp_audio_path):
            logger.error("Failed to download audio stream.")
            raise HTTPException(status_code=500, detail="Failed to download audio stream.")

        # --- 5. Mux Video and Audio ---
        logger.info(f"Muxing video and audio to {muxed_output_path} using FFmpeg at {effective_ffmpeg_path}")
        if not run_ffmpeg_mux(temp_video_path, temp_audio_path, muxed_output_path, ffmpeg_exe_path=effective_ffmpeg_path):
            logger.error("Failed to mux video and audio.")
            raise HTTPException(status_code=500, detail="Failed to process video (muxing error). Check server logs for FFmpeg details.")

        # --- 6. Schedule Cleanup & Return File ---
        logger.info(f"Muxing successful. Preparing file response for {muxed_output_path}")
        # Add task to cleanup files *after* response is sent
        background_tasks.add_task(cleanup_files, files_to_cleanup)

        return FileResponse(
            path=str(muxed_output_path), # Ensure path is string for FileResponse
            media_type='video/mp4',
            filename=suggested_filename
        )

    except HTTPException: # Re-raise HTTPExceptions directly
        # Cleanup files if an HTTPException occurred during the process before FileResponse
        # Note: if muxing failed and raised HTTPException, files_to_cleanup includes muxed_output_path which might not exist.
        # cleanup_files handles non-existent files gracefully.
        background_tasks.add_task(cleanup_files, files_to_cleanup)
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred during video processing: {e}", exc_info=True)
        background_tasks.add_task(cleanup_files, files_to_cleanup) # Try to cleanup before raising
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {str(e)}")

# Ensure to import Path from pathlib at the top
# from pathlib import Path (already there)
