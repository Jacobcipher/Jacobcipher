import os
import uuid
import requests # We'll add this to requirements.txt later
import subprocess
import logging
from pathlib import Path

# Configure basic logging for this module
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

FFMPEG_EXE_PATH = "C:\ffmpeg\bin\ffmpeg.exe" # Windows path, ensure FFmpeg is here

# Define a base directory for temporary files within the backend folder
# This assumes processor.py is in vidgrabber/backend/
TEMP_DIR_BASE = Path(__file__).resolve().parent / "temp_files"

def generate_temp_filepath(prefix: str = "stream", extension: str = ".mp4") -> Path:
    """
    Generates a unique temporary filepath within the backend/temp_files directory.
    Ensures the temp_files directory exists.
    """
    os.makedirs(TEMP_DIR_BASE, exist_ok=True)
    unique_id = uuid.uuid4()
    filename = f"{prefix}_{unique_id}{extension}"
    return TEMP_DIR_BASE / filename

def download_stream(url: str, output_path: Path) -> bool:
    """
    Downloads content from a URL and saves it to output_path.
    Uses streaming to handle potentially large files.
    Returns True on success, False on failure.
    """
    logger.info(f"Attempting to download stream from {url} to {output_path}")
    try:
        with requests.get(url, stream=True, timeout=30) as r: # Added timeout
            r.raise_for_status()  # Will raise an HTTPError for bad responses (4XX, 5XX)
            with open(output_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        logger.info(f"Successfully downloaded to {output_path}")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to download {url}. Error: {e}")
        return False
    except IOError as e:
        logger.error(f"Failed to write to {output_path}. Error: {e}")
        return False

def run_ffmpeg_mux(video_path: Path, audio_path: Path, output_path: Path, ffmpeg_exe_path: str = FFMPEG_EXE_PATH) -> bool:
    """
    Muxes video and audio streams into an output file using FFmpeg.
    Returns True on success, False on failure.
    """
    if not Path(ffmpeg_exe_path).exists():
        logger.error(f"FFmpeg executable not found at {ffmpeg_exe_path}. Please check the path.")
        return False
    if not video_path.exists():
        logger.error(f"Input video file not found: {video_path}")
        return False
    if not audio_path.exists():
        logger.error(f"Input audio file not found: {audio_path}")
        return False

    command = [
        ffmpeg_exe_path,
        '-i', str(video_path),
        '-i', str(audio_path),
        '-c:v', 'copy',          # Copy video stream without re-encoding
        '-c:a', 'copy',          # Copy audio stream without re-encoding
        '-y',                    # Overwrite output file if it exists
        str(output_path)
    ]

    logger.info(f"Running FFmpeg command: {' '.join(command)}")
    try:
        process = subprocess.run(command, capture_output=True, text=True, check=False, timeout=300) # Added timeout, check=False
        if process.returncode == 0:
            logger.info(f"FFmpeg muxing successful: {output_path}")
            return True
        else:
            logger.error(f"FFmpeg failed for {output_path}.")
            logger.error(f"FFmpeg stdout: {process.stdout}")
            logger.error(f"FFmpeg stderr: {process.stderr}")
            return False
    except subprocess.TimeoutExpired:
        logger.error(f"FFmpeg command timed out for {output_path}.")
        return False
    except Exception as e: # Catch any other exception during subprocess.run
        logger.error(f"An unexpected error occurred while running FFmpeg: {e}")
        return False


def cleanup_files(paths: list) -> None:
    """
    Deletes a list of files. Logs errors if deletion fails.
    Accepts list of Path objects or strings.
    """
    for file_path in paths:
        try:
            p = Path(file_path) # Ensure it's a Path object
            if p.exists():
                p.unlink()
                logger.info(f"Successfully deleted temporary file: {p}")
            else:
                logger.info(f"Temporary file not found for deletion (already deleted?): {p}")
        except OSError as e: # Catching OSError for file deletion issues
            logger.error(f"Error deleting temporary file {file_path}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error deleting file {file_path}: {e}")

if __name__ == '__main__':
    # Basic test for generate_temp_filepath
    # Create a dummy temp_files directory at the same level as processor.py for this test
    # This is just for a direct `python processor.py` run, actual app will use the path relative to __file__

    # test_temp_dir = Path("temp_files") # For direct script run test
    # os.makedirs(test_temp_dir, exist_ok=True)
    # temp_video_path = generate_temp_filepath(prefix="test_video", extension=".mp4")
    # temp_audio_path = generate_temp_filepath(prefix="test_audio", extension=".m4a")
    # temp_output_path = generate_temp_filepath(prefix="test_output", extension=".mp4")
    # print(f"Generated video path: {temp_video_path}")
    # print(f"Generated audio path: {temp_audio_path}")
    # print(f"Generated output path: {temp_output_path}")

    # Note: download_stream and run_ffmpeg_mux would require actual URLs and files for testing here.
    # print("\nTo test download_stream and run_ffmpeg_mux, you would need:")
    # print("1. Valid stream URLs.")
    # print("2. FFmpeg installed and FFMPEG_EXE_PATH correctly set.")
    # print("3. Actual video and audio files created from those URLs.")

    # Example cleanup test
    # cleanup_files([temp_video_path, temp_audio_path, temp_output_path, "non_existent_file.txt"])
    pass
