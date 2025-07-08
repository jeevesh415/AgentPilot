"""Configuration Manager Module.

This module provides the ConfigManager class for managing application-wide configuration settings
within the Agent Pilot system. The ConfigManager handles persistent storage and retrieval of
configuration data, automatically synchronizing changes between memory and the database.

Key Features:
- Automatic persistence of configuration changes to database
- JSON-based configuration storage and serialization
- Real-time configuration updates with immediate save operations
- Integration with application telemetry systems
- Dictionary-like interface for easy configuration access and modification

The ConfigManager extends ManagerController to provide specialized configuration management
capabilities, ensuring that all application settings are consistently maintained and immediately
persisted whenever changes occur.
"""  # unchecked

import json

from typing_extensions import override

from utils import sql, telemetry
from utils.helpers import ManagerController


class ConfigManager(ManagerController):
    def __init__(self, system):
        super().__init__(system)

    @override
    def load(self):
        sys_config = sql.get_scalar("SELECT `value` FROM `settings` WHERE `field` = 'app_config'")
        self.clear()
        self.update(json.loads(sys_config))
        # telemetry_on = self.get("system.telemetry", True)
        # telemetry.enabled = telemetry_on

    @override
    def save(self):
        sql.execute("UPDATE `settings` SET `value` = ? WHERE `field` = 'app_config'", (json.dumps(dict(self)),))
        self.load()

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self.save()

    def __delitem__(self, key):
        super().__delitem__(key)
        self.save()
