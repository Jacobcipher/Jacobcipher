import yt_dlp
from yt_dlp.utils import DownloadError, ExtractorError
import re # For cleaning filename
import logging

# Configure basic logging for this module if not already configured by a higher-level module
# This assumes that if a root logger is configured, this will just use it.
logger = logging.getLogger(__name__)
if not logger.handlers: # Check if handlers are already configured
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def get_video_info(video_url: str):
    """
    Uses yt-dlp to fetch metadata and URLs for the best video and audio streams
    suitable for muxing.
    Returns a dictionary with title, thumbnail, video_url, audio_url, and suggested_filename.
    """

    # Format selection:
    # - 'bv*[ext=mp4]' : Best video-only stream with mp4 extension.
    # - 'ba[ext=m4a]' : Best audio-only stream with m4a extension (AAC).
    # - '/b[ext=mp4]' : Fallback to best overall stream with mp4 extension (might be muxed).
    # - 'bv*+ba' : Fallback to best video-only and best audio-only of any extension.
    # - '/b' : Final fallback to best overall of any extension.
    # Prioritize mp4/m4a for wider compatibility and because FFmpeg handles them well.
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'format': 'bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b',
        # 'format_sort': ['res,fps,hdr:12,vcodec:vp9.2,channels,acodec,size,tbr,asr'], # yt-dlp default sort
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)

            title = info.get("title", "Untitled_Video")
            # Clean the title to create a safe filename
            safe_title = re.sub(r'[\/*?:"<>|]', "", title) # Remove illegal characters
            safe_title = re.sub(r'\s+', '_', safe_title) # Replace spaces with underscores
            suggested_filename = f"{safe_title[:100]}.mp4" # Limit length and add .mp4 extension

            video_stream_url = None
            audio_stream_url = None

            # Requested formats are those chosen by yt-dlp based on the format string.
            # If 'requested_formats' is present, it means yt-dlp selected separate video and audio.
            if info.get('requested_formats'):
                video_format = info['requested_formats'][0] # First one is usually video
                audio_format = info['requested_formats'][1] # Second one is usually audio

                # Check if they are indeed video and audio respectively
                if video_format.get('vcodec') != 'none' and video_format.get('acodec') == 'none':
                    video_stream_url = video_format.get('url')
                if audio_format.get('acodec') != 'none' and audio_format.get('vcodec') == 'none':
                    audio_stream_url = audio_format.get('url')

                # Fallback if the order is swapped or if one is muxed and the other is audio
                if not video_stream_url and audio_format.get('vcodec') != 'none' and audio_format.get('acodec') == 'none':
                     video_stream_url = audio_format.get('url')
                if not audio_stream_url and video_format.get('acodec') != 'none' and video_format.get('vcodec') == 'none':
                     audio_stream_url = video_format.get('url')


            # If 'requested_formats' isn't there, or if we couldn't get both URLs from it,
            # it might be that yt-dlp selected a single, already muxed format.
            # Or, it might be a single video-only or audio-only stream if that's all that matched.
            if not (video_stream_url and audio_stream_url):
                # Check if the main 'url' entry is for a pre-muxed file (has both codecs)
                if info.get('url') and info.get('vcodec') != 'none' and info.get('acodec') != 'none':
                    # This is a pre-muxed format, we can't use it for muxing with a separate audio.
                    # This part of the logic indicates that we might need to adjust format selection
                    # or downloader logic if we *only* want to mux.
                    # For now, if we hit this, it means our format selector gave us something already muxed.
                    # This isn't ideal for the muxing flow, but we'll flag it.
                    # To strictly enforce separate streams, the format selector would be just 'bv*+ba'.
                    # Let's assume for now the goal is to get *some* video and audio, even if one is from a muxed source
                    # and the other is a separate audio track (less common).
                    # The chosen format string 'bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b' tries to get separate streams first.
                    # If it results in a single format in `info['formats']` that is muxed, then `info['url']` will be that.

                    # If we got here, it means the primary format selection likely resulted in a single (possibly muxed) file.
                    # This is a simplification for now. A more robust solution would iterate through info.get('formats')
                    # to find distinct video and audio if `requested_formats` is not as expected.
                    # Given the format string, `requested_formats` *should* be populated if distinct streams are chosen.
                    # If not, it implies `yt-dlp` chose one of the fallback single formats (e.g., `/b[ext=mp4]`).
                     return {
                        "error": "Could not reliably identify separate video and audio streams for muxing. The selected format might be a single file.",
                        "title": title,
                        "thumbnail": info.get("thumbnail"),
                        "suggested_filename": suggested_filename,
                        "video_url": info.get('url') if info.get('vcodec') != 'none' else None, # If it's a single file, use its URL as video
                        "audio_url": None # No separate audio URL in this case
                    }


            if not video_stream_url or not audio_stream_url:
                # This can happen if the video is audio-only, video-only, or format selection failed
                error_message = "Could not retrieve separate video and audio stream URLs. The content might be audio-only, video-only, or the requested formats are unavailable."
                if info.get('vcodec') == 'none' and info.get('acodec') != 'none':
                    error_message = "The content appears to be audio-only."
                elif info.get('acodec') == 'none' and info.get('vcodec') != 'none':
                    error_message = "The content appears to be video-only (no audio track)."

                return {"error": error_message, "title": title, "thumbnail": info.get("thumbnail")}

            return {
                "title": title,
                "thumbnail": info.get("thumbnail"),
                "video_url": video_stream_url,
                "audio_url": audio_stream_url,
                "suggested_filename": suggested_filename,
                "original_url": video_url # Keep original_url for context
            }

    except ExtractorError as e: # yt-dlp specific error for when it can't process a URL
        logger.error(f"ExtractorError for {video_url}: {e}")
        return {"error": f"Failed to process URL: {str(e)}", "original_url": video_url} # type: ignore
    except DownloadError as e: # More general yt-dlp download related error
        logger.error(f"DownloadError for {video_url}: {e}")
        return {"error": f"Failed to retrieve video information: {str(e)}", "original_url": video_url}
    except Exception as e:
        logger.error(f"An unexpected error occurred in get_video_info for {video_url}: {e}", exc_info=True)
        return {"error": f"An unexpected error occurred while processing video details.", "original_url": video_url}

if __name__ == '__main__':
    # logger = yt_dlp.utils. جوړول شوي_لاګر('TestDownloader') # type: ignore
    # logger.setLevel(yt_dlp.utils. варіانونه.ERROR) # type: ignore

    # test_urls = [
    #     "https://www.youtube.com/watch?v=dQw4w9WgXcQ", # Standard video
    #     "https://www.youtube.com/shorts/TuAckwPV1eI",  # YouTube Short
    #     "https://www.youtube.com/watch?v=zFhfksjf_mY" # Music video, often has good m4a
    # ]
    # for url in test_urls:
    #     print(f"\nTesting URL: {url}")
    #     data = get_video_info(url)
    #     if data.get("error"):
    #         print(f"  Error: {data['error']}")
    #     else:
    #         print(f"  Title: {data.get('title')}")
    #         print(f"  Suggested Filename: {data.get('suggested_filename')}")
    #         print(f"  Thumbnail: {data.get('thumbnail')}")
    #         print(f"  Video URL: {data.get('video_url') is not None}")
    #         print(f"  Audio URL: {data.get('audio_url') is not None}")
    pass
