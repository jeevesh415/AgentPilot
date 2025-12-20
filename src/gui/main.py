
import asyncio
from datetime import datetime
import json
import os
from pathlib import Path
import sys
import uuid

import PySide6
import qasync
from PySide6.QtWidgets import *
from PySide6.QtCore import Signal, QTimer, QThreadPool, QPropertyAnimation, QEasingCurve, QObject
from PySide6.QtGui import QIcon, QTextDocument, Qt
from typing_extensions import override

# from core.connectors.h5 import append_h5_dataset, create_h5_dataset, tea_kinds
from src.core.connectors.h5 import DATA_DIR, PriceFile
from src.core.connectors.mysql import MysqlConnector
from src.core.connectors.sqlite import SqliteConnector
from src.utils import sql
from src.utils.sql import define_table, get_db_path
from utils.sql_upgrade import upgrade_script
from utils import telemetry  # , sql
from utils.helpers import display_message_box, flatten_list, get_avatar_paths_from_config, display_message
from gui.style import ACCENT_COLOR_1, get_stylesheet
from gui.widgets.config_pages import ConfigPages
from gui.util import CustomMenu, IconButton, clear_layout, find_main_widget, CVBoxLayout, safe_single_shot, set_selected_pages
# from plugins.calligrapher.src.main import test_calligrapher

from gui import system

os.environ["QT_OPENGL"] = "software"

BOTTOM_CORNER_X = 400
BOTTOM_CORNER_Y = 450

PIN_MODE = True


class SystemManager:
    def __init__(self):
        self._main_gui = None

        from core.managers.modules import ModuleManager
        self.modules = ModuleManager(system=self)
        # Managers will be populated here
        # self.apis = APIManager
        # self.agents = AgentManager
        # ....
    
    def reload_managers(self):
        self.modules.load()
        custom_managers = self.modules.get_modules_in_folder(
            module_type='Managers',
            fetch_keys=('name', 'class',)
        )
        for name, mgr in custom_managers:
            if name in self.__dict__:
                continue
            if mgr:
                setattr(self, name, mgr(self))

    def load(self):
        self.reload_managers()

        for name, mgr in self.__dict__.items():
            if name.startswith('_'):
                continue
            print(f'Loading manager: {name}')
            mgr.load()

    def load_manager(self, manager_name):
        mgr = getattr(self, manager_name, None)
        if mgr:
            mgr.load()


# class TutorialHighlightWidget(QWidget):
#     clicked_target = Signal()
#
#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.parent = parent
#         self.setAttribute(Qt.WA_TranslucentBackground)
#         self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
#
#         self.setStyleSheet("border-top-left-radius: 30px;")
#         self.target_pos = QPoint(90, 60)
#         self.target_radius = 50
#         self.message = ""
#
#         self.installEventFilter(self)
#
#     def eventFilter(self, obj, event):
#         if event.type() == QEvent.MouseButtonPress:
#             if (event.pos() - self.target_pos).manhattanLength() <= self.target_radius:
#                 self.clicked_target.emit()
#                 return True
#         return super().eventFilter(obj, event)
#
#     def mousePressEvent(self, event):
#         # call parent mousePressEvent
#         self.parent.mousePressEvent(event)
#
#     def mouseMoveEvent(self, event):
#         # event.ignore()
#         super().mouseMoveEvent(event)
#
#     def paintEvent(self, event):
#         painter = QPainter(self)
#         painter.setRenderHint(QPainter.Antialiasing)
#
#         # Create a path for the entire widget
#         full_path = QPainterPath()
#         full_path.addRect(self.rect())
#
#         # Create a path for the circular cutout
#         circle_path = QPainterPath()
#         circle_path.addEllipse(self.target_pos, self.target_radius, self.target_radius)
#
#         # Subtract the circle path from the full path
#         dimmed_path = full_path.subtracted(circle_path)
#
#         # Draw dimmed overlay
#         painter.setBrush(QColor(0, 0, 0, 128))
#         painter.setPen(Qt.NoPen)
#         painter.drawPath(dimmed_path)
#
#         # Draw circle border
#         painter.setBrush(Qt.NoBrush)
#         painter.setPen(QPen(Qt.white, 2))
#         painter.drawEllipse(self.target_pos, self.target_radius, self.target_radius)
#
#         # Draw message
#         if self.message:
#             painter.setPen(Qt.white)
#             painter.drawText(self.rect(), Qt.AlignBottom | Qt.AlignHCenter, self.message)
#
#     def set_target(self, pos, radius, message=""):
#         self.target_pos = pos
#         self.target_radius = radius
#         self.message = message
#         self.update()


class TOSDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Terms of Use")
        self.setWindowIcon(QIcon(':/resources/icon.png'))
        self.setMinimumSize(300, 350)
        self.resize(300, 350)

        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowSystemMenuHint | Qt.WindowCloseButtonHint)

        layout = QVBoxLayout(self)

        self.tos_label = QTextEdit("""
The material embodied in this software is provided to you "as-is" and without warranty of any kind, express, implied or otherwise, including without limitation, any warranty of fitness for a particular purpose. 
In no event shall Agent Pilot or it's creators be liable to you or anyone else for any direct, special, incidental, indirect or consequential damages of any kind, or any damages whatsoever, including but not limited to, loss of profit, loss of use, savings or revenue, or the claims of third parties, whether or not Agent Pilot creators have been advised of the possibility of such loss, however caused and on any theory of liability, arising out of or in connection with the possession, use or performance of this software.
"""
                                )
        self.tos_label.setReadOnly(True)
        self.tos_label.setFrameStyle(QFrame.NoFrame)

        layout.addWidget(self.tos_label)

        h_layout = QHBoxLayout()
        h_layout.addStretch(1)

        self.decline_button = QPushButton("Decline")
        self.decline_button.setFixedWidth(100)
        self.decline_button.clicked.connect(self.reject)
        h_layout.addWidget(self.decline_button)

        self.agree_button = QPushButton("Agree")
        self.agree_button.setFixedWidth(100)
        self.agree_button.clicked.connect(self.accept)
        h_layout.addWidget(self.agree_button)

        layout.addLayout(h_layout)


