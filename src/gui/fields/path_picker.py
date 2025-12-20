"""
Path picker field widget for configurable directory selection.

This module provides a PathPicker field widget that extends QWidget to create
an interactive directory selection interface. It includes a text input for manual entry
and a browse button for directory dialogs. Integrates with the configuration system for directory path settings.
"""

from PySide6.QtWidgets import QSizePolicy, QWidget, QLineEdit, QPushButton, QFileDialog, QHBoxLayout


class PathPicker(QWidget):
    def __init__(self, parent, **kwargs):
        super().__init__(parent)
        self.parent = parent
        # self.mode = kwargs.get('mode', 'any')
        width = kwargs.get('width', None)

        # Create layout
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(4)
        
        # Create path input
        self.path_input = QLineEdit(self)
        self.path_input.setPlaceholderText('Select or enter a path...')
        self.path_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.path_input.setMinimumWidth(200)
        
        # Create browse button
        self.browse_button = QPushButton('Browse', self)
        self.browse_button.setMaximumWidth(60)
        self.browse_button.clicked.connect(self.browse_path)
        
        # Add widgets to layout
        self.layout.addWidget(self.browse_button)
        self.layout.addWidget(self.path_input)
        
        # # Set fixed width if specified
        # if width:
        #     self.setFixedWidth(width)
        #     # Adjust path input width to fill remaining space
        #     button_width = self.browse_button.maximumWidth()
        #     spacing = self.layout.spacing()
        #     path_width = width - button_width - spacing - 10
        #     self.path_input.setFixedWidth(max(path_width, 100))
        
        # Connect signals
        self.path_input.textChanged.connect(parent.update_config)

    def get_value(self):
        return self.path_input.text()

    def set_value(self, value):
        if value:
            self.path_input.setText(str(value))

    def clear_value(self):
        self.path_input.clear()

    def browse_path(self):
        current_path = self.path_input.text()
        
        path = QFileDialog.getExistingDirectory(
            self, 
            'Select Directory', 
            current_path
        )
        
        if path:
            self.path_input.setText(path)
