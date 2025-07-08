
"""
Image Model Settings Widget for Agent Pilot.

This module provides a specialized configuration widget for managing image generation model
settings within the Agent Pilot application. It enables users to configure image generation
AI models, their parameters, and related settings for visual content creation.

Key Features:
• Model type selection through plugin-based dropdown interface
• Integration with the Agent Pilot plugin system for model discovery
• Configuration fields for image generation parameters and settings
• Support for multiple image generation providers and models
• Dynamic model configuration based on selected provider
• Validation and error handling for model settings
• Seamless integration with the ConfigFields architecture
• Real-time updates and configuration persistence

The ImageModelSettings widget extends ConfigFields to provide a specialized interface for
configuring image generation AI models. It serves as a crucial component in the Agent Pilot
system for enabling visual content creation capabilities, allowing users to select and
configure appropriate image generation models for their specific needs.
"""  # unchecked

from gui.widgets.config_fields import ConfigFields
from utils.helpers import set_module_type


@set_module_type(module_type='Widgets')
class ImageModelSettings(ConfigFields):
    def __init__(self, parent):
        super().__init__(parent=parent)
        self.schema = [
            {
                'text': 'Type',
                'key': 'model_type',
                'type': 'PluginComboBox',
                'plugin_type': 'MODEL',
                'allow_none': False,
                'width': 90,
                'default': 'Voice',
                'row_key': 0,
            },
            {
                'text': 'Model',
                'type': 'model',
                'model_kind': 'IMAGE',
                # 'default': 'mistral/mistral-large-latest',
                'row_key': 0,
            },
            # {
            #     'text': 'Member options',
            #     'type': 'MemberPopupButton',
            #     'use_namespace': 'group',
            #     'member_type': 'image',
            #     'label_position': None,
            #     'default': '',
            #     'row_key': 0,
            # },
        ]