class TitleButtonBar(CustomMenu):
    def __init__(self, parent):
        super().__init__(parent=parent)
        self.icon_size = 12
        self.schema = [
            {
                'text': 'Minimize',
                'icon_path': ':/resources/icon-minimize.png',
                'target': self.minimizeApp,
            },
            {
                'text': 'Maximize',
                'icon_path': ':/resources/icon-maximize.png',
                'target': self.maximizeApp,
            },
            {
                'text': 'Close',
                'icon_path': ':/resources/close.png',
                'target': self.closeApp,
            },
        ]
        self.create_toolbar()

    def minimizeApp(self):
        self.window().showMinimized()

    def maximizeApp(self):
        if self.window().isMaximized():
            self.window().showNormal()
        else:
            self.window().showMaximized()

    def closeApp(self):
        self.window().close()


#     # def toggleNotifications(self):
#     #     pass
#     #     # self.main.notification_manager.setVisible(self.notif_button.isChecked())

#     # class NotificationIconButton(ToggleIconButton):
#     #     """Toggle button with a notification number bubble"""
#     #     def __init__(self, **kwargs):
#     #         super().__init__(**kwargs)
#     #         self.setFixedSize(20, 20)
#     #         self.bubble_number = 67697

#     #     def set_bubble_number(self, n):
#     #         """Set the number to display in the notification bubble"""
#     #         self.bubble_number = n
#     #         self.update()  # Trigger a repaint

#     #     def paintEvent(self, event):
#     #         """Override paint event to draw the bubble"""
#     #         super().paintEvent(event)

#     #         if self.bubble_number > 0:
#     #             painter = QPainter()
#     #             if not painter.begin(self):
#     #                 return

#     #             try:
#     #                 painter.setRenderHint(QPainter.Antialiasing)

#     #                 # Define bubble size and position
#     #                 bubble_size = 20
#     #                 bubble_x = self.width() - bubble_size - 2
#     #                 bubble_y = 2

#     #                 # Draw the red circle

#     #                 painter.setBrush(QColor(ACCENT_COLOR_1))  # Red color
#     #                 painter.setPen(Qt.NoPen)
#     #                 painter.drawEllipse(bubble_x, bubble_y, bubble_size, bubble_size)

#     #                 # Draw the number text
#     #                 painter.setPen(Qt.white)
#     #                 font = QFont()
#     #                 font.setPointSize(8)
#     #                 font.setBold(True)
#     #                 painter.setFont(font)

#     #                 # Format the number (show 99+ for numbers > 99)
#     #                 text = str(self.bubble_number) if self.bubble_number <= 99 else "99+"

#     #                 # Draw text centered in the bubble
#     #                 text_rect = PySide6.QtCore.QRect(bubble_x, bubble_y, bubble_size, bubble_size)
#     #                 painter.drawText(text_rect, Qt.AlignCenter, text)
#     #             finally:
#     #                 painter.end()

    #     # def paintEvent(self, event):
    #     #     """Override paint event to draw the bubble"""
    #     #     super().paintEvent(event)

    #     #     if self.bubble_number > 0:
    #     #         painter = QPainter(self)
    #     #         painter.setRenderHint(QPainter.Antialiasing)

    #     #         # Define bubble size and position
    #     #         bubble_size = 20
    #     #         bubble_x = self.width() - bubble_size - 2
    #     #         bubble_y = 2

    #     #         # Draw the red circle
                
    #     #         painter.setBrush(QColor(ACCENT_COLOR_1))  # Red color
    #     #         painter.setPen(Qt.NoPen)
    #     #         painter.drawEllipse(bubble_x, bubble_y, bubble_size, bubble_size)

    #     #         # Draw the number text
    #     #         painter.setPen(Qt.white)
    #     #         font = QFont()
    #     #         font.setPointSize(8)
    #     #         font.setBold(True)
    #     #         painter.setFont(font)

    #     #         # Format the number (show 99+ for numbers > 99)
    #     #         text = str(self.bubble_number) if self.bubble_number <= 99 else "99+"

    #     #         # Draw text centered in the bubble
    #     #         text_rect = PySide6.QtCore.QRect(bubble_x, bubble_y, bubble_size, bubble_size)
    #     #         painter.drawText(text_rect, Qt.AlignCenter, text)

    #     #         painter.end()


class MainPages(ConfigPages):
    def __init__(self, parent):
        super().__init__(
            parent=parent,
            default_page='chat',
            right_to_left=True,
            bottom_to_top=True,
            button_kwargs=dict(
                button_type='icon',
                icon_size=50
            ),
        )
        self.parent = parent
        self.main = parent
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.build_schema()

    @override
    def build_schema(self):
        from utils import sql
        pinned_pages: list = sql.get_scalar(
            "SELECT `value` FROM settings WHERE `field` = 'pinned_pages';",
            load_json=True
        )
        page_definitions = system.manager.modules.get_modules_in_folder(
            module_type='Pages',
            fetch_keys=('uuid', 'name', 'class',),
        )
        page_definitions = [  # filter out pages that are not main or pinned
            (module_id, module_name, page_class)
            for module_id, module_name, page_class in page_definitions
            if getattr(page_class, 'page_type', 'any') == 'main'
            or (getattr(page_class, 'page_type', 'any') == 'any' and module_name in pinned_pages)
        ]
        preferred_order = ['chat', 'contexts', 'agents', 'blocks', 'tools', 'modules']
        locked_below = ['settings']
        locked_above = ['chat', 'contexts', 'agents', 'blocks', 'tools', 'modules']
        order_column = 1
        if preferred_order:
            order_idx = {name: i for i, name in enumerate(preferred_order)}
            page_definitions.sort(key=lambda x: order_idx.get(x[order_column], len(preferred_order)))
        
        # sort so locked_below are at the bottom
        page_definitions.sort(key=lambda x: x[1] in locked_below)

        new_pages = {}
        for page_name in locked_above:
            if page_name in self.pages and page_name in [page[1] for page in page_definitions]:
                new_pages[page_name] = self.pages[page_name]
        for module_id, module_name, page_class in page_definitions:
            try:
                # new_pages[module_name] = page_class(parent=self)
                page = page_class(parent=self)
                setattr(page, 'module_id', module_id)
                existing_page = self.pages.get(module_name, None)
                if existing_page and getattr(existing_page, 'user_editing', False):
                    setattr(page, 'user_editing', True)

                if hasattr(page, 'add_breadcrumb_widget') and getattr(page, 'show_breadcrumbs', True):
                    page.add_breadcrumb_widget()

                new_pages[module_name] = page

            except Exception as e:
                display_message(f"Error loading page '{module_name}': {e}", 'Error', QMessageBox.Warning)

        for page_name in locked_below:
            if page_name in self.pages and page_name in [page[1] for page in page_definitions]:
                new_pages[page_name] = self.pages[page_name]

        self.pages = new_pages

        super().build_schema()

        self.settings_sidebar.setFixedWidth(70)

    def add_page(self):
        dlg_title, dlg_prompt = ('New page name', 'Enter a new name for the new page')
        text, ok = QInputDialog.getText(self, dlg_title, dlg_prompt)
        if not ok:
            return
    
        system.manager.modules.add(name=text, module_type='Pages')
    
        main = find_main_widget(self)
        main.main_pages.build_schema()
        # main.page_settings.build_schema()
        main.main_pages.settings_sidebar.toggle_page_pin(text, True)
        page_btn = main.main_pages.settings_sidebar.page_buttons.get(text, None)
        if page_btn:
            page_btn.click()
            main.main_pages.edit_page(text)


