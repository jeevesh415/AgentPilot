"""Set Variable System Member Module.

This module provides the SetVariable member, a system utility for setting
variables within workflows. SetVariable enables workflows to set variables
to communicate status updates, alerts, and important information to users
or external systems.

Key Features:
- System variable setting and management
- Integration with notification systems and services
- Configurable notification content and formatting
- Workflow status and progress reporting
- User variable setting and management
- External system variable support
- Event-driven notification triggering
- Message templating and dynamic content

Notifications enable workflows to provide feedback, alerts, and status
updates to users and external systems, enhancing the user experience
and workflow monitoring capabilities.
"""

from typing import Dict, Any

from plugins.workflows.members import Member
from utils.helpers import set_module_type


@set_module_type(module_type='Members')  # , settings='notif_settings')
class SetVariable(Member):
    default_avatar = ':/resources/icon-notif.png'
    default_name = 'Set Variable'
    workflow_insert_mode = 'single'
    OUTPUT = None

    @property
    def INPUTS(self):
        return {
            'CONFIG': {
                'scope': str,  # 'global', 'workflow'
                'ephemeral': bool,
                'variable': str,
                'value': str,
            },
        }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.receivable_function = None  #  self.receive

    async def run(self):
        pass
        yield 'SYS', 'SKIP'  # todo not needed anymore
