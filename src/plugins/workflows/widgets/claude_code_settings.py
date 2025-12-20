
"""Claude Code Settings Widget Module.

This module provides the ClaudeCodeSettings widget, a configuration interface
for customizing Claude code execution and chat model parameters in Agent Pilot.

Key Features:
- Model selection for Claude code/chat
- System message customization for Claude
- Schema-driven configuration fields
- Real-time updates and persistence

The ClaudeCodeSettings widget enables users to tailor Claude's code execution
environment and chat behavior to their workflow needs.
"""  # unchecked

from gui.widgets.config_fields import ConfigFields


class ClaudeCodeSettings(ConfigFields):
    def __init__(self, parent):
        super().__init__(parent=parent)
        self.conf_namespace = 'chat'
        self.schema = [
            {
                'text': 'Model',
                'type': 'model',
                'model_kind': 'CHAT',
                'default': '',
                'width': 200,
                'row_key': 0,
            },
            {
                'text': 'Max turns',
                'type': int,
                'minimum': 1,
                'maximum': 99,
                'default': 7,
                'width': 60,
                'has_toggle': True,
                'row_key': 0,
            },
            {
                'text': 'System message',
                'key': 'sys_msg',
                'type': str,
                'num_lines': 12,
                'default': '',
                'stretch_x': True,
                'format_blocks': True,
                'enhancement_key': 'system_message',
                'stretch_y': True,
                'label_position': 'top',
            },
        ]
