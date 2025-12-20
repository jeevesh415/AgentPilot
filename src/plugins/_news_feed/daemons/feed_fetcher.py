"""
Feed Fetcher Daemon
Background service that periodically fetches new items from RSS/Atom feeds
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from utils import sql
from plugins.news_feed.utils.rss_parser import fetch_and_parse_feed

logger = logging.getLogger(__name__)


class FeedFetcherDaemon:
    """Daemon for fetching RSS/Atom feeds periodically"""

    def __init__(self, system=None):
        self.system = system
        self._running = False
        self._task_group = None
        self._feed_tasks = {}  # Track running tasks per feed
        self._last_fetch = {}  # Track last fetch time per feed

        # Define tables on initialization
        self._define_tables()

        logger.info("Feed Fetcher Daemon initialized")

    def _define_tables(self):
        """Ensure database tables exist"""
        try:
            sql.define_table('feeds')
            sql.define_table('feed_items', relations=['feed_id'])

            # Create indexes for better performance
            sql.execute("""
                CREATE INDEX IF NOT EXISTS idx_feed_items_feed_id
                ON feed_items(feed_id)
            """)
            sql.execute("""
                CREATE INDEX IF NOT EXISTS idx_feed_items_created_at
                ON feed_items(created_at)
            """)
        except Exception as e:
            logger.debug(f"Tables/indexes may already exist: {e}")

    async def start(self):
        """Start the daemon"""
        logger.info("Starting Feed Fetcher Daemon")
        self._running = True

        try:
            # Initial load of feeds
            await self.load_feeds()

            # Main daemon loop
            while self._running:
                try:
                    # Check feeds every minute
                    await asyncio.sleep(60)

                    if not self._running:
                        break

                    # Reload feeds and check for updates
                    await self.check_feeds()

                except asyncio.CancelledError:
                    logger.info("Feed fetcher daemon cancelled")
                    break
                except Exception as e:
                    logger.error(f"Error in daemon loop: {e}")
                    await asyncio.sleep(60)  # Wait before retrying

        except Exception as e:
            logger.error(f"Fatal error in feed fetcher daemon: {e}")
        finally:
            self._running = False
            logger.info("Feed Fetcher Daemon stopped")

    def stop(self):
        """Stop the daemon"""
        logger.info("Stopping Feed Fetcher Daemon")
        self._running = False

        # Cancel all running feed tasks
        for task in self._feed_tasks.values():
            if not task.done():
                task.cancel()

    async def load_feeds(self):
        """Load all enabled feeds from database"""
        try:
            feeds = await asyncio.to_thread(sql.get_results, """
                SELECT id, name, config
                FROM feeds
                WHERE json_extract(config, '$.enabled') = 1
            """, return_type='dict')

            logger.info(f"Loaded {len(feeds)} enabled feeds")

            # Initialize last fetch times
            for feed in feeds:
                feed_id = feed['id']
                config = json.loads(feed['config']) if feed['config'] else {}
                last_fetched = config.get('last_fetched')

                if last_fetched:
                    try:
                        self._last_fetch[feed_id] = datetime.fromisoformat(last_fetched)
                    except:
                        self._last_fetch[feed_id] = None
                else:
                    self._last_fetch[feed_id] = None

                # Fetch immediately if never fetched
                if not self._last_fetch[feed_id]:
                    asyncio.create_task(self.fetch_feed(feed))

        except Exception as e:
            logger.error(f"Failed to load feeds: {e}")

    async def check_feeds(self):
        """Check all feeds and fetch those that need updating"""
        try:
            feeds = await asyncio.to_thread(sql.get_results, """
                SELECT id, name, config
                FROM feeds
                WHERE json_extract(config, '$.enabled') = 1
            """, return_type='dict')

            current_time = datetime.now()

            for feed in feeds:
                feed_id = feed['id']
                config = json.loads(feed['config']) if feed['config'] else {}

                # Skip if already fetching
                if feed_id in self._feed_tasks and not self._feed_tasks[feed_id].done():
                    continue

                # Check if it's time to fetch
                update_interval = config.get('update_interval', 3600)  # Default 1 hour
                last_fetch = self._last_fetch.get(feed_id)

                if last_fetch:
                    time_since_fetch = (current_time - last_fetch).total_seconds()
                    if time_since_fetch < update_interval:
                        continue

                # Schedule fetch
                logger.debug(f"Scheduling fetch for feed: {feed['name']}")
                task = asyncio.create_task(self.fetch_feed(feed))
                self._feed_tasks[feed_id] = task

        except Exception as e:
            logger.error(f"Failed to check feeds: {e}")

    async def fetch_feed(self, feed_data: Dict):
        """Fetch a single feed"""
        feed_id = feed_data['id']
        feed_name = feed_data['name']

        try:
            config = json.loads(feed_data['config']) if feed_data['config'] else {}
            url = config.get('url')

            if not url:
                logger.warning(f"Feed {feed_name} has no URL configured")
                return

            logger.info(f"Fetching feed: {feed_name}")

            # Fetch and parse feed
            feed_info, items = await asyncio.to_thread(
                fetch_and_parse_feed, url, timeout=30
            )

            # Store new items
            max_items = config.get('max_items', 100)
            new_count = await self.store_feed_items(feed_id, items[:max_items])

            # Update feed metadata and status
            await self.update_feed_status(feed_id, feed_info, success=True)

            # Update last fetch time
            self._last_fetch[feed_id] = datetime.now()

            logger.info(f"Feed {feed_name}: fetched {new_count} new items")

        except asyncio.CancelledError:
            logger.info(f"Fetch cancelled for feed: {feed_name}")
            raise
        except Exception as e:
            logger.error(f"Failed to fetch feed {feed_name}: {e}")
            await self.update_feed_status(feed_id, None, success=False, error=str(e))

    async def store_feed_items(self, feed_id: int, items: List[Dict]) -> int:
        """Store new feed items in database"""
        stored_count = 0

        try:
            # Get existing item GUIDs to avoid duplicates
            existing_guids = await asyncio.to_thread(sql.get_results, """
                SELECT json_extract(config, '$.guid') as guid
                FROM feed_items
                WHERE feed_id = ?
            """, (feed_id,), return_type='column')

            existing_guids = set(existing_guids)

            for item in items:
                try:
                    # Check for duplicate
                    guid = item.get('guid', item.get('link', ''))
                    if not guid or guid in existing_guids:
                        continue

                    # Prepare item config
                    config = {
                        'guid': guid,
                        'title': item.get('title', 'Untitled'),
                        'link': item.get('link', ''),
                        'description': item.get('description', ''),
                        'content': item.get('content', ''),
                        'author': item.get('author', ''),
                        'pub_date': item.get('pub_date', ''),
                        'read': False,
                        'starred': False,
                        'categories': item.get('categories', [])
                    }

                    # Prepare metadata
                    metadata = {
                        'enclosure': item.get('enclosure', {})
                    }

                    # Insert item
                    await asyncio.to_thread(sql.execute, """
                        INSERT INTO feed_items (feed_id, name, config, metadata)
                        VALUES (?, ?, ?, ?)
                    """, (
                        feed_id,
                        item.get('title', 'Untitled')[:255],  # Limit title length
                        json.dumps(config),
                        json.dumps(metadata)
                    ))

                    stored_count += 1
                    existing_guids.add(guid)

                except Exception as e:
                    logger.debug(f"Failed to store item: {e}")
                    continue

            # Clean up old items if needed
            if stored_count > 0:
                await self.cleanup_old_items(feed_id)

        except Exception as e:
            logger.error(f"Failed to store feed items: {e}")

        return stored_count

    async def cleanup_old_items(self, feed_id: int):
        """Remove old items exceeding max_items limit"""
        try:
            # Get max items setting
            config_json = await asyncio.to_thread(sql.get_scalar, """
                SELECT config FROM feeds WHERE id = ?
            """, (feed_id,))

            config = json.loads(config_json) if config_json else {}
            max_items = config.get('max_items', 100)

            # Delete old unstarred items
            await asyncio.to_thread(sql.execute, """
                DELETE FROM feed_items
                WHERE feed_id = ?
                AND json_extract(config, '$.starred') = 0
                AND id NOT IN (
                    SELECT id FROM feed_items
                    WHERE feed_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                )
            """, (feed_id, feed_id, max_items))

        except Exception as e:
            logger.debug(f"Failed to cleanup old items: {e}")

    async def update_feed_status(self, feed_id: int, feed_info: Optional[Dict],
                                success: bool, error: Optional[str] = None):
        """Update feed status after fetch attempt"""
        try:
            current_time = datetime.now().isoformat()

            if success:
                # Update metadata if available
                if feed_info:
                    metadata = {
                        'feed_type': feed_info.get('type', 'unknown'),
                        'feed_title': feed_info.get('title', ''),
                        'feed_description': feed_info.get('description', ''),
                        'feed_link': feed_info.get('link', ''),
                        'feed_language': feed_info.get('language', ''),
                        'last_updated': current_time
                    }

                    await asyncio.to_thread(sql.execute, """
                        UPDATE feeds
                        SET config = json_set(
                            json_set(
                                json_set(config, '$.last_fetched', ?),
                                '$.last_error', NULL
                            ),
                            '$.error_count', 0
                        ),
                        metadata = ?
                        WHERE id = ?
                    """, (current_time, json.dumps(metadata), feed_id))
                else:
                    # Just update last fetch time
                    await asyncio.to_thread(sql.execute, """
                        UPDATE feeds
                        SET config = json_set(
                            json_set(
                                json_set(config, '$.last_fetched', ?),
                                '$.last_error', NULL
                            ),
                            '$.error_count', 0
                        )
                        WHERE id = ?
                    """, (current_time, feed_id))
            else:
                # Update error status
                await asyncio.to_thread(sql.execute, """
                    UPDATE feeds
                    SET config = json_set(
                        json_set(config, '$.last_error', ?),
                        '$.error_count', json_extract(config, '$.error_count') + 1
                    )
                    WHERE id = ?
                """, (error or "Unknown error", feed_id))

        except Exception as e:
            logger.error(f"Failed to update feed status: {e}")


# Daemon instance for the system to manage
daemon_instance = None


def get_daemon(system=None):
    """Get or create the daemon instance"""
    global daemon_instance
    if daemon_instance is None:
        daemon_instance = FeedFetcherDaemon(system)
    return daemon_instance


# Entry points for the system
async def start(system=None):
    """Start the daemon (called by system)"""
    daemon = get_daemon(system)
    await daemon.start()


def stop(system=None):
    """Stop the daemon (called by system)"""
    daemon = get_daemon(system)
    daemon.stop()