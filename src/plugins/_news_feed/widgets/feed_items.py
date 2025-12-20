"""
Feed Items Display Widget
Displays and manages RSS/Atom feed items
"""

import json
import logging
import webbrowser
from datetime import datetime

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QListWidget,
                              QListWidgetItem, QLabel, QPushButton, QTextBrowser,
                              QSplitter, QComboBox, QCheckBox, QLineEdit,
                              QMessageBox)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QColor, QBrush

from utils import sql
from plugins.news_feed.managers.feeds import FeedManager

logger = logging.getLogger(__name__)


class FeedItemsWidget(QWidget):
    """Widget for displaying and interacting with feed items"""

    item_read = Signal(int)  # Emitted when an item is marked as read
    item_starred = Signal(int)  # Emitted when an item is starred

    def __init__(self, parent=None):
        super().__init__(parent)

        self.feed_manager = FeedManager(None)
        self.current_feed_id = None
        self.current_item = None
        self.items_data = []

        self.init_ui()
        self.connect_signals()

        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_items)
        self.refresh_timer.start(60000)  # Refresh every minute

    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Top toolbar
        toolbar = self.create_toolbar()
        layout.addLayout(toolbar)

        # Main content splitter
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        # Left panel - items list
        self.items_list = self.create_items_list()
        splitter.addWidget(self.items_list)

        # Right panel - item viewer
        self.item_viewer = self.create_item_viewer()
        splitter.addWidget(self.item_viewer)

        # Set splitter sizes
        splitter.setSizes([400, 600])

    def create_toolbar(self):
        """Create the toolbar with controls"""
        toolbar = QHBoxLayout()

        # Feed selector
        self.feed_combo = QComboBox()
        self.feed_combo.addItem("All Feeds", None)
        self.load_feed_list()
        self.feed_combo.currentIndexChanged.connect(self.on_feed_changed)
        toolbar.addWidget(QLabel("Feed:"))
        toolbar.addWidget(self.feed_combo)

        # View filter
        self.view_combo = QComboBox()
        self.view_combo.addItems(["All Items", "Unread Only", "Starred"])
        self.view_combo.currentIndexChanged.connect(self.on_view_changed)
        toolbar.addWidget(QLabel("View:"))
        toolbar.addWidget(self.view_combo)

        # Search
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search items...")
        self.search_input.textChanged.connect(self.on_search_changed)
        self.search_input.setMaximumWidth(200)
        toolbar.addWidget(self.search_input)

        # Action buttons
        self.btn_refresh = QPushButton("🔄 Refresh")
        self.btn_refresh.clicked.connect(self.refresh_items)
        toolbar.addWidget(self.btn_refresh)

        self.btn_mark_all_read = QPushButton("✓ Mark All Read")
        self.btn_mark_all_read.clicked.connect(self.mark_all_read)
        toolbar.addWidget(self.btn_mark_all_read)

        # Stretch
        toolbar.addStretch()

        # Status label
        self.status_label = QLabel("0 items")
        toolbar.addWidget(self.status_label)

        return toolbar

    def create_items_list(self):
        """Create the feed items list widget"""
        items_list = QListWidget()
        items_list.setAlternatingRowColors(True)
        items_list.itemClicked.connect(self.on_item_clicked)
        items_list.itemDoubleClicked.connect(self.on_item_double_clicked)

        # Custom styling
        items_list.setStyleSheet("""
            QListWidget {
                font-size: 12px;
                outline: none;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #ddd;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
                color: black;
            }
            QListWidget::item:hover {
                background-color: #f5f5f5;
            }
        """)

        return items_list

    def create_item_viewer(self):
        """Create the item content viewer"""
        viewer = QTextBrowser()
        viewer.setOpenExternalLinks(False)  # We'll handle link clicks
        viewer.anchorClicked.connect(self.on_link_clicked)

        # Styling
        viewer.setStyleSheet("""
            QTextBrowser {
                font-size: 14px;
                padding: 10px;
            }
        """)

        return viewer

    def connect_signals(self):
        """Connect widget signals"""
        pass  # Signals already connected in init methods

    def load_feed_list(self):
        """Load the list of feeds for the combo box"""
        try:
            feeds = sql.get_results("""
                SELECT id, name FROM feeds ORDER BY name
            """, return_type='dict')

            for feed in feeds:
                self.feed_combo.addItem(feed['name'], feed['id'])

        except Exception as e:
            logger.error(f"Failed to load feed list: {e}")

    def on_feed_changed(self):
        """Handle feed selection change"""
        self.current_feed_id = self.feed_combo.currentData()
        self.refresh_items()

    def on_view_changed(self):
        """Handle view filter change"""
        self.refresh_items()

    def on_search_changed(self):
        """Handle search text change"""
        search_text = self.search_input.text().lower()
        if len(search_text) < 2 and search_text:  # Don't search single characters
            return

        for i in range(self.items_list.count()):
            item = self.items_list.item(i)
            item_data = item.data(Qt.UserRole)
            if search_text:
                # Search in title and description
                title = item_data.get('config', {}).get('title', '').lower()
                description = item_data.get('config', {}).get('description', '').lower()
                visible = search_text in title or search_text in description
                item.setHidden(not visible)
            else:
                item.setHidden(False)

    def refresh_items(self):
        """Refresh the items list"""
        try:
            # Clear current list
            self.items_list.clear()
            self.items_data = []

            # Get view filter
            view_filter = self.view_combo.currentIndex()
            unread_only = view_filter == 1
            starred_only = view_filter == 2

            # Get items based on current selection
            if self.current_feed_id:
                items = self.feed_manager.get_feed_items(
                    self.current_feed_id,
                    unread_only=unread_only,
                    limit=100
                )
            else:
                items = self.feed_manager.get_all_items(
                    unread_only=unread_only,
                    starred_only=starred_only,
                    limit=100
                )

            # Add items to list
            for item_data in items:
                self.add_item_to_list(item_data)

            # Update status
            total = len(items)
            unread = sum(1 for item in items if not item.get('config', {}).get('read', False))
            self.status_label.setText(f"{total} items ({unread} unread)")

            # Clear viewer if no selection
            if self.items_list.count() == 0:
                self.item_viewer.clear()

        except Exception as e:
            logger.error(f"Failed to refresh items: {e}")

    def add_item_to_list(self, item_data):
        """Add a single item to the list"""
        config = item_data.get('config', {})

        # Create list item
        list_item = QListWidgetItem()

        # Format title and date
        title = config.get('title', 'Untitled')
        pub_date = config.get('pub_date', '')
        feed_name = item_data.get('feed_name', '')

        # Format date
        date_str = ""
        if pub_date:
            try:
                dt = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
                now = datetime.now(dt.tzinfo)
                diff = now - dt

                if diff.days == 0:
                    if diff.seconds < 3600:
                        date_str = f"{diff.seconds // 60}m ago"
                    else:
                        date_str = f"{diff.seconds // 3600}h ago"
                elif diff.days == 1:
                    date_str = "Yesterday"
                elif diff.days < 7:
                    date_str = f"{diff.days}d ago"
                else:
                    date_str = dt.strftime("%b %d")
            except:
                date_str = pub_date[:10] if len(pub_date) >= 10 else ""

        # Build display text
        if feed_name and not self.current_feed_id:  # Show feed name if viewing all feeds
            display_text = f"{title}\n{feed_name} • {date_str}"
        else:
            display_text = f"{title}\n{date_str}"

        # Add star indicator
        if config.get('starred'):
            display_text = "⭐ " + display_text

        list_item.setText(display_text)
        list_item.setData(Qt.UserRole, item_data)

        # Style based on read status
        if not config.get('read'):
            font = list_item.font()
            font.setBold(True)
            list_item.setFont(font)
            # Unread background color
            list_item.setBackground(QBrush(QColor(240, 248, 255)))

        self.items_list.addItem(list_item)
        self.items_data.append(item_data)

    def on_item_clicked(self, item):
        """Handle item selection"""
        item_data = item.data(Qt.UserRole)
        if not item_data:
            return

        self.current_item = item_data
        self.display_item(item_data)

        # Mark as read if unread
        config = item_data.get('config', {})
        if not config.get('read'):
            self.mark_item_read(item_data['id'], True)

            # Update list item styling
            font = item.font()
            font.setBold(False)
            item.setFont(font)
            item.setBackground(QBrush(QColor(255, 255, 255)))

            # Update item data
            config['read'] = True

    def on_item_double_clicked(self, item):
        """Handle item double-click - open in browser"""
        item_data = item.data(Qt.UserRole)
        if item_data:
            link = item_data.get('config', {}).get('link')
            if link:
                webbrowser.open(link)

    def display_item(self, item_data):
        """Display item content in the viewer"""
        config = item_data.get('config', {})

        # Build HTML content
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; padding: 10px; }}
                h2 {{ color: #333; margin-bottom: 5px; }}
                .meta {{ color: #666; font-size: 12px; margin-bottom: 15px; }}
                .content {{ line-height: 1.6; }}
                .actions {{ margin-top: 15px; padding-top: 15px; border-top: 1px solid #ddd; }}
                a {{ color: #1976d2; text-decoration: none; }}
                a:hover {{ text-decoration: underline; }}
            </style>
        </head>
        <body>
        """

        # Title
        title = config.get('title', 'Untitled')
        html += f"<h2>{title}</h2>"

        # Metadata
        meta_parts = []
        if config.get('author'):
            meta_parts.append(f"By {config['author']}")
        if config.get('pub_date'):
            try:
                dt = datetime.fromisoformat(config['pub_date'].replace('Z', '+00:00'))
                meta_parts.append(dt.strftime("%B %d, %Y at %I:%M %p"))
            except:
                meta_parts.append(config['pub_date'])
        if item_data.get('feed_name'):
            meta_parts.append(f"From {item_data['feed_name']}")

        if meta_parts:
            html += f"<div class='meta'>{' • '.join(meta_parts)}</div>"

        # Content
        content = config.get('content') or config.get('description', '')
        if content:
            # Basic HTML sanitization (in production, use proper HTML sanitizer)
            content = content.replace('<script', '&lt;script')
            html += f"<div class='content'>{content}</div>"

        # Actions
        link = config.get('link')
        if link:
            html += f"""
            <div class='actions'>
                <a href='{link}'>Open in Browser →</a>
            </div>
            """

        html += "</body></html>"

        self.item_viewer.setHtml(html)

    def on_link_clicked(self, url):
        """Handle clicks on links in the viewer"""
        webbrowser.open(url.toString())

    def mark_item_read(self, item_id, read=True):
        """Mark an item as read or unread"""
        try:
            self.feed_manager.mark_item_read(item_id, read)
            self.item_read.emit(item_id)
        except Exception as e:
            logger.error(f"Failed to mark item read: {e}")

    def mark_item_starred(self, item_id, starred=True):
        """Mark an item as starred or unstarred"""
        try:
            self.feed_manager.mark_item_starred(item_id, starred)
            self.item_starred.emit(item_id)
        except Exception as e:
            logger.error(f"Failed to mark item starred: {e}")

    def mark_all_read(self):
        """Mark all visible items as read"""
        reply = QMessageBox.question(
            self,
            "Mark All Read",
            "Mark all visible items as read?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                self.feed_manager.mark_all_read(self.current_feed_id)
                self.refresh_items()
            except Exception as e:
                logger.error(f"Failed to mark all as read: {e}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to mark items as read: {str(e)}"
                )

    def closeEvent(self, event):
        """Clean up when widget is closed"""
        self.refresh_timer.stop()
        event.accept()