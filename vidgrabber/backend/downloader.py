import yt_dlp
from yt_dlp.utils import DownloadError

def get_video_info(video_url: str):
    """
    Uses yt-dlp to fetch video metadata.
    Returns a dictionary with title, thumbnail, and filtered formats.
    """
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)

            raw_formats = []
            if info.get('formats'):
                for f in info['formats']:
                    raw_formats.append({
                        'format_id': f.get('format_id'),
                        'ext': f.get('ext'),
                        'resolution': f.get('resolution') or f.get('format_note') or f.get('height'), # include height as fallback for resolution
                        'fps': f.get('fps'),
                        'filesize_approx': f.get('filesize') or f.get('filesize_approx'),
                        'url': f.get('url'),
                        'format_note': f.get('format_note'),
                        'acodec': f.get('acodec'),
                        'vcodec': f.get('vcodec'),
                        'width': f.get('width'),
                        'height': f.get('height'),
                        'tbr': f.get('tbr'), # Total bitrate
                    })

            # Filter formats:
            # 1. Must have a URL.
            # 2. Prefer formats with both video and audio.
            # 3. Fallback to video-only if no combined formats are easily found (less ideal for direct download).

            filtered_formats = []
            if raw_formats:
                # Priority 1: Muxed MP4 formats (often good quality, widely compatible)
                # Common YouTube format IDs for decent quality muxed mp4: 18 (360p), 22 (720p)
                priority_muxed_ids = ['18', '22']
                for fmt_id in priority_muxed_ids:
                    for f in raw_formats:
                        if f['format_id'] == fmt_id and f.get('url') and \
                           (f.get('vcodec') and f['vcodec'] != 'none') and \
                           (f.get('acodec') and f['acodec'] != 'none') and \
                           f['ext'] == 'mp4':
                            if not any(existing_f['format_id'] == f['format_id'] for existing_f in filtered_formats):
                                filtered_formats.append(f)

                # Priority 2: Other formats with both video and audio, preferring mp4 and webm
                for f in raw_formats:
                    if f.get('url') and \
                       (f.get('vcodec') and f['vcodec'] != 'none') and \
                       (f.get('acodec') and f['acodec'] != 'none') and \
                       f['ext'] in ['mp4', 'webm']:
                        # Avoid adding duplicates if already picked by priority_muxed_ids
                        if not any(existing_f['format_id'] == f['format_id'] for existing_f in filtered_formats):
                            filtered_formats.append(f)

                # Fallback / Augmentation: If very few (or no) combined formats found,
                # consider adding some high-quality video-only and audio-only if direct links are the goal.
                # For this iteration, we'll keep it simple and focus on combined first.
                # If filtered_formats is still empty, add any format that has a URL and a resolution.
                if not filtered_formats:
                    for f in raw_formats:
                        if f.get('url') and (f.get('resolution') or (f.get('width') and f.get('height'))):
                             if not any(existing_f['format_id'] == f['format_id'] for existing_f in filtered_formats):
                                filtered_formats.append(f) # This might include video-only or audio-only

            # Sort by resolution (height) and then by filetype (mp4 first)
            if filtered_formats:
                filtered_formats.sort(key=lambda x: (
                    int(x.get('height', 0) or 0),
                    x.get('ext') == 'mp4'
                ), reverse=True)


            return {
                "title": info.get("title", "N/A"),
                "thumbnail": info.get("thumbnail", None),
                "uploader": info.get("uploader", None),
                "duration_string": info.get("duration_string", None),
                "formats": filtered_formats,
                "original_url": video_url,
            }

    except DownloadError as e:
        print(f"Error downloading video info: {e}")
        return {"error": str(e), "original_url": video_url}
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        # It's good to log the full traceback here in a real app for debugging
        # import traceback
        # print(traceback.format_exc())
        return {"error": f"An unexpected error occurred while processing video. Details: {str(e)}", "original_url": video_url}

if __name__ == '__main__':
    # Example usage (for testing this script directly)
    # test_urls = [
    #     "https://www.youtube.com/shorts/TuAckwPV1eI",
    #     "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    #     # "https://www.facebook.com/Meta/videos/268420336069880/" # Requires login or different handling often
    # ]
    # for test_url in test_urls:
    #     print(f"\nFetching info for: {test_url}")
    #     video_data = get_video_info(test_url)
    #     if video_data and not video_data.get('error'):
    #         print(f"Title: {video_data.get('title')}")
    #         # print(f"Thumbnail: {video_data.get('thumbnail')}")
    #         # print(f"Duration: {video_data.get('duration_string')}")
    #         print("Formats Found:")
    #         if video_data.get("formats"):
    #             for fmt in video_data.get("formats", []):
    #                 print(f"  - ID: {fmt.get('format_id')}, Ext: {fmt.get('ext')}, Resolution: {fmt.get('resolution')}, VCodec: {fmt.get('vcodec')}, ACodec: {fmt.get('acodec')}, TBR: {fmt.get('tbr')}, Filesize: {fmt.get('filesize_approx')}")
    #         else:
    #             print("  No formats returned after filtering.")
    #     else:
    #         print(f"Could not fetch video data: {video_data.get('error')}")
    pass
