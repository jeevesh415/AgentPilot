"""Projects Page Module.

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

from typing_extensions import override
from gui.widgets.config_db_tree import ConfigDBTree
from gui.widgets.workflow_settings import WorkflowSettings
from utils import sql


class Page_Projects(ConfigDBTree):
    display_name = 'Projects'
    icon_path = ":/resources/icon-workspace.png"
    page_type = 'any'  # either 'settings', 'main', or 'any' ('any' means it can be pinned between main and settings)

    def __init__(self, parent):
        super().__init__(
            parent=parent,
            table_name='projects',  # todo name
            query="""
                SELECT
                    name,
                    id,
                    config,
                    folder_id
                FROM projects
                ORDER BY pinned DESC, ordr, name""",
            schema=[
                {
                    'text': 'Name',
                    'key': 'name',
                    'type': str,
                    'stretch': True,
                    'image_key': 'config',
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
            layout_type='vertical',
            config_widget=self.Project_Config_Widget(parent=self),
            folder_config_widget=self.Folder_Config_Widget(parent=self),
            tree_header_hidden=True,
            add_item_options={'title': 'New Project', 'prompt': 'Enter a name for the project:'},
            del_item_options={'title': 'Delete Project',
                              'prompt': 'Are you sure you want to delete this project?'},
            readonly=True,
            searchable=True,
            filterable=True,
            folder_key='projects',
        )
        self.splitter.setSizes([500, 500])

    class Project_Config_Widget(
