"""
Toggle button field widget for configurable toggle buttons.

This module provides a ButtonToggle field widget that extends ToggleIconButton
to create configurable toggle buttons. It automatically connects to the parent's
update_config method and provides value management for boolean toggle states.
"""  # unchecked

from gui.util import ToggleIconButton


class ButtonToggle(ToggleIconButton):
    def __init__(self, parent, **kwargs):
        # kwargs.pop('text', None)  # Remove 'text' argument if it exists
        super().__init__(parent=parent, **kwargs)
        # connect checked signal to the value change
        self.toggled.connect(parent.update_config)

    def get_value(self):
        return self.isChecked()

    def set_value(self, value):
        self.setChecked(value)