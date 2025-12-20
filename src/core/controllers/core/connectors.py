"""
Controller for Connector modules.

Each Connector module contains a class definition.

The class must implement the following methods:
- __init__(self, **kwargs)
- get_results(self, query, params=None, return_type='list')
- get_scalar(self, query, params=None, return_type='list')
- execute(self, query, params=None)
"""

from core.managers.modules import ModulesController


class ConnectorsController(ModulesController):
    def __init__(self, system):
        super().__init__(
            system, 
            module_type='connectors', 
            load_to_path='core.connectors',
            class_based=True,
            inherit_from=None,
            description="Database connection modules",
            long_description="Connector modules handle connections to external sources such as databases"
        )
