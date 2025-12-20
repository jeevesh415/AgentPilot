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

from plugins.workflows.members import Member
from utils.helpers import set_module_type


@set_module_type(module_type='Members', settings='notif_settings')
class Notif(Member):
    default_avatar = ':/resources/icon-notif.png'
    default_name = 'Notification'
    workflow_insert_mode = 'single'
    OUTPUT = None

    @property
    def INPUTS(self):
        return {
            'CONFIG': {
                'text': str,
            },
        }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.receivable_function = None

    async def run(self):
        self.main.notification_manager.show_notification(
            message=self.config.get('text', ''), 
            icon=self.config.get('icon', 'Information'),
            title=self.config.get('title', None),
            color=self.config.get('color', '#438BB9'),
            duration=self.config.get('duration', 5000),
        )
        
        # # # Send notification
        # # self.main.tray.showMessage(
        # #     "Hello!",
        # #     "This is a PySide6 system notification.",
        # #     QSystemTrayIcon.Information,
        # #     5000  # duration in ms
        # # )
        # self.main.show_notification(
        #     self.config.get('text', ''), 
        #     title=self.config.get('title', ''), 
        #     color=color
        # )
        self.workflow.save_message('sys', f"Shown notification: {self.config.get('text', '')}", self.full_member_id())
        yield 'SYS', 'SKIP'  # todo not needed anymore