class NotificationWidget(QWidget):
    closed = Signal(QObject)

    def __init__(self, parent=None, color=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.main = parent.main
        # Handle color defaults and conversions
        if not color:
            color = '#ff6464'
        elif color == 'blue':
            color = '#438BB9'
        elif color == 'red':
            color = '#ff6464'
        elif not color.startswith('#'):
            color = '#ff6464'

        # Create the main layout
        self.outer_layout = QVBoxLayout(self)
        self.outer_layout.setContentsMargins(0, 0, 0, 0)
        self.outer_layout.setSpacing(0)

        # Create the content container
        self.content = QWidget(self)
        self.content.setStyleSheet(f"""
            background-color: {color};
            border-radius: 10px;
            color: white;
        """)

        # Inner layout for the content
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(12, 10, 12, 10)
        self.content_layout.setSpacing(0)

        # Create text label with proper wrapping
        self.label = QLabel()
        self.label.setWordWrap(True)
        self.label.setStyleSheet("color: white; font-size: 11pt;")
        self.label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        self.content_layout.addWidget(self.label)

        # Add content to outer layout
        self.outer_layout.addWidget(self.content)

        # Set size policies
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        self.setMaximumWidth(300)

        # Initialize with zero height
        self.content.setMinimumHeight(0)
        self.content.setMaximumHeight(0)

        # Setup timer for auto-hide
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide_animation)

        # Setup animation
        self.animation = QPropertyAnimation(self.content, b"maximumHeight")
        self.animation.setEasingCurve(QEasingCurve.InOutCubic)
        self.animation.finished.connect(self.on_animation_finished)

    def show_message(self, message, duration=5000):
        # Set the message
        self.label.setText(message)

        # Calculate proper size based on text
        self.label.adjustSize()
        text_width = min(self.label.sizeHint().width(), 280)  # Account for padding

        # Create a temporary document to calculate proper text height
        doc = QTextDocument()
        doc.setDefaultFont(self.label.font())
        doc.setHtml(message)
        doc.setTextWidth(text_width)

        # Calculate target height with margins
        target_height = doc.size().height() + 20  # Add some padding

        # Reset animation and height
        self.animation.stop()
        self.content.setMaximumHeight(0)

        # Start show animation
        self.animation.setStartValue(0)
        self.animation.setEndValue(target_height)
        self.animation.setDuration(250)
        self.animation.start()

        if not self.main.isMinimized():
            # Start timer for auto-hide
            self.timer.start(duration)

    def hide_animation(self):
        # Start hide animation
        current_height = self.content.height()
        self.animation.stop()
        self.animation.setStartValue(current_height)
        self.animation.setEndValue(0)
        self.animation.setDuration(250)
        self.animation.start()

    def on_animation_finished(self):
        if self.content.maximumHeight() == 0:
            self.hide()
            self.closed.emit(self)

    def enterEvent(self, event):
        self.timer.stop()
        event.accept()

    def leaveEvent(self, event):
        self.timer.start(3000)
        event.accept()


class NotificationManager(QWidget):
    def __init__(self, parent):
        super().__init__(parent=parent)
        self.main = parent
        self.setFixedWidth(300)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

        # Main layout for stacking notifications
        self.layout = CVBoxLayout(self)
        self.layout.setSpacing(6)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setAlignment(Qt.AlignTop)

        self.notifications = []

    def show_notification(self, message, title, icon='Information', color=None, duration=5000):
        is_minimized = self.main.isMinimized()
        if is_minimized:
            icon = getattr(QSystemTrayIcon, icon, QSystemTrayIcon.Information)
            self.main.tray.showMessage(
                title,
                message,
                icon,
                duration  # duration in ms
            )
            # self.tray.showMessage(message, color)
            return
        
        # Create new notification
        notification = NotificationWidget(self, color=color)
        notification.closed.connect(self.remove_notification)

        # Add to layout
        self.layout.addWidget(notification)
        self.notifications.append(notification)

        # Display the notification
        notification.show_message(message, duration)
        # self.setVisible(True)
        self.update_position()

        print(message)

    def remove_notification(self, notification):
        if notification in self.notifications:
            self.notifications.remove(notification)
            self.layout.removeWidget(notification)
            notification.deleteLater()

        # if not self.notifications:
        #     self.hide()
        # else:
        # if self.notifications:
        self.update_position()

    def update_position(self):
        # Position in top right corner of main window with padding
        # visible = self.notifications is not None and not self.main.isMinimized()
        # self.setVisible(visible)
        # if not visible:
        #     return
        self.move(self.main.x() + self.main.width() - self.width() - 90,
                 self.main.y() + 50)
        self.adjustSize()


