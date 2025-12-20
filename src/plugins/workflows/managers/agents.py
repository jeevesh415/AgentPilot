
"""Agent Manager Module.

This module provides the AgentManager class for managing AI agents within the Agent Pilot system.
Agents are intelligent entities that can interact with users, execute workflows, and utilize tools
to accomplish tasks. The AgentManager handles CRUD operations, configuration management, and
organizational features for agents.

Key Features:
- Agent creation, modification, and deletion
- Configuration management with workflow support
- Folder-based organization for agent categorization
- Database persistence with UUID tracking
- Integration with the workflow execution system

The AgentManager extends BaseManager to provide specialized functionality for agent entities,
distinguishing them from other entity types like contacts while maintaining consistent data management
patterns throughout the application.
"""  # unchecked

from utils.helpers import BaseManager


class AgentManager(BaseManager):
    def __init__(self, system):
        super().__init__(
            system,
            table_name='entities',
            folder_key='agents',
            load_columns=['uuid', 'config'],
            default_fields={
                'kind': 'AGENT',
            },
            add_item_options={'title': 'Add Agent', 'prompt': 'Enter a name for the agent:'},
            del_item_options={'title': 'Delete Agent', 'prompt': 'Are you sure you want to delete this agent?'},
            config_is_workflow=True,
        )  # todo rename back to agents
