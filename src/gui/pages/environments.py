"""Environments Page Module.

This module provides the execution environments management page for the Agent Pilot
GUI interface. Environments define the runtime contexts where code execution and
workflow operations take place, including Docker containers, virtual environments,
and integrated execution contexts.

Key Features:
- Environment creation and configuration
- Support for multiple environment types (Docker, integrated, etc.)
- Environment isolation and security settings
- Plugin-based environment providers
- Environment status monitoring and management
- Integration with code execution systems
- Custom environment development support

The page enables users to configure safe and isolated execution environments
for running user code, agent tools, and workflow operations.
"""  # unchecked

from gui.widgets.config_db_tree import ConfigDBTree
from gui.widgets.config_joined import ConfigJoined
from gui.widgets.config_plugin import ConfigPlugin


class Page_Environments_Settings(ConfigDBTree):
    display_name = 'Envs'
    page_type = 'settings'  # either 'settings', 'main', or 'any' ('any' means it can be pinned between main and settings)

    def __init__(self, parent):
        super().__init__(
            parent=parent,
            table_name='environments',
            query="""
                SELECT
                    name,
                    id,
                    folder_id
                FROM environments
                ORDER BY pinned DESC, name""",
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
            ],
            add_item_options={'title': 'Add Environment', 'prompt': 'Enter a name for the environment:'},
            del_item_options={'title': 'Delete Environment',
                              'prompt': 'Are you sure you want to delete this environment?'},
            readonly=False,
            layout_type='horizontal',
            folder_key='environments',
            config_widget=self.EnvironmentConfig(parent=self),
        )

    def on_edited(self):
        from system import manager
        manager.environments.load()

    class EnvironmentConfig(ConfigJoined):
        def __init__(self, parent):
            super().__init__(parent=parent)
            self.widgets = [
                self.EnvironmentPlugin(parent=self),
            ]

        class EnvironmentPlugin(ConfigPlugin):
            def __init__(self, parent):
                super().__init__(
                    parent,
                    plugin_type='EnvironmentSettings',
                    plugin_json_key='environment_type',  # todo - rename
                    plugin_label_text='Environment Type',
                    none_text='Local',
                    # default_class=EnvironmentSettings,
                )
