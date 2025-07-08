"""
Font selection field widget for configurable font choices.

This module provides a FontComboBox field widget that extends BaseCombo to create
a dropdown for selecting system fonts. It includes a custom delegate that renders
each font name in its actual font family, making it easy to preview fonts.
The widget automatically populates with available system fonts and integrates
with the configuration system.
"""  # unchecked

from PySide6.QtGui import Qt, QFontDatabase
from PySide6.QtWidgets import QStyledItemDelegate

from gui.fields.combo import BaseCombo
from utils.helpers import block_signals


class FontComboBox(BaseCombo):
    class FontItemDelegate(QStyledItemDelegate):
        def paint(self, painter, option, index):
            font_name = index.data()

            self.font = option.font
            self.font.setFamily(font_name)
            self.font.setPointSize(12)

            painter.setFont(self.font)
            painter.drawText(option.rect, Qt.TextSingleLine, index.data())

    def __init__(self, parent, **kwargs):
        self.first_item = kwargs.pop('first_item', None)
        super().__init__(parent, **kwargs)

        with block_signals(self):
            self.addItem('')
            available_fonts = QFontDatabase.families()
            self.addItems(available_fonts)

        font_delegate = self.FontItemDelegate(self)
        self.setItemDelegate(font_delegate)