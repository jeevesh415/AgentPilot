"""Contact Conversation Member Module.

This module provides the Contact member, representing external contacts or
third-party participants in conversations and workflows. Contacts enable
integration with external services, APIs, or other systems that can participate
in multi-agent conversations.

Key Features:
- External contact representation in conversations
- Third-party integration capabilities
- API and service integration support
- Configuration management for contact settings
- Message flow control and workflow integration
- External system communication handling
- Contact session and state management

The Contact member enables workflows to integrate with external systems,
services, or third-party contacts, expanding the capabilities of multi-agent
interactions beyond the local Agent Pilot environment.
"""

from typing import Dict, Any
from members import Member
from utils.helpers import set_module_type


@set_module_type(module_type='Members', settings='contact_settings')
class Contact(Member):
    default_role = 'contact'
    default_avatar = ':/resources/icon-user.png'
    default_name = 'Contact'
    output_type = 'OUTPUT'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.workflow = kwargs.get('workflow')
        self.config: Dict[str, Any] = kwargs.get('config', {})
        self.receivable_function = None

    async def run(self):
        yield 'SYS', 'BREAK'
