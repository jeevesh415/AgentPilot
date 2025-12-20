"""
Projects Page Module.

This module provides the projects management page for the Agent Pilot GUI interface.
Projects enable users to organize and group related agents, workflows, and resources
into cohesive workspaces for different tasks or domains. The page facilitates
project-based organization and management of Agent Pilot resources.

Key Features:
- Project creation, editing, and deletion
- Workspace organization for related components
- Project-specific configuration and settings
- Folder-based organization for project categorization
- Search and filtering capabilities
- Integrated configuration widget for detailed project setup
- Resource management within project contexts

The page extends ConfigDBTree to provide database-backed project management with
a dual-panel interface showing the project list and detailed configuration options.
"""

from PySide6.QtWidgets import QMessageBox
from gui.widgets.config_db_tree import ConfigDBTree
from gui.util import get_project_type_class
from utils.helpers import display_message
from utils.sql import define_table
from plugins.projects.gui.project_types.general import GeneralProject


class Page_Projects(ConfigDBTree):
    display_name = 'Projects'
    icon_path = ":/resources/icon-workspace.png"
    page_type = 'main'  # either 'settings', 'main', or 'any' ('any' means it can be pinned between main and settings)

    def __init__(self, parent):
        super().__init__(
            parent=parent,
            manager='projects',  # todo name
            query="""
                SELECT
                    name,
                    id,
                    -- COALESCE(json_extract(config, '$.cwd'), '') as cwd,
                    config,
                    folder_id
                FROM projects
                ORDER BY pinned DESC, ordr, name COLLATE NOCASE""",
            schema=[
                {
                    'text': 'Name',
                    'key': 'name',
                    'type': str,
                    'stretch': True,
                },
                {
                    'text': 'id',
                    'key': 'id',
                    'type': int,
                    'visible': False,
                },
                {
                    'text': 'config',
                    'type': str,
                    'visible': False,
                },
            ],
            layout_type='horizontal',
            config_widget=None, # GeneralProject(parent=self),
            folder_config_widget=self.Folder_Config_Widget(parent=self),
            tree_header_hidden=True,
            readonly=True,
            searchable=True,
            filterable=True,
        )
        self.splitter.setSizes([200, 800])
        define_table('project_concepts', relations=['project_id'])
    
    def on_edited(self):
        self.config_widget.widgets[1].pages['Files'].load_config()
    
    def on_item_selected(self):
        project_type = self.get_config().get('project_type', 'general')
        project_type_class = get_project_type_class(project_type)
        if not project_type_class:
            display_message(
                message=f"Project type module '{project_type}' not found.",
                icon=QMessageBox.Warning,
            )
            project_type_class = GeneralProject

        is_same = isinstance(self.config_widget, project_type_class)
        if not is_same:
            if self.config_widget is not None:
                self.config_layout.removeWidget(self.config_widget)
                self.config_widget.deleteLater()
            self.config_widget = project_type_class(self)
            self.config_layout.insertWidget(0, self.config_widget)
            self.config_widget.build_schema()
            
        super().on_item_selected()
        