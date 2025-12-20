
"""
Configuration widget for organizing multiple configuration pages in a tabbed interface.

This module provides the ConfigTabs widget, which creates a tabbed interface for organizing
multiple configuration pages or sections. The widget extends ConfigCollection to provide
tab-based navigation between different configuration components.

Key features:
- Tabbed interface for organizing multiple configuration pages
- Dynamic tab creation and management functionality
- Automatic schema building for all contained tab widgets
- Optional tab bar hiding for embedded usage scenarios
- Breadcrumb navigation integration
- User-editable tabs

The widget is essential for Agent Pilot's configuration system, providing an organized way
to present complex configuration interfaces that span multiple categories or sections.
It's commonly used in settings pages, agent configurations, and other multi-faceted
configuration scenarios where logical grouping improves user experience.
"""

import json
from PySide6.QtWidgets import *
from typing_extensions import override

from utils import sql
from utils.helpers import block_signals

from gui.util import find_attribute, IconButton, CVBoxLayout, find_main_widget, get_selected_pages

from gui.widgets.config_collection import ConfigCollection


class ConfigTabs(ConfigCollection):
    def __init__(self, parent, **kwargs):
        super().__init__(parent=parent)
        self.layout = CVBoxLayout(self)
        self.content = QTabWidget(self)
        self.pages = kwargs.get('pages', {})
        self.new_page_btn = None
        # self.user_editable = True
        self.content.currentChanged.connect(self.on_current_changed)
        hide_tab_bar = kwargs.get('hide_tab_bar', False)
        if hide_tab_bar:
            self.content.tabBar().hide()
        
        self.layout.addWidget(self.content)

        self.new_page_btn = IconButton(
            parent=self,
            icon_path=':/resources/icon-new-large.png',
            size=25,
        )
        self.new_page_btn.setMinimumWidth(25)
        self.new_page_btn.clicked.connect(self.add_page)

    @override
    def build_schema(self):
        """Build the widgets of all tabs from `self.tabs`"""
        # remove all tabs
        for i in reversed(range(self.content.count())):
            widget = self.content.widget(i)
            self.content.removeTab(i)
            # widget.deleteLater()
        
        # build all tabs
        with block_signals(self):
            for tab_name, tab in self.pages.items():
                if hasattr(tab, 'build_schema'):
                    tab.build_schema()
                self.content.addTab(tab, tab_name)

        if not find_attribute(self, 'user_editing'):
            self.new_page_btn.hide()
        self.recalculate_new_page_btn_position()

        if hasattr(self, 'after_init'):
            self.after_init()

    @override
    def load(self):
        super().load()
        self.recalculate_new_page_btn_position()

    def on_current_changed(self, _):
        self.load()
        self.update_breadcrumbs()
        main = find_main_widget(self)
        path = get_selected_pages(main.main_pages)
        sql.execute("UPDATE settings SET value = ? WHERE `field` = 'page_path'", (json.dumps(path),))
        

    # def show_tab_context_menu(self, pos):
    #     tab_index = self.content.tabBar().tabAt(pos)
    #     if tab_index == -1:
    #         return
    #
    #     menu = QMenu(self.parent)
    #
    #     page_key = list(self.pages.keys())[tab_index]
    #     user_editing = find_attribute(self, 'user_editing', False)
    #     if user_editing:
    #         btn_delete = menu.addAction('Delete')
    #         btn_delete.triggered.connect(lambda: self.delete_page(page_key))
    #
    #         menu.exec_(QCursor.pos())  # todo not working why?
    #         # if action == btn_delete:
    #         #     self.delete_page(page_key)

    def recalculate_new_page_btn_position(self):
        if not self.new_page_btn:
            return
        tab_bar = self.content.tabBar()
        pos = tab_bar.mapTo(self, tab_bar.rect().topRight())
        self.new_page_btn.move(pos.x() + 1, pos.y())