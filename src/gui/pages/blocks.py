
"""Blocks Page Module.

This module provides the blocks management page for the Agent Pilot GUI interface.
Blocks are reusable content components that can contain text, prompts, code, or
entire workflows. The page enables users to create, organize, and manage these
modular components for use across different agents and workflows.

Key Features:
- Block creation, editing, and deletion
- Support for multiple block types (text, prompt, code, workflow)
- Workflow configuration and settings management
- Folder-based organization for block categorization
- Search and filtering capabilities
- Integrated configuration widget for detailed block setup
- Preview and testing capabilities

The page extends ConfigDBTree to provide database-backed block management with
a dual-panel interface showing the block library and detailed configuration options.
"""  # unchecked

from gui.widgets.config_db_tree import ConfigDBTree
from gui.widgets.workflow_settings import WorkflowSettings


class Page_Block_Settings(ConfigDBTree):
    display_name = 'Blocks'
    icon_path = ":/resources/icon-blocks.png"
    page_type = 'any'  # either 'settings', 'main', or 'any' ('any' means it can be pinned between main and settings)

    def __init__(self, parent):
        super().__init__(
            parent=parent,
            manager='blocks',
            query="""
                SELECT
                    name,
                    id,
                    uuid,
                    folder_id
                FROM blocks
                ORDER BY pinned DESC, ordr, name""",
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
                    'text': 'uuid',
                    'key': 'uuid',
                    'type': int,
                    'visible': False,
                },
            ],
            readonly=False,
            layout_type='horizontal',
            tree_header_hidden=True,
            default_item_icon=':/resources/icon-block.png',
            config_widget=self.Block_Config_Widget(parent=self),
            folder_config_widget=self.Folder_Config_Widget(parent=self),
            searchable=True,
        )
        self.splitter.setSizes([400, 1000])

    class Block_Config_Widget(WorkflowSettings):
        def __init__(self, parent):
            super().__init__(parent=parent)
