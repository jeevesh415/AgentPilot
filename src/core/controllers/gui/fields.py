"""
Controller for Field modules.

Each field module contains a class that derives from QWidget.

The class must implement the following methods:
- get_value()
- set_value(value)
- clear_value()

The class can optionally implement the following methods:
- 
"""
from core.managers.modules import ModulesController


class FieldsController(ModulesController):
    def __init__(self, system):
        super().__init__(
            system, 
            module_type='fields', 
            load_to_path='gui.fields',
            class_based=True,
            inherit_from='QWidget',
            description="Form field components",
            long_description="Fields are QWidget modules that represent a single data field, such as a text field, a number field, a checkbox, etc."
        )
