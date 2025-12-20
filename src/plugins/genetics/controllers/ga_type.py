
from core.managers.modules import ModulesController


class GATypeController(ModulesController):
    def __init__(self, system):
        super().__init__(
            system, 
            module_type='ga_types', 
            load_to_path='plugins.genetics.ga_types',
            class_based=True,
            # inherit_from='ModulesController',
            description="GA type management controllers",
            long_description="GA type modules define different types of genetic algorithms"
        )
