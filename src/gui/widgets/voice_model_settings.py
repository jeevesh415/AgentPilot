
"""
Voice Model Settings Widget for Agent Pilot.

This module provides a specialized configuration widget for managing voice synthesis model
settings within the Agent Pilot application. It enables users to configure voice AI models,
their parameters, and related settings for speech synthesis and voice generation.

Key Features:
• Model type selection through plugin-based dropdown interface
• Voice model configuration for speech synthesis
• Integration with the Agent Pilot plugin system for model discovery
• Dynamic configuration fields based on selected voice provider
• Support for multiple voice synthesis providers and models
• Real-time configuration updates and validation
• Seamless integration with the ConfigFields architecture
• Flexible voice model parameter management

The VoiceModelSettings widget extends ConfigFields to provide a specialized interface for
configuring voice synthesis AI models. It serves as a crucial component in the Agent Pilot
system for enabling speech synthesis capabilities, allowing users to select and configure
appropriate voice models for their specific audio generation and text-to-speech needs.
"""  # unchecked

from gui.widgets.config_fields import ConfigFields


class VoiceModelSettings(ConfigFields):
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
                'model_kind': 'VOICE',
                # 'default': 'mistral/mistral-large-latest',
                'default': {
                    'kind': 'VOICE',
                    'model_name': '9BWtsMINqrJLrRacOk9x',
                    # 'model_params': {},
                    'provider': 'elevenlabs',
                },
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
                'text': 'Play audio',
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
            # {
            #     'text': 'Member options',
            #     'type': 'MemberPopupButton',
            #     'use_namespace': 'group',
            #     'member_type': 'voice',
            #     'label_position': None,
            #     'default': '',
            #     'row_key': 0,
            # },
        ]

