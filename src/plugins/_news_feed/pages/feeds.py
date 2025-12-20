"""
Main Feeds Management Page
Provides the primary interface for managing RSS/Atom feeds
"""

import json
import logging

from PySide6.QtWidgets import QMessageBox, QInputDialog

from gui.widgets.config_db_tree import ConfigDBTree
from plugins.news_feed.widgets.feed_config import FeedConfigWidget
from gui.widgets.config_fields import ConfigFields
from utils import sql

logger = logging.getLogger(__name__)


class Page_News_Feeds(ConfigDBTree):
    """Main page for managing RSS/Atom feeds"""

    display_name = "News Feeds"
    icon_path = ":/resources/icon-globe.png"  # Using globe icon for feeds
    page_type = 'main'  # Show in main navigation

    def __init__(self, parent):
        # Initialize feed manager
        from plugins.news_feed.managers.feeds import FeedManager
        self.feed_manager = FeedManager(getattr(parent, 'system', None))

        super().__init__(
            parent=parent,
            manager='feeds',  # Reference to the feed manager
            table_name='feeds',
            query="""
                SELECT
                    f.name,
                    f.id,
                    f.config,
                    f.metadata,
                    f.folder_id,
                    f.pinned,
                    json_extract(f.config, '$.enabled') as enabled,
                    json_extract(f.config, '$.last_error') as has_error,
                    (SELECT COUNT(*) FROM feed_items
                     WHERE feed_id = f.id
                     AND json_extract(config, '$.read') = 0) as unread_count
                FROM feeds f
                ORDER BY f.pinned DESC, f.folder_id, f.ordr, f.name COLLATE NOCASE
            """,
            schema=[
                {
                    'text': 'Feed',
                    'key': 'name',
                    'type': str,
                    'stretch': True,
                },
                {
                    'text': '📰',  # Unread indicator
                    'key': 'unread_count',
                    'type': int,
                    'width': 40,
                    'text_alignment': 'center',
                },
                {
                    'text': '✓',  # Enabled indicator
                    'key': 'enabled',
                    'type': bool,
                    'width': 30,
                    'text_alignment': 'center',
                },
                {
                    'text': 'id',
                    'key': 'id',
                    'type': int,
                    'visible': False,
                },
                {
                    'text': 'config',
                    'key': 'config',
                    'type': str,
                    'visible': False,
                },
                {
                    'text': 'metadata',
                    'key': 'metadata',
                    'type': str,
                    'visible': False,
                },
                {
                    'text': 'has_error',
                    'key': 'has_error',
                    'type': str,
                    'visible': False,
                },
            ],
            add_item_prompt="Enter the RSS/Atom feed URL:",
            add_item_title="Add RSS Feed",
            add_folder_prompt="Enter folder name:",
            del_item_prompt="Are you sure you want to delete this feed and all its items?",
            del_folder_prompt="Delete this folder and move feeds to root?",
            layout_type='horizontal',
            config_widget=self.Feed_Config_Widget(parent=self),
            folder_config_widget=self.Folder_Config_Widget(parent=self),
            searchable=True,
            filterable=False,
            tree_header_hidden=False,
            readonly=False,
            folder_key='news_feed_folders',
        )

        # Set initial splitter sizes
        self.splitter.setSizes([300, 700])

        # Apply custom styling to show errors
        self.tree.setStyleSheet(self.tree.styleSheet() + """
            QTreeView::item {
                padding: 2px;
            }
        """)

    def on_item_added(self):
        """Override to handle adding new feeds"""
        url, ok = QInputDialog.getText(
            self,
            self.add_item_title,
            self.add_item_prompt,
            text=""
        )

        if ok and url:
            try:
                # Validate URL
                is_valid, error_msg = self.feed_manager.validate_feed(url)
                if not is_valid:
                    QMessageBox.warning(
                        self,
                        "Invalid Feed",
                        error_msg
                    )
                    return

                # Get current folder
                folder_id = self.get_selected_folder_id()

                # Add the feed
                feed_id = self.feed_manager.add_feed(url, folder_id=folder_id)

                if feed_id:
                    # Refresh tree and select the new feed
                    self.load(select_id=feed_id)

                    QMessageBox.information(
                        self,
                        "Feed Added",
                        "The feed has been successfully added and initial items have been fetched."
                    )

            except Exception as e:
                logger.error(f"Failed to add feed: {e}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to add feed: {str(e)}"
                )

    def on_item_deleted(self):
        """Override to handle feed deletion"""
        item_id = self.get_selected_item_id()
        if not item_id:
            return

        reply = QMessageBox.question(
            self,
            self.del_item_title,
            self.del_item_prompt,
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                self.feed_manager.delete_feed(item_id)
                self.load()
                QMessageBox.information(
                    self,
                    "Feed Deleted",
                    "The feed and all its items have been deleted."
                )
            except Exception as e:
                logger.error(f"Failed to delete feed: {e}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to delete feed: {str(e)}"
                )

    def on_edited(self, item_id, column_key, new_value):
        """Handle inline editing of feed properties"""
        if column_key == 'name':
            # Update feed name
            try:
                sql.execute("""
                    UPDATE feeds SET name = ? WHERE id = ?
                """, (new_value, item_id))
                self.load()
            except Exception as e:
                logger.error(f"Failed to update feed name: {e}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to update feed name: {str(e)}"
                )

    def format_display_value(self, row_data, column):
        """Format values for display in the tree"""
        key = column['key']
        value = row_data.get(key, '')

        if key == 'unread_count':
            # Show unread count or empty if zero
            if value and value > 0:
                return str(value)
            return ''

        elif key == 'enabled':
            # Show checkmark for enabled feeds
            if value:
                return '✓'
            return ''

        elif key == 'name':
            # Add error indicator to name if feed has errors
            if row_data.get('has_error'):
                return f"⚠️ {value}"
            return value

        return super().format_display_value(row_data, column)

    def get_item_tooltip(self, row_data, column):
        """Provide tooltips for tree items"""
        key = column['key']

        if key == 'unread_count':
            count = row_data.get('unread_count', 0)
            if count > 0:
                return f"{count} unread item{'s' if count != 1 else ''}"
            return "No unread items"

        elif key == 'enabled':
            if row_data.get('enabled'):
                return "Feed is enabled for automatic updates"
            return "Feed is disabled"

        elif key == 'name':
            if row_data.get('has_error'):
                return f"Last error: {row_data['has_error']}"

            # Show feed metadata in tooltip
            metadata = row_data.get('metadata', '{}')
            if metadata:
                try:
                    meta_dict = json.loads(metadata) if isinstance(metadata, str) else metadata
                    feed_type = meta_dict.get('feed_type', 'unknown')
                    description = meta_dict.get('feed_description', '')
                    if description:
                        return f"{feed_type.upper()} Feed: {description[:100]}"
                    return f"{feed_type.upper()} Feed"
                except:
                    pass

        return None

    def contextMenuEvent(self, event):
        """Add custom context menu items"""
        # Call parent implementation first
        super().contextMenuEvent(event)

        # Could add custom menu items here like:
        # - Update Now
        # - Mark All Read
        # - Open in Browser
        # - Export OPML

    class Feed_Config_Widget(FeedConfigWidget):
        """Custom feed configuration widget"""

        def __init__(self, parent):
            super().__init__(parent=parent)

            # Connect signal to refresh tree when feed is updated
            self.feed_updated.connect(parent.load)

    class Folder_Config_Widget(ConfigFields):
        """Configuration widget for feed folders"""

        def __init__(self, parent):
            super().__init__(
                parent=parent,
                propagate_config=False,
                schema=[
                    {
                        'text': 'Folder Name',
                        'key': 'name',
                        'type': str,
                        'width': 300,
                    },
                    {
                        'text': 'Description',
                        'key': 'description',
                        'type': str,
                        'multiline': True,
                        'width': 400,
                        'height': 60,
                        'is_config_field': True,
                    },
                    {
                        'text': 'Icon',
                        'key': 'icon',
                        'type': ('📁', '📂', '📰', '🗞️', '📡', '🌐'),
                        'default': '📁',
                        'width': 80,
                        'is_config_field': True,
                    }
                ]
            )