def migrate_tables():

    main_db_path = get_db_path()
    fin_db_path = os.path.join(os.path.dirname(main_db_path), 'finance.db')
    # create the finance.db sqlite3 database if it doesn't exist
    if os.path.exists(fin_db_path):
        os.remove(fin_db_path)

    other_conn = SqliteConnector(db_path=fin_db_path)

    other_conn.execute("""
        CREATE TABLE "apis" (
            "id"	INTEGER,
            "name"	TEXT NOT NULL,
            PRIMARY KEY("id" AUTOINCREMENT)
        )
    """)
    other_conn.execute("""
        CREATE TABLE "assets" (
            "id"	INTEGER,
            "api_id"	INTEGER NOT NULL,
            "api_asset_id"	TEXT NOT NULL,
            "name"	TEXT NOT NULL,
            "symbol"	TEXT NOT NULL,
            "kind"	TEXT DEFAULT NULL,
            "group_to"	INTEGER DEFAULT NULL,
            "metadata"	TEXT NOT NULL DEFAULT '{}',
            "last_update"	TEXT NOT NULL DEFAULT '{}',
            "last_price"	NUMERIC DEFAULT 0,
            PRIMARY KEY("id" AUTOINCREMENT)
        )
    """)
    other_conn.execute("""
        CREATE TABLE "markets" (
            "id"	INTEGER,
            "api_id"	INTEGER NOT NULL,
            "market_id"	TEXT NOT NULL,
            "base_asset"	TEXT DEFAULT NULL,
            "quote_asset"	TEXT DEFAULT NULL,
            "base_symb"	TEXT NOT NULL,
            "quote_symb"	TEXT NOT NULL,
            PRIMARY KEY("id" AUTOINCREMENT)
        )
    """)
    other_conn.execute("""
        CREATE TABLE "trades" (
            "id"	INTEGER,
            "unix"	INTEGER NOT NULL,
            "trade_id"	TEXT NOT NULL,
            "exchange"	TEXT NOT NULL,
            "asset_sold"	INTEGER NOT NULL,
            "amt_sold"	NUMERIC NOT NULL,
            "asset_received"	INTEGER NOT NULL,
            "amt_received"	NUMERIC NOT NULL,
            "fee_asset"	INTEGER NOT NULL,
            "fee_amt"	NUMERIC NOT NULL,
            "category"	TEXT NOT NULL DEFAULT '',
            "symb_asset_sold"	TEXT DEFAULT '',
            "symb_asset_received"	TEXT DEFAULT '',
            "symb_fee_asset"	TEXT DEFAULT '',
            "notes"	TEXT NOT NULL DEFAULT '',
            "ignored"	INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY("id" AUTOINCREMENT)
        )
    """)
    other_conn.execute("""
        CREATE TABLE "depwiths" (
            "id"	INTEGER,
            "unix"	INTEGER NOT NULL,
            "depwith"	INTEGER NOT NULL,
            "user_id"	INTEGER NOT NULL,
            "ins_shares"	INTEGER NOT NULL,
            "ins_amt"	NUMERIC NOT NULL,
            "tot_pot"	NUMERIC NOT NULL,
            "ignore"	INTEGER NOT NULL,
            "questionable"	INTEGER NOT NULL,
            "asset_symb"	TEXT NOT NULL,
            "asset_id"	INTEGER DEFAULT NULL,
            "asset_amt"	NUMERIC DEFAULT 0,
            "note"	TEXT NOT NULL DEFAULT '',
            PRIMARY KEY("id" AUTOINCREMENT)
        )
    """)
    other_conn.execute("""
        CREATE TABLE "files" (
            "id"	INTEGER,
            "file_id"	TEXT NOT NULL,
            "file_path"	TEXT NOT NULL,
            PRIMARY KEY("id" AUTOINCREMENT)
        )
    """)

    other_conn.execute("""
        CREATE TABLE "users" (
            "id"	INTEGER,
            "name"	TEXT NOT NULL,
            "shares"	INTEGER NOT NULL,
            PRIMARY KEY("id" AUTOINCREMENT)
        )
    """)
    
    # DEPWITHS
    mysql_conn = MysqlConnector()
    depwiths_rows = mysql_conn.get_results("""
        SELECT 
            dte,
            depWith,
            user,
            insShares,
            insAmt,
            old_totPot,
            asset_symb,
            asset,
            asset_amt,
            `ignore`,
            questionable,
            note
        FROM mfDepsWiths
        WHERE mf_depwith_group = ''
    """)
    c_depwiths_rows = [
        (
            row[0].timestamp(),
            row[1],
            row[2],
            row[3],
            row[4],
            row[5],
            row[6],
            row[7],
            row[8],
            row[9],
            row[10],
            row[11],
        )
        for row in depwiths_rows
    ]
    other_conn.execute(f"""
        INSERT INTO depwiths (
            unix, 
            depwith, 
            user_id, 
            ins_shares, 
            ins_amt, 
            tot_pot, 
            asset_symb, 
            asset_id, 
            asset_amt, 
            `ignore`, 
            questionable, 
            note
        )
        VALUES {', '.join(['(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'] * len(c_depwiths_rows))}
    """, flatten_list(c_depwiths_rows))

    # TRADES
    trades_rows = mysql_conn.get_results("""
        SELECT 
            timestamp_opened,
            trade_id,
            exchange,
            asset_sold,
            amt_sold,
            asset_received,
            amt_received,
            fee_asset,
            fee_amt,
            category,
            notes,
            symb_asset_sold,
            symb_asset_received,
            symb_fee_asset,
            ignored
        FROM trades
        WHERE user_group = 2
    """)
    c_trades_rows = [
        (
            row[0].timestamp(),
            row[1],
            row[2],
            row[3],
            row[4],
            row[5],
            row[6],
            row[7],
            row[8],
            row[9],
            row[10],
            row[11],
            row[12],
            row[13],
            row[14],
        )
        for row in trades_rows
    ]
    other_conn.execute(f"""
        INSERT INTO trades (
            unix, 
            trade_id, 
            exchange, 
            asset_sold, 
            amt_sold, 
            asset_received, 
            amt_received, 
            fee_asset, 
            fee_amt, 
            category, 
            notes, 
            symb_asset_sold, 
            symb_asset_received, 
            symb_fee_asset, 
            ignored
        )
        VALUES {', '.join(['(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'] * len(c_trades_rows))}
    """, flatten_list(c_trades_rows))

    # USERS
    users_rows = mysql_conn.get_results("""
        SELECT 
            id,
            name,
            shares
        FROM users
        WHERE user_group = 2
    """)
    other_conn.execute(f"""
        INSERT INTO users (
            id, 
            name, 
            shares
        )
        VALUES {', '.join(['(?, ?, ?)'] * len(users_rows))}
    """, flatten_list(users_rows))

    # # ASSETS
    assets_rows = mysql_conn.get_results("""
        SELECT 
            a.id,
            a.api_id,
            a.api_asset_id,
            a.name,
            a.symb,
            '', -- UPPER(t.`type`),
            a.group_id,
            a.metadata,
            a.last_update
        FROM assets a
    """)
    # batches of 10_000
    if assets_rows:
        for i in range(0, len(assets_rows), 10_000):
            batch = assets_rows[i:i+10_000]
            if not batch:
                continue
            other_conn.execute(f"""
                INSERT INTO assets (
                    id,
                    api_id,
                    api_asset_id,
                    name,
                    symbol,
                    kind,
                    group_to,
                    metadata,
                    last_update,
                    last_price
                )
                VALUES {', '.join(['(?, ?, ?, ?, ?, ?, ?, ?, ?, 0)'] * len(batch))}
            """, flatten_list(batch))

    pass

    # table_col_map = {
    #     'mfDepsWiths': {
    #         'new_name': 'depwiths',
    #         'columns': {
    #             'unix': 'unix',
    #             'depWith': 'depWith',
    #             'user': 'user',
    #             'ins_shares': 'ins_shares',
    #             'ins_amt': 'ins_amt',
    #             'tot_pot': 'tot_pot',
    #         }
    # }

