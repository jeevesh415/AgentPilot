
"""
Contact Settings Widget for Agent Pilot.

This module provides a specialized configuration widget for managing contact/user avatar settings
and related personal information within the Agent Pilot application. It allows users to configure
their visual representation and identification details.

Key Features:
• Avatar image selection and management with configurable diameter display
• Contact information fields configuration and validation
• Automatic field alignment for centered display layout
• Support for image file handling and preview functionality
• Dynamic field updating based on member/contact selection
• Validation and error handling for contact data integrity
• Seamless integration with the parent widget architecture

The ContactSettings widget extends ConfigFields to provide a specialized interface for
managing user contact information and avatar settings. It serves as a key component
in the Agent Pilot user interface for personalizing the user experience and maintaining
contact data consistency throughout the application.
"""  # unchecked

from PySide6.QtGui import Qt
from gui.widgets.config_fields import ConfigFields
from utils.helpers import set_module_type


@set_module_type(module_type='Widgets')
class ContactSettings(ConfigFields):
    def __init__(self, parent):
        super().__init__(parent=parent)
        self.parent = parent
        self.member_id = None
        self.field_alignment = Qt.AlignHCenter
        self.schema = [
            {
                'text': 'Avatar',
                'key': 'avatar_path',
                'type': 'image',
                'label_position': None,
                'diameter': 30,
                'row_key': 0,
                'default': '',
            },
            {
                'text': 'Name',
                'type': str,
                'stretch_x': True,
                'text_size': 15,
                # 'text_alignment': Qt.AlignCenter,
                'label_position': None,
                'transparent': True,
                'row_key': 0,
                'default': 'Contact',
            },
            {
                'text': 'Phone number',
                'type': str,
                'default': '',
            },
            {
                'text': 'Email',
                'type': str,
                'width': 250,
                'default': '',
            },
        ]
