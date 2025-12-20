"""
Controller for Controller modules.

Each Controller module contains a class that derives from ModulesController.

The class can optionally implement the following methods:
- initial_content(module_name)
"""

from core.managers.modules import ModulesController


class ControllersController(ModulesController):
    def __init__(self, system):
        super().__init__(
            system, 
            module_type='controllers', 
            load_to_path='core.controllers',
            class_based=True,
            inherit_from='ModulesController',
            description="Module type management controllers",
            long_description="Controller modules define different types of modules"
        )
