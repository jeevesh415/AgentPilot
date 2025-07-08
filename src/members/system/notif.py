"""Notification System Member Module.

This module provides the Notif member, a system utility for sending
notifications and alerts within workflows. Notifications enable workflows
to communicate status updates, alerts, and important information to users
or external systems.

Key Features:
- System notification and alert generation
- Integration with notification systems and services
- Configurable notification content and formatting
- Workflow status and progress reporting
- User alert and messaging capabilities
- External system notification support
- Event-driven notification triggering
- Message templating and dynamic content

Notifications enable workflows to provide feedback, alerts, and status
updates to users and external systems, enhancing the user experience
and workflow monitoring capabilities.
"""

from typing import Dict, Any

from members import Member
from utils.helpers import set_module_type


@set_module_type(module_type='Members', settings='notif_settings')
class Notif(Member):
    default_avatar = ':/resources/icon-notif.png'
    default_name = 'Notification'
    OUTPUT = None

    @property
    def INPUTS(self):
        return {
            'CONFIG': {
                'text': Any[str, list[str]],
            },
        }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.workflow = kwargs.get('workflow')
        self.config: Dict[str, Any] = kwargs.get('config', {})
        self.receivable_function = None  #  self.receive

    async def run(self):
        from system import manager
        message = manager.blocks.format_string(
            self.config.get('text', ''),
            ref_workflow=self.workflow,
        )
        color = self.config.get('color', '#438BB9')
        self.main.show_notification_signal.emit(message, color)
        yield 'SYS', 'SKIP'  # todo not needed anymore
