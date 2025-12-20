"""
Controller for Daemon modules.

Each Daemon module contains a class that derives from Daemon.

The class must implement the following methods:
- __init__(self, **kwargs)
- start(self)
- stop(self)
"""

from core.managers.modules import ModulesController


class DaemonsController(ModulesController):
    def __init__(self, system):
        super().__init__(
            system, 
            module_type='daemons', 
            load_to_path='core.daemons',
            class_based=True,
            inherit_from=None,
            description="Background tasks or periodic jobs",
            long_description="Daemon modules are background processes that run continuously"
        )
