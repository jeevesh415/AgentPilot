"""
Feed Reader Page
Main interface for reading RSS/Atom feed items
"""

import logging

from PySide6.QtWidgets import QVBoxLayout

from gui.widgets.config_widget import ConfigWidget
from plugins.news_feed.widgets.feed_items import FeedItemsWidget

logger = logging.getLogger(__name__)


class Page_Feed_Reader(ConfigWidget):
    """Main feed reading interface"""

    display_name = "Feed Reader"
    icon_path = ":/resources/icon-info.png"  # Using info icon for reader
    page_type = 'main'  # Show in main navigation

    def __init__(self, parent):
        super().__init__(parent=parent)

        # Create layout for ConfigWidget
        self.layout = QVBoxLayout(self)

        # Add feed items widget
        self.feed_items_widget = FeedItemsWidget(self)
        self.layout.addWidget(self.feed_items_widget)

        # Load initial items
        self.feed_items_widget.refresh_items()

    def load_config(self, config=None):
        """Load configuration (if any)"""
        # Feed reader doesn't have configuration to save
        pass

    def get_config(self):
        """Get configuration (if any)"""
        # Feed reader doesn't have configuration to save
        return {}

    def save_config(self):
        """Save configuration (if any)"""
        # Feed reader doesn't have configuration to save
        pass