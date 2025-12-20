"""YouTube Integration Module.

This module provides utilities for interacting with YouTube channels and videos
using yt-dlp. It handles channel metadata fetching, video listing, and data
validation for the YouTube page.
"""

import re
from datetime import datetime
from typing import Optional


class YouTubeManager:
    """Manages yt-dlp operations for channel and video fetching."""

    @staticmethod
    def get_channel_info(channel_url_or_handle: str) -> dict:
        """Fetch channel metadata using yt-dlp.

        Parameters
        ----------
        channel_url_or_handle : str
            YouTube channel URL, handle, or channel ID

        Returns
        -------
        dict
            Channel metadata including name, channel_id, thumbnail, description,
            subscriber_count, video_count
        """
        import yt_dlp

        # For channel info, we just need metadata, not the video list
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': 'in_playlist',  # Extract just the channel metadata
            'socket_timeout': 10,
            'retries': 1,
            'playlistend': 0,  # Don't fetch any videos for channel info
        }

        try:
            # Ensure we're fetching the main channel page
            if '@' in channel_url_or_handle and '/videos' not in channel_url_or_handle:
                channel_url = f"{channel_url_or_handle}/videos"
            elif 'youtube.com/channel/' in channel_url_or_handle and '/videos' not in channel_url_or_handle:
                channel_url = f"{channel_url_or_handle}/videos"
            else:
                channel_url = channel_url_or_handle

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(channel_url, download=False)

                return {
                    'name': info.get('title', info.get('uploader', 'Unknown')),
                    'channel_id': info.get('channel_id', ''),
                    'channel_url': info.get('channel_url', ''),
                    'channel_handle': info.get('uploader_id', ''),
                    'thumbnail_url': info.get('thumbnail', ''),
                    'description': info.get('description', ''),
                    'subscriber_count': info.get('subscriber_count', 0) or 0,
                    'video_count': info.get('playlist_count', 0) or 0,
                }
        except Exception as e:
            raise ValueError(f"Failed to fetch channel info: {str(e)}")

    # @staticmethod
    # def get_channel_videos(channel_url_or_handle: str, max_results: int = 50) -> list:
    #     """Fetch recent videos from channel.

    #     Parameters
    #     ----------
    #     channel_url_or_handle : str
    #         YouTube channel URL, handle, or channel ID
    #     max_results : int
    #         Maximum number of videos to fetch

    #     Returns
    #     -------
    #     list
    #         List of video dictionaries with video_id, title, thumbnail,
    #         duration, upload_date, view_count, description, url
    #     """
    #     import yt_dlp

    #     ydl_opts = {
    #         'quiet': True,
    #         'no_warnings': True,
    #         'extract_flat': 'in_playlist',  # Extract video entries from playlist
    #         'playlistend': max_results,
    #         'socket_timeout': 10,
    #         'retries': 1,
    #     }

    #     try:
    #         # Ensure we're fetching the videos tab specifically
    #         if '@' in channel_url_or_handle and '/videos' not in channel_url_or_handle:
    #             channel_url = f"{channel_url_or_handle}/videos"
    #         elif 'youtube.com/channel/' in channel_url_or_handle and '/videos' not in channel_url_or_handle:
    #             channel_url = f"{channel_url_or_handle}/videos"
    #         elif 'youtube.com/c/' in channel_url_or_handle and '/videos' not in channel_url_or_handle:
    #             channel_url = f"{channel_url_or_handle}/videos"
    #         else:
    #             channel_url = channel_url_or_handle

    #         with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    #             info = ydl.extract_info(channel_url, download=False)

    #             # Handle both playlist and channel extraction
    #             entries = info.get('entries', [])

    #             videos = []
    #             for entry in entries:
    #                 if not entry:
    #                     continue

    #                 # Skip if this is a playlist/tab entry instead of a video
    #                 if entry.get('_type') == 'playlist':
    #                     continue

    #                 # Only process actual video entries
    #                 if 'id' not in entry or 'title' not in entry:
    #                     continue

    #                 # Filter out special playlist names that aren't videos
    #                 title = entry.get('title', '')
    #                 if title in ['Videos', 'Shorts', 'Live', 'Playlists', 'Community', 'Channels', 'About']:
    #                     continue

    #                 video_id = entry.get('id', '')
    #                 if not video_id:
    #                     continue

    #                 videos.append({
    #                     'video_id': video_id,
    #                     'title': title,
    #                     'thumbnail_url': entry.get('thumbnail', entry.get('thumbnails', [{}])[-1].get('url', '') if entry.get('thumbnails') else ''),
    #                     'duration': entry.get('duration', 0) or 0,
    #                     'upload_date': entry.get('upload_date', ''),
    #                     'view_count': entry.get('view_count', 0) or 0,
    #                     'description': entry.get('description', ''),
    #                     'url': entry.get('url', f"https://youtube.com/watch?v={video_id}"),
    #                 })

    #                 # Stop when we have enough videos
    #                 if len(videos) >= max_results:
    #                     break

    #             return videos
    #     except Exception as e:
    #         raise ValueError(f"Failed to fetch channel videos: {str(e)}")

    @staticmethod
    def get_video_info(video_url: str) -> dict:
        """Fetch single video information.

        Parameters
        ----------
        video_url : str
            YouTube video URL

        Returns
        -------
        dict
            Video metadata
        """
        import yt_dlp

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)

                return {
                    'video_id': info.get('id', ''),
                    'title': info.get('title', 'Unknown'),
                    'thumbnail_url': info.get('thumbnail', ''),
                    'duration': info.get('duration', 0) or 0,
                    'upload_date': info.get('upload_date', ''),
                    'view_count': info.get('view_count', 0) or 0,
                    'description': info.get('description', ''),
                    'url': info.get('webpage_url', video_url),
                    'channel': info.get('channel', ''),
                    'channel_id': info.get('channel_id', ''),
                }
        except Exception as e:
            raise ValueError(f"Failed to fetch video info: {str(e)}")

    @staticmethod
    def validate_channel_url(url_or_handle: str) -> tuple[bool, str]:
        """Validate and normalize YouTube channel URL/handle.

        Parameters
        ----------
        url_or_handle : str
            YouTube channel URL, handle, or channel ID

        Returns
        -------
        tuple[bool, str]
            (is_valid, normalized_url)
        """
        if not url_or_handle:
            return False, ""

        url_or_handle = url_or_handle.strip()

        # Handle @username format
        if url_or_handle.startswith('@'):
            return True, f"https://youtube.com/{url_or_handle}"

        # Handle channel ID format
        if re.match(r'^UC[\w-]{22}$', url_or_handle):
            return True, f"https://youtube.com/channel/{url_or_handle}"

        # Handle full URLs
        youtube_patterns = [
            r'(?:https?://)?(?:www\.)?youtube\.com/(?:c/|channel/|user/|@)[\w-]+',
            r'(?:https?://)?(?:www\.)?youtube\.com/@[\w-]+',
        ]

        for pattern in youtube_patterns:
            if re.match(pattern, url_or_handle):
                if not url_or_handle.startswith('http'):
                    url_or_handle = 'https://' + url_or_handle
                return True, url_or_handle

        return False, url_or_handle

    @staticmethod
    def download_video(video_url: str, output_path: str, progress_callback=None):
        """Download video with progress tracking.

        Parameters
        ----------
        video_url : str
            YouTube video URL
        output_path : str
            Output file path
        progress_callback : callable, optional
            Callback function for progress updates
        """
        import yt_dlp

        def progress_hook(d):
            if progress_callback and d['status'] == 'downloading':
                if 'total_bytes' in d:
                    percent = d['downloaded_bytes'] / d['total_bytes'] * 100
                    progress_callback(percent)

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'outtmpl': output_path,
            'progress_hooks': [progress_hook] if progress_callback else [],
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
        except Exception as e:
            raise ValueError(f"Failed to download video: {str(e)}")

    @staticmethod
    def format_duration(seconds: int) -> str:
        """Format duration in seconds to HH:MM:SS or MM:SS.

        Parameters
        ----------
        seconds : int
            Duration in seconds

        Returns
        -------
        str
            Formatted duration string
        """
        if seconds < 0:
            return "00:00"

        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"

    @staticmethod
    def format_upload_date(date_str: str) -> str:
        """Format upload date string to readable format.

        Parameters
        ----------
        date_str : str
            Date string in YYYYMMDD format

        Returns
        -------
        str
            Formatted date string
        """
        if not date_str or len(date_str) != 8:
            return ""

        try:
            date_obj = datetime.strptime(date_str, '%Y%m%d')
            return date_obj.strftime('%Y-%m-%d')
        except ValueError:
            return date_str

    @staticmethod
    def format_view_count(count: int) -> str:
        """Format view count to readable string.

        Parameters
        ----------
        count : int
            View count

        Returns
        -------
        str
            Formatted view count string (e.g., "1.2M", "45K")
        """
        if count < 1000:
            return str(count)
        elif count < 1000000:
            return f"{count/1000:.1f}K"
        else:
            return f"{count/1000000:.1f}M"
