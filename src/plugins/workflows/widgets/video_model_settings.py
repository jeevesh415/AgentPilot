
"""
Video Model Settings Widget for Agent Pilot.

This module provides a specialized configuration widget for managing video generation model
settings within the Agent Pilot application. It enables users to configure video generation
AI models, their parameters, and related settings for visual content creation.

Key Features:
• Model type selection through plugin-based dropdown interface
• Integration with the Agent Pilot plugin system for model discovery
• Configuration fields for video generation parameters and settings
• Support for multiple video generation providers and models
• Dynamic model configuration based on selected provider
• Validation and error handling for model settings
• Seamless integration with the ConfigFields architecture
• Real-time updates and configuration persistence

The VideoModelSettings widget extends ConfigFields to provide a specialized interface for
configuring video generation AI models. It serves as a crucial component in the Agent Pilot
system for enabling visual content creation capabilities, allowing users to select and
configure appropriate video generation models for their specific needs.
"""  # unchecked

from gui.widgets.config_fields import ConfigFields
from utils.helpers import set_module_type


@set_module_type(module_type='Widgets')
class VideoModelSettings(ConfigFields):
    def __init__(self, parent):
        super().__init__(parent=parent)
        self.schema = [
            {
                'text': 'Model',
                'type': 'model',
                'model_kind': 'VIDEO',
                'width': 180,
                'row_key': 0,
            },
            {
                'text': 'Text',
                'type': str,
                'label_position': 'top',
                'num_lines': 3,
                'stretch_x': True,
                'stretch_y': True,
                'default': '',
            },
            {
                'text': 'Open video',
                'type': bool,
                'default': True,
                'row_key': 1,
            },
            {
                'text': 'Use cache',
                'type': bool,
                'default': False,
                'row_key': 1,
            },
            {
                'text': 'Wait until finished',
                'type': bool,
                'default': False,
                'row_key': 1,
            },
        ]