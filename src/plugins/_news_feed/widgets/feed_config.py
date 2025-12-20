"""
Feed Configuration Widget
Provides UI for configuring RSS/Atom feed settings
"""

import json
import logging
from datetime import datetime

from PySide6.QtWidgets import QPushButton, QHBoxLayout, QMessageBox
from PySide6.QtCore import Signal

from gui.widgets.config_fields import ConfigFields
from utils import sql

logger = logging.getLogger(__name__)


class FeedConfigWidget(ConfigFields):
    """Configuration widget for individual RSS/Atom feeds"""

    feed_updated = Signal(int)  # Emitted when feed is manually updated

    def __init__(self, parent):
        # Define configuration schema
        schema = [
            {
                'text': 'Feed URL',
                'key': 'url',
                'type': str,
                'width': 400,
                'placeholder': 'https://example.com/feed.xml',
                'tooltip': 'The RSS or Atom feed URL',
                'is_config_field': True,
            },
            {
                'text': 'Custom Name',
                'key': 'custom_name',
                'type': str,
                'width': 300,
                'placeholder': 'Leave empty to use feed title',
                'tooltip': 'Override the feed title with a custom name',
                'is_config_field': False,  # Store in name column, not config
            },
            {
                'text': 'Enabled',
                'key': 'enabled',
                'type': bool,
                'default': True,
                'tooltip': 'Enable or disable automatic feed updates',
                'is_config_field': True,
            },
            {
                'text': 'Update Interval',
                'key': 'update_interval',
                'type': ('15 minutes', '30 minutes', '1 hour', '3 hours', '6 hours', '12 hours', '24 hours'),
                'default': '1 hour',
                'width': 150,
                'tooltip': 'How often to check for new items',
                'is_config_field': True,
                'map_values': {  # Map display values to seconds
                    '15 minutes': 900,
                    '30 minutes': 1800,
                    '1 hour': 3600,
                    '3 hours': 10800,
                    '6 hours': 21600,
                    '12 hours': 43200,
                    '24 hours': 86400
                }
            },
            {
                'text': 'Max Items',
                'key': 'max_items',
                'type': int,
                'default': 100,
                'minimum': 10,
                'maximum': 1000,
                'width': 100,
                'tooltip': 'Maximum number of items to keep for this feed',
                'is_config_field': True,
            },
            {
                'text': 'Categories',
                'key': 'categories',
                'type': str,
                'width': 300,
                'placeholder': 'tech, news, blog (comma-separated)',
                'tooltip': 'Categorize this feed with tags',
                'is_config_field': True,
            }
        ]

        super().__init__(
            parent=parent,
            schema=schema,
            propagate_config=False  # Don't propagate to parent immediately
        )

        # Add action buttons
        self._add_action_buttons()

        # Store reference to current feed
        self.current_feed_id = None
        self.feed_metadata = {}

    def _add_action_buttons(self):
        """Add action buttons for feed operations"""
        # Create button layout
        button_layout = QHBoxLayout()

        # Update Now button
        self.btn_update = QPushButton("Update Now")
        self.btn_update.setToolTip("Manually fetch new items from this feed")
        self.btn_update.clicked.connect(self.update_feed_now)
        button_layout.addWidget(self.btn_update)

        # Clear Items button
        self.btn_clear = QPushButton("Clear Items")
        self.btn_clear.setToolTip("Delete all items from this feed")
        self.btn_clear.clicked.connect(self.clear_feed_items)
        button_layout.addWidget(self.btn_clear)

        # Mark All Read button
        self.btn_mark_read = QPushButton("Mark All Read")
        self.btn_mark_read.setToolTip("Mark all items in this feed as read")
        self.btn_mark_read.clicked.connect(self.mark_all_read)
        button_layout.addWidget(self.btn_mark_read)

        # Add stretch to push buttons to the left
        button_layout.addStretch()

        # Add button layout to main layout
        self.layout.addLayout(button_layout)

        # Add status display area
        from PySide6.QtWidgets import QLabel
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: gray; font-style: italic;")
        self.layout.addWidget(self.status_label)

    def load_config(self, json_config=None):
        """Load feed configuration"""
        if json_config is None:
            json_config = {}

        # Store feed ID if available
        if hasattr(self.parent, 'get_selected_item_id'):
            self.current_feed_id = self.parent.get_selected_item_id()

        # Load metadata if available
        if self.current_feed_id:
            metadata_json = sql.get_scalar("""
                SELECT metadata FROM feeds WHERE id = ?
            """, (self.current_feed_id,))

            if metadata_json:
                self.feed_metadata = json.loads(metadata_json) if metadata_json else {}
            else:
                self.feed_metadata = {}

        # Convert update interval from seconds to display value
        if 'update_interval' in json_config:
            interval_seconds = json_config['update_interval']
            # Find matching display value
            for display_value, seconds in self.schema[3]['map_values'].items():
                if seconds == interval_seconds:
                    json_config['update_interval'] = display_value
                    break

        # Convert categories list to string if needed
        if 'categories' in json_config and isinstance(json_config['categories'], list):
            json_config['categories'] = ', '.join(json_config['categories'])

        # Load configuration
        super().load_config(json_config)

        # Update status display
        self.update_status_display()

        # Enable/disable buttons based on feed state
        self.update_button_states()

    def get_config(self):
        """Get feed configuration"""
        config = super().get_config()

        # Convert update interval to seconds
        if 'update_interval' in config:
            map_values = self.schema[3]['map_values']
            display_value = config['update_interval']
            config['update_interval'] = map_values.get(display_value, 3600)

        # Convert categories string to list
        if 'categories' in config and config['categories']:
            categories_str = config['categories']
            config['categories'] = [cat.strip() for cat in categories_str.split(',') if cat.strip()]
        else:
            config['categories'] = []

        return config

    def update_status_display(self):
        """Update the status label with feed information"""
        if not self.feed_metadata:
            self.status_label.setText("")
            return

        status_parts = []

        # Feed type
        feed_type = self.feed_metadata.get('feed_type', 'unknown')
        status_parts.append(f"Type: {feed_type.upper()}")

        # Last updated
        config = self.get_config()
        if config.get('last_fetched'):
            try:
                last_fetched = datetime.fromisoformat(config['last_fetched'])
                time_diff = datetime.now() - last_fetched
                if time_diff.days > 0:
                    time_str = f"{time_diff.days} day{'s' if time_diff.days > 1 else ''} ago"
                elif time_diff.seconds > 3600:
                    hours = time_diff.seconds // 3600
                    time_str = f"{hours} hour{'s' if hours > 1 else ''} ago"
                else:
                    minutes = time_diff.seconds // 60
                    time_str = f"{minutes} minute{'s' if minutes != 1 else ''} ago"
                status_parts.append(f"Last updated: {time_str}")
            except:
                pass

        # Error status
        if config.get('last_error'):
            error_count = config.get('error_count', 0)
            status_parts.append(f"⚠️ Error ({error_count}x): {config['last_error'][:50]}")

        # Item count
        item_count = self.feed_metadata.get('item_count', 0)
        if item_count > 0:
            status_parts.append(f"Items: {item_count}")

        self.status_label.setText(" | ".join(status_parts))

    def update_button_states(self):
        """Enable/disable buttons based on current state"""
        has_feed = self.current_feed_id is not None
        self.btn_update.setEnabled(has_feed)
        self.btn_clear.setEnabled(has_feed)
        self.btn_mark_read.setEnabled(has_feed)

    def update_feed_now(self):
        """Manually trigger feed update"""
        if not self.current_feed_id:
            return

        try:
            # Import manager
            from plugins.news_feed.managers.feeds import FeedManager

            # Create temporary manager instance
            manager = FeedManager(None)

            # Update the feed
            self.btn_update.setEnabled(False)
            self.btn_update.setText("Updating...")

            new_items, error = manager.update_feed(self.current_feed_id)

            if error:
                QMessageBox.warning(
                    self,
                    "Update Failed",
                    f"Failed to update feed: {error}"
                )
            else:
                QMessageBox.information(
                    self,
                    "Feed Updated",
                    f"Successfully fetched {new_items} new item{'s' if new_items != 1 else ''}."
                )

                # Reload configuration to show updated status
                if hasattr(self.parent, 'load_selected_config'):
                    self.parent.load_selected_config()

                # Emit signal
                self.feed_updated.emit(self.current_feed_id)

        except Exception as e:
            logger.error(f"Failed to update feed: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"An error occurred: {str(e)}"
            )
        finally:
            self.btn_update.setEnabled(True)
            self.btn_update.setText("Update Now")

    def clear_feed_items(self):
        """Clear all items from the current feed"""
        if not self.current_feed_id:
            return

        reply = QMessageBox.question(
            self,
            "Clear Feed Items",
            "Are you sure you want to delete all items from this feed?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                sql.execute("""
                    DELETE FROM feed_items WHERE feed_id = ?
                """, (self.current_feed_id,))

                QMessageBox.information(
                    self,
                    "Items Cleared",
                    "All items have been removed from this feed."
                )

                # Emit signal
                self.feed_updated.emit(self.current_feed_id)

            except Exception as e:
                logger.error(f"Failed to clear feed items: {e}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to clear items: {str(e)}"
                )

    def mark_all_read(self):
        """Mark all items in the current feed as read"""
        if not self.current_feed_id:
            return

        try:
            from plugins.news_feed.managers.feeds import FeedManager

            manager = FeedManager(None)
            manager.mark_all_read(self.current_feed_id)

            QMessageBox.information(
                self,
                "Items Marked as Read",
                "All items in this feed have been marked as read."
            )

            # Emit signal
            self.feed_updated.emit(self.current_feed_id)

        except Exception as e:
            logger.error(f"Failed to mark items as read: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to mark items as read: {str(e)}"
            )

    def save_config(self):
        """Save the configuration"""
        if not self.current_feed_id:
            return

        try:
            config = self.get_config()

            # Handle custom name separately (goes in name column)
            custom_name = self.schema_config.get('custom_name', '').strip()

            # Update database
            if custom_name:
                sql.execute("""
                    UPDATE feeds
                    SET config = ?, name = ?
                    WHERE id = ?
                """, (json.dumps(config), custom_name, self.current_feed_id))
            else:
                sql.execute("""
                    UPDATE feeds
                    SET config = ?
                    WHERE id = ?
                """, (json.dumps(config), self.current_feed_id))

            # Update status display
            self.update_status_display()

        except Exception as e:
            logger.error(f"Failed to save feed config: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to save configuration: {str(e)}"
            )