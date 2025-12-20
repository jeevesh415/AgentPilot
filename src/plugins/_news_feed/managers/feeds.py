"""
Feed Manager for News Feed Plugin
Handles CRUD operations for RSS/Atom feeds
"""

import json
import logging
import time
from typing import Dict, List, Optional
from datetime import datetime

from utils.helpers import BaseManager
from utils import sql
from plugins.news_feed.utils.rss_parser import fetch_and_parse_feed, validate_feed_url

logger = logging.getLogger(__name__)


class FeedManager(BaseManager):
    """Manager for RSS/Atom feeds"""

    def __init__(self, system):
        super().__init__(
            system,
            table_name='feeds',
            folder_key='news_feeds',
            load_columns=['name', 'config', 'metadata'],
            add_item_options={
                'title': 'Add RSS Feed',
                'prompt': 'Enter the RSS/Atom feed URL:',
                'validator': self.validate_feed
            },
            del_item_options={
                'title': 'Delete Feed',
                'prompt': 'Are you sure you want to delete this feed and all its items?'
            }
        )

        # Define database tables
        self._define_tables()

    def _define_tables(self):
        """Define database tables for feeds and feed items"""
        # Define feeds table (will have auto-generated columns)
        sql.define_table('feeds')

        # Define feed_items table with feed_id relation
        sql.define_table('feed_items', relations=['feed_id'])

        # Add indexes for better performance
        try:
            sql.execute("""
                CREATE INDEX IF NOT EXISTS idx_feed_items_feed_id
                ON feed_items(feed_id)
            """)
            sql.execute("""
                CREATE INDEX IF NOT EXISTS idx_feed_items_created_at
                ON feed_items(created_at)
            """)
        except Exception as e:
            logger.debug(f"Indexes may already exist: {e}")

    def validate_feed(self, url: str) -> tuple[bool, str]:
        """
        Validate a feed URL before adding it
        Returns: (is_valid, error_message)
        """
        # Check URL format
        if not validate_feed_url(url):
            return False, "Invalid URL format. Please enter a valid HTTP/HTTPS URL."

        # Check if feed already exists
        existing = sql.get_scalar("""
            SELECT COUNT(*) FROM feeds
            WHERE json_extract(config, '$.url') = ?
        """, (url,))

        if existing > 0:
            return False, "This feed URL has already been added."

        # Try to fetch and parse the feed
        try:
            feed_info, items = fetch_and_parse_feed(url)
            if not feed_info.get('title'):
                return False, "Could not extract feed title."
            return True, ""
        except Exception as e:
            return False, f"Failed to fetch feed: {str(e)}"

    def add_feed(self, url: str, name: Optional[str] = None, folder_id: Optional[int] = None) -> Optional[int]:
        """Add a new feed to the database"""
        try:
            # Fetch and parse the feed to get metadata
            feed_info, items = fetch_and_parse_feed(url)

            # Use provided name or feed title
            feed_name = name or feed_info.get('title', 'Untitled Feed')

            # Prepare config
            config = {
                'url': url,
                'enabled': True,
                'update_interval': 3600,  # Default 1 hour
                'max_items': 100,
                'last_fetched': None,
                'last_error': None,
                'error_count': 0
            }

            # Prepare metadata
            metadata = {
                'feed_type': feed_info.get('type', 'unknown'),
                'feed_title': feed_info.get('title', ''),
                'feed_description': feed_info.get('description', ''),
                'feed_link': feed_info.get('link', ''),
                'feed_language': feed_info.get('language', ''),
                'item_count': len(items)
            }

            # Insert feed into database
            feed_id = sql.execute("""
                INSERT INTO feeds (name, kind, config, metadata, folder_id)
                VALUES (?, 'feed', ?, ?, ?)
            """, (
                feed_name,
                json.dumps(config),
                json.dumps(metadata),
                folder_id
            ))

            # Store initial items if any
            if items:
                self.store_feed_items(feed_id, items[:config['max_items']])

            logger.info(f"Added feed '{feed_name}' with ID {feed_id}")
            return feed_id

        except Exception as e:
            logger.error(f"Failed to add feed: {e}")
            raise

    def store_feed_items(self, feed_id: int, items: List[Dict]) -> int:
        """Store feed items in the database"""
        stored_count = 0

        for item in items:
            try:
                # Check if item already exists (by guid or link)
                guid = item.get('guid', item.get('link', ''))
                if not guid:
                    continue

                existing = sql.get_scalar("""
                    SELECT COUNT(*) FROM feed_items
                    WHERE feed_id = ? AND json_extract(config, '$.guid') = ?
                """, (feed_id, guid))

                if existing > 0:
                    continue  # Skip existing items

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
                sql.execute("""
                    INSERT INTO feed_items (feed_id, name, config, metadata, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    feed_id,
                    item.get('title', 'Untitled'),
                    json.dumps(config),
                    json.dumps(metadata),
                    int(time.time())
                ))

                stored_count += 1

            except Exception as e:
                logger.error(f"Failed to store item: {e}")
                continue

        return stored_count

    def update_feed(self, feed_id: int) -> tuple[int, Optional[str]]:
        """
        Manually update a feed
        Returns: (new_items_count, error_message)
        """
        try:
            # Get feed config
            feed_config = sql.get_scalar("""
                SELECT config FROM feeds WHERE id = ?
            """, (feed_id,), load_json=True)

            if not feed_config:
                return 0, "Feed not found"

            url = feed_config.get('url')
            if not url:
                return 0, "Feed URL not configured"

            # Fetch and parse feed
            feed_info, items = fetch_and_parse_feed(url)

            # Update feed metadata
            metadata = {
                'feed_type': feed_info.get('type', 'unknown'),
                'feed_title': feed_info.get('title', ''),
                'feed_description': feed_info.get('description', ''),
                'feed_link': feed_info.get('link', ''),
                'feed_language': feed_info.get('language', ''),
                'last_updated': datetime.now().isoformat()
            }

            # Store new items
            max_items = feed_config.get('max_items', 100)
            new_count = self.store_feed_items(feed_id, items[:max_items])

            # Update feed config with success
            sql.execute("""
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
            """, (
                datetime.now().isoformat(),
                json.dumps(metadata),
                feed_id
            ))

            # Clean up old items if exceeding max_items
            self.cleanup_old_items(feed_id, max_items)

            return new_count, None

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to update feed {feed_id}: {error_msg}")

            # Update feed config with error
            try:
                sql.execute("""
                    UPDATE feeds
                    SET config = json_set(
                        json_set(config, '$.last_error', ?),
                        '$.error_count', json_extract(config, '$.error_count') + 1
                    )
                    WHERE id = ?
                """, (error_msg, feed_id))
            except Exception as update_error:
                logger.error(f"Failed to update error status: {update_error}")

            return 0, error_msg

    def cleanup_old_items(self, feed_id: int, max_items: int):
        """Remove old items exceeding max_items limit"""
        try:
            # Keep starred items and most recent items up to max_items
            sql.execute("""
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
            logger.error(f"Failed to cleanup old items: {e}")

    def get_feed_items(self, feed_id: int, unread_only: bool = False,
                      limit: int = 50, offset: int = 0) -> List[Dict]:
        """Get items for a specific feed"""
        try:
            where_clause = "WHERE feed_id = ?"
            params = [feed_id]

            if unread_only:
                where_clause += " AND json_extract(config, '$.read') = 0"

            query = f"""
                SELECT id, name, config, metadata, created_at
                FROM feed_items
                {where_clause}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """
            params.extend([limit, offset])

            results = sql.get_results(query, params, return_type='dict')

            # Parse JSON fields
            for item in results:
                item['config'] = json.loads(item['config']) if item['config'] else {}
                item['metadata'] = json.loads(item['metadata']) if item['metadata'] else {}

            return results

        except Exception as e:
            logger.error(f"Failed to get feed items: {e}")
            return []

    def get_all_items(self, unread_only: bool = False, starred_only: bool = False,
                     limit: int = 50, offset: int = 0) -> List[Dict]:
        """Get items from all feeds"""
        try:
            where_clauses = []
            params = []

            if unread_only:
                where_clauses.append("json_extract(fi.config, '$.read') = 0")

            if starred_only:
                where_clauses.append("json_extract(fi.config, '$.starred') = 1")

            where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

            query = f"""
                SELECT
                    fi.id,
                    fi.name,
                    fi.config,
                    fi.metadata,
                    fi.created_at,
                    f.name as feed_name
                FROM feed_items fi
                JOIN feeds f ON fi.feed_id = f.id
                {where_clause}
                ORDER BY fi.created_at DESC
                LIMIT ? OFFSET ?
            """
            params.extend([limit, offset])

            results = sql.get_results(query, params, return_type='dict')

            # Parse JSON fields
            for item in results:
                item['config'] = json.loads(item['config']) if item['config'] else {}
                item['metadata'] = json.loads(item['metadata']) if item['metadata'] else {}

            return results

        except Exception as e:
            logger.error(f"Failed to get all items: {e}")
            return []

    def mark_item_read(self, item_id: int, read: bool = True):
        """Mark an item as read or unread"""
        try:
            sql.execute("""
                UPDATE feed_items
                SET config = json_set(config, '$.read', ?)
                WHERE id = ?
            """, (1 if read else 0, item_id))
        except Exception as e:
            logger.error(f"Failed to mark item as read: {e}")

    def mark_item_starred(self, item_id: int, starred: bool = True):
        """Mark an item as starred or unstarred"""
        try:
            sql.execute("""
                UPDATE feed_items
                SET config = json_set(config, '$.starred', ?)
                WHERE id = ?
            """, (1 if starred else 0, item_id))
        except Exception as e:
            logger.error(f"Failed to mark item as starred: {e}")

    def mark_all_read(self, feed_id: Optional[int] = None):
        """Mark all items as read for a feed or all feeds"""
        try:
            if feed_id:
                sql.execute("""
                    UPDATE feed_items
                    SET config = json_set(config, '$.read', 1)
                    WHERE feed_id = ?
                """, (feed_id,))
            else:
                sql.execute("""
                    UPDATE feed_items
                    SET config = json_set(config, '$.read', 1)
                """)
        except Exception as e:
            logger.error(f"Failed to mark all as read: {e}")

    def delete_feed(self, feed_id: int):
        """Delete a feed and all its items"""
        try:
            # Delete items first
            sql.execute("DELETE FROM feed_items WHERE feed_id = ?", (feed_id,))

            # Delete feed
            sql.execute("DELETE FROM feeds WHERE id = ?", (feed_id,))

            logger.info(f"Deleted feed {feed_id} and all its items")
        except Exception as e:
            logger.error(f"Failed to delete feed: {e}")
            raise

    def get_feeds_for_update(self) -> List[Dict]:
        """Get all enabled feeds that need updating"""
        try:
            query = """
                SELECT id, name, config
                FROM feeds
                WHERE json_extract(config, '$.enabled') = 1
                ORDER BY json_extract(config, '$.last_fetched') ASC NULLS FIRST
            """

            results = sql.get_results(query, return_type='dict')

            # Parse config JSON
            for feed in results:
                feed['config'] = json.loads(feed['config']) if feed['config'] else {}

            return results

        except Exception as e:
            logger.error(f"Failed to get feeds for update: {e}")
            return []