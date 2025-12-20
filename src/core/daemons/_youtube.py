"""YouTube Daemon for managing YouTube channel and video operations.

This daemon provides asynchronous YouTube functionality including channel video fetching using yt-dlp.
"""

import asyncio
import json
from typing import Optional, Dict

from utils import jsn
from utils.helpers import display_message
from utils import sql


class YouTubeDaemon:
    """Daemon for managing YouTube channel operations and auto-sync."""

    def __init__(self, system):
        """Initialize YouTube daemon.

        Parameters
        ----------
        system : object
            System object containing database connection and configuration
        """
        self.system = system
        self._running = False
        self._task_group: Optional[asyncio.TaskGroup] = None
        self._sync_tasks: Dict[int, asyncio.Task] = {}
        # self.db_connector = system.db_connector

        # yt-dlp options for channel info
        self.channel_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': 'in_playlist',
            'socket_timeout': 10,
            'retries': 1,
            'playlistend': 0,
        }

        # yt-dlp options for video listing
        self.video_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': 'in_playlist',
            'socket_timeout': 10,
            'retries': 1,
        }

    async def start(self):
        """Start the YouTube daemon and initialize auto-sync tasks."""
        self._running = True
        return

        while True:
            # get all channels from youtube_channels table
            channels = sql.get_results("""
                SELECT id, name
                FROM youtube_channels
            """, return_type='dict')

            for id, name in channels.items():
                await self.update_channel_data(id, name)

            await asyncio.sleep(1)
    
    async def update_channel_data(self, channel_id: int, channel_name: str):
        """
        Fetch all videos and playlists from channel and save to database
        """
        import yt_dlp

        ydl_opts = self.video_opts.copy()

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Fetch channel information (flat = only metadata, no downloads)
                # url = f"https://www.youtube.com/{channel_name}"
                # info = ydl.extract_info(url, download=False)
                info = json.loads(jsn)

                # Extract playlists from the channel
                if 'entries' not in info:
                    display_message(f"No playlists found for channel: {channel_name}")
                    return

                for playlist in info['entries']:
                    if playlist.get('_type') != 'playlist':
                        display_message(f"Skipping non-playlist entry: {playlist.get('title')}")
                        continue
                    
                    playlist_title = playlist.get('title', '')
                    playlist_metadata = json.dumps(playlist)

                    playlist_id = sql.get_scalar("SELECT id FROM youtube_channel_playlists WHERE name = ? AND channel_id = ?", (playlist_title, channel_id))
                    if not playlist_id:
                        sql.execute("""
                            INSERT INTO youtube_channel_playlists (name, channel_id, metadata)
                            VALUES (?, ?, ?)
                        """, (playlist_title, channel_id, playlist_metadata))
                        playlist_id = sql.execute("SELECT MAX(id) FROM youtube_channel_playlists")

                    # Extract videos inside the playlist
                    if 'entries' in playlist:
                        for video in playlist['entries']:
                            if video.get('_type') != 'url':
                                display_message(f"Skipping non-video entry: {video.get('title')}")
                                continue

                            video_title = video.get('title', '')
                            video_metadata = json.dumps(video)

                            video_id = sql.get_scalar("SELECT id FROM youtube_channel_videos WHERE name = ? AND channel_id = ?", (video_title, channel_id))
                            if not video_id:
                                # Insert video into youtube_channel_videos
                                sql.execute("""
                                    INSERT INTO youtube_channel_videos (name, channel_id, playlist_id, metadata)
                                    VALUES (?, ?, ?, ?)
                                """, (video_title, channel_id, playlist_id, video_metadata))
                                video_id = sql.execute("SELECT MAX(id) FROM youtube_channel_videos")

                # sql.commit()

        except Exception as e:
            raise ValueError(f"Failed to fetch channel playlists: {str(e)}")

    async def stop(self):
        """Stop the daemon and cancel all tasks."""
        self._running = False

        # Cancel all sync tasks
        for task in self._sync_tasks.values():
            if not task.done():
                task.cancel()

        # Cancel task group if it exists
        if self._task_group:
            # Note: TaskGroup doesn't have a cancel method, tasks will cancel on exit
            pass

    # async def _initialize_auto_sync_tasks(self, tg: asyncio.TaskGroup):
    #     """Initialize auto-sync tasks for channels with auto_sync enabled.

    #     Parameters
    #     ----------
    #     tg : asyncio.TaskGroup
    #         Task group to create tasks in
    #     """
    #     # Get all channels with auto_sync enabled
    #     channels = self.db_connector.get_results("""
    #         SELECT id, name, config
    #         FROM youtube_channels
    #         WHERE config IS NOT NULL
    #     """)

    #     for channel in channels:
    #         try:
    #             config = json.loads(channel[2]) if channel[2] else {}
    #             if config.get('auto_sync', False):
    #                 channel_id = channel[0]
    #                 sync_frequency = config.get('sync_frequency', 24)
    #                 task = tg.create_task(
    #                     self._channel_sync_task(channel_id, sync_frequency)
    #                 )
    #                 self._sync_tasks[channel_id] = task
    #         except Exception as e:
    #             print(f"Error initializing sync for channel {channel[1]}: {e}")

    # async def _auto_sync_monitor(self):
    #     """Monitor for changes in auto-sync settings and manage sync tasks."""
    #     while self._running:
    #         try:
    #             # Check every 60 seconds for auto-sync changes
    #             await asyncio.sleep(60)

    #             # Get current auto-sync settings
    #             channels = self.db_connector.get_results("""
    #                 SELECT id, name, config
    #                 FROM youtube_channels
    #                 WHERE config IS NOT NULL
    #             """)

    #             current_auto_sync_ids = set()

    #             for channel in channels:
    #                 try:
    #                     config = json.loads(channel[2]) if channel[2] else {}
    #                     channel_id = channel[0]

    #                     if config.get('auto_sync', False):
    #                         current_auto_sync_ids.add(channel_id)

    #                         # Start new sync task if not already running
    #                         if channel_id not in self._sync_tasks or self._sync_tasks[channel_id].done():
    #                             sync_frequency = config.get('sync_frequency', 24)
    #                             task = asyncio.create_task(
    #                                 self._channel_sync_task(channel_id, sync_frequency)
    #                             )
    #                             self._sync_tasks[channel_id] = task
    #                 except Exception as e:
    #                     print(f"Error processing channel {channel[1]}: {e}")

    #             # Cancel tasks for channels that no longer have auto-sync
    #             for channel_id, task in list(self._sync_tasks.items()):
    #                 if channel_id not in current_auto_sync_ids and not task.done():
    #                     task.cancel()
    #                     del self._sync_tasks[channel_id]

    #         except Exception as e:
    #             print(f"Error in auto-sync monitor: {e}")

    # async def _channel_sync_task(self, channel_id: int, sync_frequency: int):
    #     """Background task for auto-syncing a channel.

    #     Parameters
    #     ----------
    #     channel_id : int
    #         Database ID of the channel
    #     sync_frequency : int
    #         Hours between syncs
    #     """
    #     while self._running:
    #         try:
    #             # Perform sync
    #             await self.sync_channel(channel_id)

    #             # Wait for next sync
    #             await asyncio.sleep(sync_frequency * 3600)

    #         except asyncio.CancelledError:
    #             break
    #         except Exception as e:
    #             print(f"Error in channel sync task {channel_id}: {e}")
    #             # On error, wait 5 minutes before retrying
    #             await asyncio.sleep(300)

    # async def get_channel_info(self, channel_url_or_handle: str) -> Dict[str, Any]:
    #     """Fetch channel metadata asynchronously.

    #     Parameters
    #     ----------
    #     channel_url_or_handle : str
    #         YouTube channel URL, handle, or channel ID

    #     Returns
    #     -------
    #     dict
    #         Channel metadata
    #     """
    #     # Ensure proper channel URL format
    #     if '@' in channel_url_or_handle and '/videos' not in channel_url_or_handle:
    #         channel_url = f"{channel_url_or_handle}/videos"
    #     elif 'youtube.com/channel/' in channel_url_or_handle and '/videos' not in channel_url_or_handle:
    #         channel_url = f"{channel_url_or_handle}/videos"
    #     else:
    #         channel_url = channel_url_or_handle

    #     def extract_info():
    #         with yt_dlp.YoutubeDL(self.channel_opts) as ydl:
    #             info = ydl.extract_info(channel_url, download=False)
    #             return {
    #                 'name': info.get('title', info.get('uploader', 'Unknown')),
    #                 'channel_id': info.get('channel_id', ''),
    #                 'channel_url': info.get('channel_url', ''),
    #                 'channel_handle': info.get('uploader_id', ''),
    #                 'thumbnail_url': info.get('thumbnail', ''),
    #                 'description': info.get('description', ''),
    #                 'subscriber_count': info.get('subscriber_count', 0) or 0,
    #                 'video_count': info.get('playlist_count', 0) or 0,
    #             }

    #     # Run yt-dlp in executor to avoid blocking
    #     loop = asyncio.get_event_loop()
    #     return await loop.run_in_executor(None, extract_info)

    # async def get_channel_videos(self, channel_url_or_handle: str, max_results: int = 50) -> List[Dict[str, Any]]:
    #     """Fetch channel videos asynchronously.

    #     Parameters
    #     ----------
    #     channel_url_or_handle : str
    #         YouTube channel URL, handle, or channel ID
    #     max_results : int
    #         Maximum number of videos to fetch

    #     Returns
    #     -------
    #     list
    #         List of video dictionaries
    #     """
    #     # Ensure proper channel URL format
    #     if '@' in channel_url_or_handle and '/videos' not in channel_url_or_handle:
    #         channel_url = f"{channel_url_or_handle}/videos"
    #     elif 'youtube.com/channel/' in channel_url_or_handle and '/videos' not in channel_url_or_handle:
    #         channel_url = f"{channel_url_or_handle}/videos"
    #     elif 'youtube.com/c/' in channel_url_or_handle and '/videos' not in channel_url_or_handle:
    #         channel_url = f"{channel_url_or_handle}/videos"
    #     else:
    #         channel_url = channel_url_or_handle

    #     opts = self.video_opts.copy()
    #     opts['playlistend'] = max_results

    #     def extract_videos():
    #         with yt_dlp.YoutubeDL(opts) as ydl:
    #             info = ydl.extract_info(channel_url, download=False)
    #             entries = info.get('entries', [])

    #             videos = []
    #             for entry in entries:
    #                 if not entry:
    #                     continue

    #                 # Skip non-video entries
    #                 if entry.get('_type') == 'playlist':
    #                     continue

    #                 if 'id' not in entry or 'title' not in entry:
    #                     continue

    #                 # Filter out special playlist names
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

    #                 if len(videos) >= max_results:
    #                     break

    #             return videos

    #     # Run yt-dlp in executor to avoid blocking
    #     loop = asyncio.get_event_loop()
    #     return await loop.run_in_executor(None, extract_videos)

    # async def sync_channel(self, channel_id: int) -> bool:
    #     """Sync channel data from YouTube.

    #     Parameters
    #     ----------
    #     channel_id : int
    #         Database ID of the channel to sync

    #     Returns
    #     -------
    #     bool
    #         True if sync was successful
    #     """
    #     try:
    #         # Get channel handle from database
    #         channel_handle = self.db_connector.get_scalar(
    #             "SELECT name FROM youtube_channels WHERE id = ?",
    #             (channel_id,)
    #         )

    #         if not channel_handle:
    #             return False

    #         channel_url = f'https://www.youtube.com/{channel_handle}'

    #         # Fetch channel info and videos concurrently
    #         channel_info_task = asyncio.create_task(self.get_channel_info(channel_url))
    #         videos_task = asyncio.create_task(self.get_channel_videos(channel_url, max_results=50))

    #         channel_info = await channel_info_task
    #         videos = await videos_task

    #         # Prepare config and metadata
    #         config = {
    #             'channel_id': channel_info['channel_id'],
    #             'channel_url': channel_info['channel_url'],
    #             'channel_handle': channel_info['channel_handle'],
    #             'thumbnail_url': channel_info['thumbnail_url'],
    #             'description': channel_info['description'],
    #             'subscriber_count': channel_info['subscriber_count'],
    #             'video_count': channel_info['video_count'],
    #             'last_sync': datetime.now().isoformat(),
    #         }

    #         metadata = {
    #             'videos': videos
    #         }

    #         # Preserve existing auto_sync settings
    #         existing_config = self.db_connector.get_scalar(
    #             "SELECT config FROM youtube_channels WHERE id = ?",
    #             (channel_id,),
    #             load_json=True
    #         )

    #         if existing_config:
    #             config['auto_sync'] = existing_config.get('auto_sync', False)
    #             config['sync_frequency'] = existing_config.get('sync_frequency', 24)

    #         # Update database
    #         self.db_connector.execute(
    #             """UPDATE youtube_channels
    #                SET config = ?, metadata = ?
    #                WHERE id = ?""",
    #             (json.dumps(config), json.dumps(metadata), channel_id)
    #         )

    #         return True

    #     except Exception as e:
    #         print(f"Error syncing channel {channel_id}: {e}")
    #         return False

    # async def get_video_info(self, video_url: str) -> Dict[str, Any]:
    #     """Fetch single video information asynchronously.

    #     Parameters
    #     ----------
    #     video_url : str
    #         YouTube video URL

    #     Returns
    #     -------
    #     dict
    #         Video metadata
    #     """
    #     def extract_info():
    #         opts = {
    #             'quiet': True,
    #             'no_warnings': True,
    #         }

    #         with yt_dlp.YoutubeDL(opts) as ydl:
    #             info = ydl.extract_info(video_url, download=False)
    #             return {
    #                 'video_id': info.get('id', ''),
    #                 'title': info.get('title', 'Unknown'),
    #                 'thumbnail_url': info.get('thumbnail', ''),
    #                 'duration': info.get('duration', 0) or 0,
    #                 'upload_date': info.get('upload_date', ''),
    #                 'view_count': info.get('view_count', 0) or 0,
    #                 'description': info.get('description', ''),
    #                 'url': info.get('webpage_url', video_url),
    #                 'channel': info.get('channel', ''),
    #                 'channel_id': info.get('channel_id', ''),
    #             }

    #     # Run yt-dlp in executor to avoid blocking
    #     loop = asyncio.get_event_loop()
    #     return await loop.run_in_executor(None, extract_info)

    # async def download_video(self, video_url: str, output_path: str, progress_callback=None):
    #     """Download video asynchronously with progress tracking.

    #     Parameters
    #     ----------
    #     video_url : str
    #         YouTube video URL
    #     output_path : str
    #         Output file path
    #     progress_callback : callable, optional
    #         Async callback function for progress updates
    #     """
    #     def progress_hook(d):
    #         if progress_callback and d['status'] == 'downloading':
    #             if 'total_bytes' in d:
    #                 percent = d['downloaded_bytes'] / d['total_bytes'] * 100
    #                 # Schedule callback in the event loop
    #                 asyncio.create_task(progress_callback(percent))

    #     def download():
    #         opts = {
    #             'quiet': True,
    #             'no_warnings': True,
    #             'outtmpl': output_path,
    #             'progress_hooks': [progress_hook] if progress_callback else [],
    #         }

    #         with yt_dlp.YoutubeDL(opts) as ydl:
    #             ydl.download([video_url])

    #     # Run download in executor to avoid blocking
    #     loop = asyncio.get_event_loop()
    #     await loop.run_in_executor(None, download)

    # @staticmethod
    # def validate_channel_url(url_or_handle: str) -> tuple[bool, str]:
    #     """Validate and normalize YouTube channel URL/handle.

    #     Parameters
    #     ----------
    #     url_or_handle : str
    #         YouTube channel URL, handle, or channel ID

    #     Returns
    #     -------
    #     tuple[bool, str]
    #         (is_valid, normalized_url)
    #     """
    #     if not url_or_handle:
    #         return False, ""

    #     url_or_handle = url_or_handle.strip()

    #     # Handle @username format
    #     if url_or_handle.startswith('@'):
    #         return True, f"https://youtube.com/{url_or_handle}"

    #     # Handle channel ID format
    #     if re.match(r'^UC[\w-]{22}$', url_or_handle):
    #         return True, f"https://youtube.com/channel/{url_or_handle}"

    #     # Handle full URLs
    #     youtube_patterns = [
    #         r'(?:https?://)?(?:www\.)?youtube\.com/(?:c/|channel/|user/|@)[\w-]+',
    #         r'(?:https?://)?(?:www\.)?youtube\.com/@[\w-]+',
    #     ]

    #     for pattern in youtube_patterns:
    #         if re.match(pattern, url_or_handle):
    #             if not url_or_handle.startswith('http'):
    #                 url_or_handle = 'https://' + url_or_handle
    #             return True, url_or_handle

    #     return False, url_or_handle

    # @staticmethod
    # def format_duration(seconds: int) -> str:
    #     """Format duration in seconds to HH:MM:SS or MM:SS.

    #     Parameters
    #     ----------
    #     seconds : int
    #         Duration in seconds

    #     Returns
    #     -------
    #     str
    #         Formatted duration string
    #     """
    #     if seconds < 0:
    #         return "00:00"

    #     hours = seconds // 3600
    #     minutes = (seconds % 3600) // 60
    #     secs = seconds % 60

    #     if hours > 0:
    #         return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    #     else:
    #         return f"{minutes:02d}:{secs:02d}"

    # @staticmethod
    # def format_upload_date(date_str: str) -> str:
    #     """Format upload date string to readable format.

    #     Parameters
    #     ----------
    #     date_str : str
    #         Date string in YYYYMMDD format

    #     Returns
    #     -------
    #     str
    #         Formatted date string
    #     """
    #     if not date_str or len(date_str) != 8:
    #         return ""

    #     try:
    #         date_obj = datetime.strptime(date_str, '%Y%m%d')
    #         return date_obj.strftime('%Y-%m-%d')
    #     except ValueError:
    #         return date_str

    # @staticmethod
    # def format_view_count(count: int) -> str:
    #     """Format view count to readable string.

    #     Parameters
    #     ----------
    #     count : int
    #         View count

    #     Returns
    #     -------
    #     str
    #         Formatted view count string (e.g., "1.2M", "45K")
    #     """
    #     if count < 1000:
    #         return str(count)
    #     elif count < 1000000:
    #         return f"{count/1000:.1f}K"
    #     else:
    #         return f"{count/1000000:.1f}M"