from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl # HttpUrl was already here
from typing import Dict, Any
from .downloader import get_video_info
from fastapi.middleware.cors import CORSMiddleware # Import CORSMiddleware

app = FastAPI(title="VidGrabber API", version="0.1.0")

# Add CORS middleware
# IMPORTANT: For production, you should restrict allow_origins to your actual frontend domain.
# Example: allow_origins=["https://yourfrontend.com"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for local development
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

class VideoUrlRequest(BaseModel):
    url: HttpUrl # Kept HttpUrl as it was correctly defined

@app.get("/")
async def read_root():
    return {"message": "Welcome to VidGrabber API. Use the /api/download endpoint to process videos."}

@app.post("/api/download")
async def process_video_url(request: VideoUrlRequest) -> Dict[str, Any]:
    video_url_str = str(request.url) # Convert HttpUrl to string for yt-dlp

    video_data = get_video_info(video_url_str)

    if not video_data:
        raise HTTPException(status_code=500, detail="Failed to retrieve video information: No data returned.")

    if video_data.get("error"):
        status_code = 400 # Default to 400 for yt-dlp errors
        if "Unsupported URL" in video_data["error"]:
            status_code = 400
        elif "not found" in video_data["error"].lower() or "unable to extract" in video_data["error"].lower():
            status_code = 404 # More specific for "not found"
        elif "private video" in video_data["error"].lower():
            status_code = 403 # Forbidden for private videos
        # Add more specific error code mappings as needed
        # else: # Potentially a server-side issue with yt-dlp or processing
        #     status_code = 500
        raise HTTPException(status_code=status_code, detail=video_data["error"])

    return video_data

# To run this app (from the backend directory):
# uvicorn app:app --reload
