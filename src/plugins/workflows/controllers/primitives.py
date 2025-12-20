
from core.managers.modules import ModulesController


class PrimitivesController(ModulesController):
    def __init__(self, system):
        super().__init__(
            system, 
            module_type='primitives', 
            load_to_path='plugins.workflows.primitives',
            class_based=True,
            inherit_from=None,
        )
        