class Main(QMainWindow):
    def __init__(self):
        super().__init__()

        # migrate_tables()
        # sys.exit(0)

        # # scan_file_ids()
        # # sys.exit(0)

        self._mousePressed = False
        self._mousePos = None
        self._mouseGlobalPos = None
        self._resizing = False
        self._resizeMargins = 10  # Margin in pixels to detect resizing

        self.setWindowTitle('AgentPilot')
        self.setWindowIcon(QIcon(':/resources/icon.png'))

        self.main = self  # workaround for bubbling up

        self.threadpool = QThreadPool()

        self.central = QWidget()
        self.central.setProperty("class", "central")
        self.setCentralWidget(self.central)
        self.layout = QVBoxLayout(self.central)

        self.setMouseTracking(True)
        self.setAcceptDrops(True)

        self.title_bar = TitleButtonBar(parent=self)
        system.manager = SystemManager()
        system.manager._main_gui = self

        # Initialize the notification manager
        self.notification_manager = NotificationManager(self)
        self.notification_manager.show()

        self.init_app()

        # Create tray icon (required for notifications)
        self.tray = QSystemTrayIcon()
        self.tray.setIcon(QIcon(':/resources/icon.png'))
        self.tray.show()

        safe_single_shot(2000, system.manager.daemons.start_all_daemons)
    
    def init_app(self):
        clear_layout(self.layout)

        # migrate_old_format('/home/jb/Desktop/CRYP/PRICE/BINANCE/0/BINANCE_ETHBTC_raw.h5')
        # migrate_old_format('/home/jb/Desktop/CRYP/PRICE/BINANCE/0/BINANCE_LTCBTC_raw.h5')

        # self.check_if_app_already_running()
        telemetry.initialize()

        self.check_db()
        self.patch_db()

        # if not test_mode:  # workaround for dialog block todo
        self.check_tos()

        from utils.reset import ensure_system_folders
        ensure_system_folders()

        # system.manager = SystemManager()
        # system.manager._main_gui = self
        system.manager.load()

        if 'AP_DEV_MODE' in os.environ.keys():
            from utils.reset import bootstrap
            # reset_table(table_name='modules')
            bootstrap()

        get_stylesheet()  # init stylesheet

        # telemetry.set_uuid(self.get_uuid())
        # telemetry.send('user_login')
        self.test_running = False
        self.page_history = []

        always_on_top = system.manager.config.get('system.always_on_top', True)
        current_flags = self.windowFlags()
        new_flags = current_flags
        if always_on_top:
            new_flags |= Qt.WindowStaysOnTopHint
        else:
            new_flags &= ~Qt.WindowStaysOnTopHint
        self.setWindowFlags(new_flags)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)

        self.main_pages = MainPages(self)

        self.layout.addWidget(self.main_pages)

        self.side_bubbles = self.SideBubbles(self)
        # is_in_ide = 'AP_DEV_MODE' in os.environ
        # dev_mode_state = True if is_in_ide else None
        # self.main_menu.pages['Settings'].pages['System'].widgets[1].toggle_dev_mode(dev_mode_state)

        from utils import sql
        window_size = sql.get_scalar("SELECT value FROM settings WHERE `field` = 'window_size'", load_json=True)
        if not window_size:
            window_size = {}
        self.resize(window_size.get('width', 720), window_size.get('height', 900))

        # self.main_menu.settings_sidebar.btn_new_context.setFocus()
        self.apply_stylesheet()
        self.apply_margin()

        app_config = system.manager.config
        self.main_pages.pages['settings'].load_config(app_config)

        screen_geometry = QApplication.primaryScreen().availableGeometry()
        new_x = screen_geometry.x() + screen_geometry.width() - self.width()
        new_y = screen_geometry.y() + screen_geometry.height() - self.height()
        self.move(new_x, new_y)

        self.notification_manager.update_position()

        self.main_pages.build_schema()
        page_path = sql.get_scalar("SELECT value FROM settings WHERE `field` = 'page_path'", load_json=True)
        if page_path:
            set_selected_pages(self.main_pages, page_path)
        self.main_pages.load()

        # # system.manager.modules.test_modules()
        # QTimer.singleShot(100, system.manager.modules.test_modules)

    @property  # todo remove
    def page_chat(self):
        return self.main.main_pages.get('chat')

    def get_uuid(self):
        from utils import sql
        my_uuid = sql.get_scalar("SELECT value FROM settings WHERE `field` = 'my_uuid'")
        if my_uuid == '':
            my_uuid = str(uuid.uuid4())
            sql.execute("UPDATE settings SET value = ? WHERE `field` = 'my_uuid'", (my_uuid,))
        return my_uuid

    def check_tos(self):
        from utils import sql
        is_accepted = sql.get_scalar("SELECT value FROM settings WHERE `field` = 'accepted_tos'")
        if is_accepted == '1':
            return

        dialog = TOSDialog()
        if dialog.exec() == QDialog.Accepted:
            sql.execute("UPDATE settings SET value = '1' WHERE `field` = 'accepted_tos'")
            return
        else:
            sys.exit(0)

    def check_db(self):
        from utils import sql
        # Check if the database is up-to-date
        try:
            upgrade_db = sql.check_database_upgrade()
            if upgrade_db:
                # ask confirmation first
                if QMessageBox.question(None, "Database outdated",
                                        "Do you want to upgrade the database to the newer version?",
                                        QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
                    # exit the app
                    sys.exit(0)

                db_version = upgrade_db
                upgrade_script.upgrade(current_version=db_version)

        except Exception as e:
            display_message_box(icon=QMessageBox.Critical, title="Error", text=str(e), buttons=QMessageBox.Ok)
            sys.exit(0)

    def patch_db(self):
        from utils import sql

        # in `settings`.`app_config`, rename `display.parameter_color` to `display.accent_color_1` and `display.structure_color` to `display.accent_color_2`
        app_config = sql.get_scalar("SELECT value FROM settings WHERE `field` = 'app_config'", load_json=True)
        if app_config:
            if 'display.parameter_color' in app_config:
                app_config['display.accent_color_1'] = app_config.pop('display.parameter_color')
                app_config['display.accent_color_2'] = app_config.pop('display.structure_color')
                sql.execute("UPDATE settings SET value = ? WHERE `field` = 'app_config'", (json.dumps(app_config),))

        # add 'finance_config' to settings table
        if not sql.get_scalar("SELECT value FROM settings WHERE `field` = 'finance_config'"):
            sql.execute("INSERT INTO settings (field, value) VALUES ('finance_config', '{}')")

        # update the json field  `roles`.`config`, set 'hide_bubbles' to
        audio_config = json.dumps({"bubble_bg_color": "#003b3b3b", "bubble_text_color": "#ff818365"})
        sql.execute("UPDATE roles SET config = ? WHERE name = 'audio'", (audio_config,))

        # add enhancement_blocks to settings table
        if not sql.get_scalar("SELECT value FROM settings WHERE `field` = 'enhancement_blocks'"):
            sql.execute("INSERT INTO settings (field, value) VALUES ('enhancement_blocks', '{}')")

        # if 'modules' is in `roles`.`config` WHERE `name` = 'user'
        has_module_field = sql.get_scalar("SELECT json_extract(config, '$.module') FROM roles WHERE name = 'user'")
        if not has_module_field:
            sql.execute("UPDATE roles SET config = json_set(config, '$.module', ?) WHERE name = 'audio'", ('AudioBubble',))
            sql.execute("UPDATE roles SET config = json_set(config, '$.module', ?) WHERE name = 'code'", ('CodeBubble',))
            sql.execute("UPDATE roles SET config = json_set(config, '$.module', ?) WHERE name = 'tool'", ('ToolBubble',))
            sql.execute("UPDATE roles SET config = json_set(config, '$.module', ?) WHERE name = 'result'", ('ResultBubble',))
            sql.execute("UPDATE roles SET config = json_set(config, '$.module', ?) WHERE name = 'image'", ('ImageBubble',))
            sql.execute("UPDATE roles SET config = json_set(config, '$.module', ?) WHERE name = 'user'", ('UserBubble',))
            sql.execute("UPDATE roles SET config = json_set(config, '$.module', ?) WHERE name = 'assistant'", ('AssistantBubble',))

        sql.ensure_column_in_tables(
            tables=[
                'modules',
                'entities',
                'blocks',
                'tools',
                'environments',
            ],
            column_name='baked',
            column_type='INTEGER',
            default_value="0",
            not_null=True,
        )
        sql.ensure_column_in_tables(
            tables=[
                'folders',
            ],
            column_name='uuid',
            column_type='TEXT',
            default_value="""(
                lower(hex(randomblob(4))) || '-' ||
                lower(hex(randomblob(2))) || '-' ||
                '4' || substr(lower(hex(randomblob(2))), 2) || '-' ||
                substr('89ab', abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))), 2) || '-' ||
                lower(hex(randomblob(6)))
            )""",
            not_null=True,
        )
        sql.ensure_column_in_tables(
            tables=[
                'blocks',
            ],
            column_name='parent_id',
            column_type='INTEGER',
            default_value='NULL',
            not_null=False,
        )

        # sql.execute("UPDATE folders SET name = 'Roles' WHERE name = 'Bubbles' and `type` = 'modules' and `locked` = 1")
        
        # add window_size to settings table
        if not sql.get_scalar("SELECT value FROM settings WHERE `field` = 'window_size'"):
            sql.execute("INSERT INTO settings (field, value) VALUES ('window_size', '{}')")
        # add page_path to settings table
        if not sql.get_scalar("SELECT value FROM settings WHERE `field` = 'page_path'"):
            sql.execute("INSERT INTO settings (field, value) VALUES ('page_path', '{}')")
        
        sql.ensure_column_in_tables(
            tables=['models'],
            column_name='metadata',
            column_type='TEXT',
            default_value='{}',
            not_null=True,
        )
        sql.ensure_column_in_tables(
            tables=['models'],
            column_name='provider_plugin',
            column_type='TEXT',
            default_value='litellm',
            not_null=True,
        )
        # # rename `entities` to `agents`
        # if sql.get_scalar("SELECT name FROM tables WHERE name = 'entities'"):
        #     sql.execute("ALTER TABLE entities RENAME TO agents")

            # ensure_column_in_tables(
        #     tables=['modules'],
        #     column_name='kind',
        #     column_type='TEXT',
        #     default_value='',  # todo - empty string default?
        #     not_null=True,
        # )
        # # if any items in `folders` table has `locked` = 1
        # locked_folders = sql.get_results("SELECT id, name FROM folders WHERE type = 'modules' AND locked = 1", return_type='dict')
        # if locked_folders:
        #     for folder_id, folder_name in locked_folders.items():
        #         folder_modules = sql.get_results(f"SELECT id FROM modules WHERE folder_id = ?",
        #                                          (folder_id,), return_type='list')
        #         for module_id in folder_modules:
        #             # set `kind` to folder_name
        #             sql.execute("UPDATE modules SET kind = ?, folder_id = NULL WHERE id = ?",
        #                         (folder_name.upper(), module_id))
        #     # delete locked folders
        #     sql.execute("DELETE FROM folders WHERE type = 'modules' and locked = 1")

    # def check_if_app_already_running(self):
    #     # if not getattr(sys, 'frozen', False):
    #     #     return  # Don't check if we are running in ide
    #
    #     current_pid = os.getpid()  # Get the current process ID
    #
    #     for proc in psutil.process_iter(['pid', 'name']):
    #         try:
    #             proc_info = proc.as_dict(attrs=['pid', 'name'])
    #             if proc_info['pid'] != current_pid and 'AgentPilot' in proc_info['name']:
    #                 raise Exception("Another instance of the application is already running.")
    #         except (psutil.NoSuchProcess, psutil.AccessDenied):
    #             # If the process no longer exists or there's no permission to access it, skip it
    #             continue

    def show_side_bubbles(self):
        self.side_bubbles.show()
        # move to top left of the main window
        self.side_bubbles.move(self.x() - self.side_bubbles.width(), self.y())

    # def hide_side_bubbles(self):
    #     print("hide side bubbles")
    #     self.side_bubbles.hide()

    class SideBubbles(QWidget):
        def __init__(self, main):
            super().__init__(parent=None)
            self.main = main
            self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
            self.setAttribute(Qt.WA_TranslucentBackground)
            self.setFixedWidth(50)

            # allow mouseMoveEvent
            self.setMouseTracking(True)

            # show 3 circles 50x50 px vertically
            self.layout = CVBoxLayout(self)

            self.load()

        def load(self):
            from utils import sql
            recent_chats = sql.get_results("""
                SELECT config
                FROM contexts
                WHERE kind = 'CHAT'
                ORDER BY id DESC
                LIMIT 3
            """, return_type='list')

            for config in recent_chats:
                row_layout = QHBoxLayout()
                config = json.loads(config)
                member_paths = get_avatar_paths_from_config(config)
                # member_pixmap = path_to_pixmap(member_paths, diameter=50)
                label = IconButton(  #) QLabel()
                    parent=self,
                    icon_path=member_paths,  # default icon
                    size=50,
                    opacity=0.75,
                    icon_size_percent=0.5,
                )

                # # when label is hovered, show a 1px border
                # # set transparent background
                # label.setStyleSheet("background-color: transparent;")
                # # set border radius to 25px
                #border-radius: 25px; border: 1px solid transparent; background-color: transparent;
                # label.setStyleSheet("""
                #     background-color: transparent;
                #     border-radius: 25px;
                #     border: 1px solid transparent;
                #     padding: 5px;
                # """)
                # set hovered background color to #ffffff20
                # label.setProperty("class", "bubble")
                # label.setPixmap(member_pixmap)
                row_layout.addWidget(label)
                self.layout.addLayout(row_layout)

        def mouseMoveEvent(self, event):
            # If the mouse is more than 50px away from any edge of side bubbles, hide it
            left_distance = event.globalX() - self.x()
            right_distance = self.x() + self.width() - event.globalX()
            top_distance = event.globalY() - self.y()
            bottom_distance = self.y() + self.height() - event.globalY()
            if left_distance < -50 or right_distance < -50 or \
               top_distance < -50 or bottom_distance < -50:
                self.hide()

    def position_title_bar(self):
        x = self.width() - self.title_bar.sizeHint().width()
        self.title_bar.move(x, 0)
        self.title_bar.raise_()

    def apply_stylesheet(self):
        QApplication.instance().setStyleSheet(get_stylesheet())
        # pixmaps
        for child in self.findChildren(IconButton):
            child.setIconPixmap()
        pass
        # trees
        for child in self.findChildren(QTreeWidget):
            child.apply_stylesheet()
        pass
        # charts
        from gui.widgets.chart_widget import ChartWidget
        options = PySide6.QtCore.Qt.FindChildOptions.FindChildrenRecursively
        for child in self.findChildren(ChartWidget, options=options):
            child.apply_stylesheet()
        pass
            
        text_color = system.manager.config.get('display.text_color', '#c4c4c4')
        # if self.page_chat:
        #     self.page_chat.top_bar.title_label.setStyleSheet(f"QLineEdit {{ color: {apply_alpha_to_hex(text_color, 0.90)}; background-color: transparent; }}"
        #                                        f"QLineEdit:hover {{ color: {text_color}; }}")

    def apply_margin(self):
        margin = system.manager.config.get('display.window_margin', 6)
        self.layout.setContentsMargins(margin, margin, margin, margin)

    def toggle_always_on_top(self):
        always_on_top = system.manager.config.get('system.always_on_top', True)

        current_flags = self.windowFlags()
        new_flags = current_flags

        # Set or unset the always-on-top flag depending on the setting
        if always_on_top:
            new_flags |= Qt.WindowStaysOnTopHint
        else:
            new_flags &= ~Qt.WindowStaysOnTopHint

        # Hide the window before applying new flags
        self.hide()
        self.setWindowFlags(new_flags)

        # Ensuring window borders and transparency
        self.setAttribute(Qt.WA_TranslucentBackground)  # Maintain transparency
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)  # Keep it frameless
        self.show()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._mousePressed = True
            self._mousePos = event.pos()
            self._mouseGlobalPos = event.globalPos()
            self._resizing = self.isMouseOnEdge(event.pos())
            self.updateCursorShape(event.pos())

    def mouseMoveEvent(self, event):
        if self._mousePressed:
            if self._resizing:
                self.resizeWindow(event.globalPos())
            else:
                self.moveWindow(event.globalPos())

    def mouseReleaseEvent(self, event):
        if self._resizing:
            # save window state to database
            window_size = {
                'width': self.width(),
                'height': self.height(),
            }
            from utils import sql
            sql.execute("""
                UPDATE settings
                SET value = json(?)
                WHERE field = 'window_size'""", (json.dumps(window_size),))
        self._mousePressed = False
        self._resizing = False
        self._mousePos = None
        self._mouseGlobalPos = None
        self.setCursor(Qt.ArrowCursor)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.test_running = False
        super().keyPressEvent(event)

    def isMouseOnEdge(self, pos):
        rect = self.rect()
        return (pos.x() < self._resizeMargins or pos.x() > rect.width() - self._resizeMargins or
                pos.y() < self._resizeMargins or pos.y() > rect.height() - self._resizeMargins)

    def moveWindow(self, globalPos):
        if self._mouseGlobalPos is None:
            return
        diff = globalPos - self._mouseGlobalPos
        self.move(self.pos() + diff)
        self._mouseGlobalPos = globalPos
        self.notification_manager.update_position()

    def resizeWindow(self, globalPos):
        diff = globalPos - self._mouseGlobalPos
        newRect = self.geometry()  # Use geometry() instead of rect() to include the window's position

        if self._mousePos.x() < self._resizeMargins:
            newRect.setLeft(newRect.left() + diff.x())
        elif self._mousePos.x() > self.width() - self._resizeMargins:
            newRect.setRight(newRect.right() + diff.x())

        if self._mousePos.y() < self._resizeMargins:
            newRect.setTop(newRect.top() + diff.y())
        elif self._mousePos.y() > self.height() - self._resizeMargins:
            newRect.setBottom(newRect.bottom() + diff.y())

        self.setGeometry(newRect)
        self._mousePos = self.mapFromGlobal(globalPos)
        self._mouseGlobalPos = globalPos

    # # @qasync.asyncSlot()
    def run_test(self):
        # from gui.demo import DemoRun  # nable
        # self.demo_runnable = DemoRun(self)  # nable(self)

        self.demo_app = QApplication(sys.argv)
        self.demo_app.setAttribute(Qt.AA_EnableHighDpiScaling)
        self.demo_app.setStyle("Fusion")  # Fixes macos white line issue
        self.demo_window = Main()
        
        from gui.demo import DemoRunnable
        self.demo_runnable = DemoRunnable(self.demo_window)  # nable(self)
        # await self.demo_runnable.run()
        self.demo_window.threadpool.start(self.demo_runnable)
        self.test_running = False
    
    # # @qasync.asyncSlot()
    # def run_test(self):
    #     self.reset_db()
    #     self.load()
    #     pass
    #     # self.run_test()

    #     # delete test_data.db
    #     if os.path.exists('./test_data.db'):
    #         os.remove('./test_data.db')

    # def reset_db(self):
    #     user_db_path = sql.get_db_path()
    #     test_db_path = os.path.join(os.path.dirname(user_db_path), 'test_data.db')
    #     shutil.copyfile(user_db_path, test_db_path)

    #     sql.set_db_filepath(test_db_path)

    #     reset_db = True
    #     if reset_db:
    #         tos_val = sql.get_scalar('SELECT value FROM settings WHERE field = "accepted_tos"')
    #         if tos_val == '1':
    #             reset_application(force=True, preserve_audio_msgs=True, bootstrap=False)
    #             # print("DATABASE RESET.")

    #         tos_val = sql.get_scalar('SELECT value FROM settings WHERE field = "accepted_tos"')
    #         if tos_val == '0':
    #             sql.execute('UPDATE settings SET value = "1" WHERE field = "accepted_tos"')


    def updateCursorShape(self, pos):
        rect = self.rect()
        left = pos.x() < self._resizeMargins
        right = pos.x() > rect.width() - self._resizeMargins
        top = pos.y() < self._resizeMargins
        bottom = pos.y() > rect.height() - self._resizeMargins

        if (left and top) or (right and bottom):
            self.setCursor(Qt.SizeFDiagCursor)
        elif (left and bottom) or (right and top):
            self.setCursor(Qt.SizeBDiagCursor)
        elif left or right:
            self.setCursor(Qt.SizeHorCursor)
        elif top or bottom:
            self.setCursor(Qt.SizeVerCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

    def resizeEvent(self, event):
        self.notification_manager.update_position()
        self.position_title_bar()
        super().resizeEvent(event)
        # self.update_resize_grip_position()

    # def changeEvent(self, event):
    #     if event.type() == QEvent.WindowStateChange:
    #         if not self.isMinimized() and self.notification_manager.notifications:
    #             self.notification_manager.setVisible(True)
    #             for notification in self.notification_manager.notifications:
    #                 notification.timer.start()
    #             # self.notification_manager.update_position()
    #     super().changeEvent(event)

    def dragEnterEvent(self, event):
        # Check if the event contains file paths to accept it
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        # Check if the event contains file paths to accept it
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        # Get the list of URLs from the event
        urls = event.mimeData().urls()

        # Extract local paths from the URLs
        paths = [url.toLocalFile() for url in urls]
        self.page_chat.attachment_bar.add_attachments(paths=paths)
        event.acceptProposedAction()


def launch():
    try:
        app = QApplication(sys.argv)
        app.setAttribute(Qt.AA_EnableHighDpiScaling)
        app.setStyle("Fusion")

        loop = qasync.QEventLoop(app)
        asyncio.set_event_loop(loop)

        window = Main()
        window.show()
        
        with loop:
            loop.run_forever()

    except Exception as e:
        if 'AP_DEV_MODE' in os.environ:
            # When debugging in IDE, re-raise
            raise e
        display_message_box(
            icon=QMessageBox.Critical,
            title='Error',
            text=str(e)
        )
