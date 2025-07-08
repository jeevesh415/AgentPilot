"""
Boolean field widget for configurable checkboxes.

This module provides a Boolean field widget that extends QCheckBox to work with
the configuration system. It automatically connects to the parent's update_config
method and provides value management for boolean settings.
"""  # unchecked

from PySide6.QtWidgets import QCheckBox


class Boolean(QCheckBox):
    def __init__(self, parent, **kwargs):
        super().__init__(parent)
        self.stateChanged.connect(parent.update_config)

    def get_value(self):
        return self.isChecked()

    def set_value(self, value):
        if not isinstance(value, bool):
            if isinstance(value, str):
                value = value.lower()
            value = value in [1, '1', 'true', 'yes', 'on']
        self.setChecked(value)

    def clear_value(self):
        self.setChecked(False)
