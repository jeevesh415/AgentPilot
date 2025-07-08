
"""
User Settings Widget for Agent Pilot.

This module provides a comprehensive configuration widget for managing user settings
and preferences within the Agent Pilot application. It organizes user configuration
options into multiple pages including personal information and chat preferences.

Key Features:
• Multi-page configuration interface with Info and Chat settings
• User information management and profile configuration
• Chat preferences and behavior customization
• Integration with the ConfigPages architecture for organized layout
• Member ID tracking for user-specific configurations
• Dynamic page-based navigation and settings organization
• Real-time configuration updates and persistence
• Support for user personalization and preference management

The UserSettings widget extends ConfigPages to provide a paginated interface for
managing user preferences and account settings. It serves as a central hub in the
Agent Pilot user interface for personal configuration, allowing users to customize
their experience, manage their profile information, and configure chat behavior
preferences throughout the application.
"""  # unchecked

from PySide6.QtGui import Qt
from gui.widgets.config_fields import ConfigFields
from gui.widgets.config_tabs import ConfigTabs
from gui.widgets.config_pages import ConfigPages
from utils.helpers import set_module_type


# @set_module_type(module_type='Widgets')
class UserSettings(ConfigPages):
    def __init__(self, parent):
        super().__init__(parent=parent)
        self.layout.addSpacing(10)
        self.member_id = None

        self.pages = {
            'Info': self.Info_Settings(self),
            'Chat': self.Chat_Settings(self),
        }

    class Info_Settings(ConfigFields):
        def __init__(self, parent):
            super().__init__(parent=parent)
            self.parent = parent
            self.conf_namespace = 'info'
            self.field_alignment = Qt.AlignHCenter
            self.schema = [
                {
                    'text': 'Avatar',
                    'key': 'avatar_path',
                    'type': 'image',
                    'default': '',
                    'label_position': None,
                },
                {
                    'text': 'Name',
                    'type': str,
                    'default': 'You',
                    'stretch_x': True,
                    'text_size': 15,
                    'text_alignment': Qt.AlignCenter,
                    'label_position': None,
                    'transparent': True,
                },
            ]

    class Chat_Settings(ConfigTabs):
        def __init__(self, parent):
            super().__init__(parent=parent)

            self.pages = {
                'Group': self.Page_Chat_Group(parent=self),
            }

        class Page_Chat_Group(ConfigFields):
            def __init__(self, parent):
                super().__init__(parent=parent)
                self.parent = parent
                self.conf_namespace = 'group'
                self.label_width = 175
                self.schema = [
                    {
                        'text': 'Output role',
                        'type': 'combo',
                        'table_name': 'roles',
                        'width': 90,
                        'tooltip': 'Set the primary output role for this member',
                        'default': 'user',
                    },
                    {
                        'text': 'Output placeholder',
                        'type': str,
                        'tooltip': 'A tag to use this member\'s output from other members system messages',
                        'default': '',
                    },
                    {
                        'text': 'Member description',
                        'type': str,
                        'num_lines': 4,
                        'label_position': 'top',
                        'stretch_x': True,
                        'tooltip': 'A description of the member that can be used by other members (Not implemented yet)',
                        'default': '',
                    },
                ]
