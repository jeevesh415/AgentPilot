"""API Manager Module.

This module provides the APIManager class for managing API configurations and credentials
within the Agent Pilot system. The APIManager handles secure storage and retrieval of
API keys, client configurations, and provider settings for various AI services and
external integrations.

Key Features:
- Secure API key and credential management
- Provider plugin configuration and integration
- Client key generation and management
- Database persistence for API configurations
- Support for multiple AI service providers
- Integration with the LiteLLM provider system

The APIManager enables Agent Pilot to connect with various AI model providers,
external services, and APIs while maintaining secure credential storage and
flexible configuration management for different integration scenarios.
"""  # unchecked

import json
import os

from typing_extensions import override

from utils.helpers import BaseManager
from utils import sql


class APIManager(BaseManager):
    def __init__(self, system):
        super().__init__(
            system,
            table_name='apis',
        )

    @override
    def load(self):
        apis = sql.get_results("""
            SELECT
                name,
                client_key,
                api_key AS api_key,
                config
            FROM apis""")
        self.clear()
        for api_name, client_key, api_key, api_config in apis:
            if api_key.startswith('$'):
                api_key = os.environ.get(api_key[1:], '')
            if client_key.startswith('$'):
                client_key = os.environ.get(client_key[1:], '')

            self[api_name] = {
                'client_key': client_key,
                'api_key': api_key,
                'config': json.loads(api_config)
            }

    @override
    def delete(self, key, where_field='id'):
        sql.execute("DELETE FROM models WHERE api_id = ?;", (key,))
        super().delete(key, where_field)
