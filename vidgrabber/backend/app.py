from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import Dict, Any # Added Any for the response model
from .downloader import get_video_info # Relative import

app = FastAPI(title="VidGrabber API", version="0.1.0")

class VideoUrlRequest(BaseModel):
    url: HttpUrl

# More specific response model can be defined later if needed
# class VideoInfoResponse(BaseModel):
#     title: str
#     thumbnail: Optional[HttpUrl] = None
#     formats: list
#     ...

@app.get("/")
async def read_root():
    return {"message": "Welcome to VidGrabber API. Use the /api/download endpoint to process videos."}

@app.post("/api/download")
async def process_video_url(request: VideoUrlRequest) -> Dict[str, Any]: # Return type changed
    """
    Accepts a video URL, fetches video information using yt-dlp,
    and returns it as a JSON response.
    """
    video_url_str = str(request.url)

    # Call the downloader function
    video_data = get_video_info(video_url_str)

    if not video_data:
        raise HTTPException(status_code=500, detail="Failed to retrieve video information: No data returned.")

    if video_data.get("error"):
        # Determine appropriate status code based on error type if possible
        # For now, using 400 for client-related errors (e.g., bad URL) or 500 for server-side issues
        status_code = 400 if "Unsupported URL" in video_data["error"] or "not found" in video_data["error"].lower() else 500
        raise HTTPException(status_code=status_code, detail=video_data["error"])

    return video_data

# To run this app (from the backend directory, assuming your main file is app.py):
# uvicorn vidgrabber.backend.app:app --reload
# (Adjust if your project structure or run command differs)
# Or, if in the 'vidgrabber' directory:
# python -m uvicorn backend.app:app --reload --app-dir .
