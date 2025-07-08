"""
Button field widget for configurable icon buttons.

This module provides a Button field widget that extends IconButton to serve as
a configurable field component. It integrates with the configuration system
while providing icon-based button functionality.
"""  # unchecked

from gui.util import IconButton


class Button(IconButton):
    def __init__(self, parent, **kwargs):
        # kwargs.pop('text', None)  # Remove 'text' argument if it exists
        super().__init__(parent=parent, **kwargs)
