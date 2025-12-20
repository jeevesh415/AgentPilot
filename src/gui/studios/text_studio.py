"""
Text Studio - Full-featured text editor similar to Notepad++.
Provides multi-tab editing, syntax highlighting, search/replace, and file management.
"""
import os

from PySide6.QtWidgets import (
    QWidget, QLabel, QGroupBox, QStatusBar,
    QPushButton, QTabWidget, QTextEdit, QPlainTextEdit,
    QFileDialog, QMessageBox, QDialog, QLineEdit,
    QCheckBox
)
from PySide6.QtCore import (
    Qt, QRegularExpression, QRect, QSize
)
from PySide6.QtGui import (
    QTextCursor, QColor, QFont, QTextDocument, QPainter,
    QTextFormat, QTextOption, QKeySequence
)

from gui.util import CustomMenu, find_main_widget, CVBoxLayout, CHBoxLayout
from utils.helpers import apply_alpha_to_hex, set_module_type
from gui import system
from gui.style import SECONDARY_COLOR


@set_module_type('Studios')
class TextStudio(QWidget):
    """
    Full-featured text editor studio similar to Notepad++.

    Features:
    - Multi-tab editing with file management
    - Syntax highlighting for multiple languages
    - Advanced search and replace with regex support
    - File explorer/tree view
    - Line numbers and code folding
    - Auto-completion and bracket matching
    - Multiple encoding support
    - Macro recording and playback
    """
    associated_extensions = ['txt', 'py', 'js', 'html', 'css', 'json', 'xml', 'md', 'sql', 'yaml', 'yml', 'ini', 'toml', 'cfg', 'conf', 'log', 'csv', 'tsv']

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main = find_main_widget(self)
        self.open_files = {}  # Track open files {filepath: editor_widget}
        self.current_file = None
        self.search_dialog = None

        # Build highlighter mapping from available modules
        self.highlighter_map = {}  # {extension: highlighter_class}
        self._load_highlighters()

        # Tab widget for multiple files
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.tab_widget.currentChanged.connect(self.on_tab_changed)

        # Menu bar
        self.menubar = self.MenuBar(self)

        # Status bar
        self.status_bar = QStatusBar()
        self.position_label = QLabel("Ln 1, Col 1")
        self.selection_label = QLabel("")
        self.encoding_label = QLabel("UTF-8")
        self.line_ending_label = QLabel("LF")
        self.status_bar.addWidget(self.position_label)
        self.status_bar.addWidget(self.selection_label)
        self.status_bar.addPermanentWidget(self.encoding_label)
        self.status_bar.addPermanentWidget(self.line_ending_label)

        self.layout = CVBoxLayout(self)
        self.layout.addWidget(self.menubar)
        self.layout.addWidget(self.tab_widget)
        self.layout.addWidget(self.status_bar)

    def _load_highlighters(self):
        """Load all available highlighters and build extension mapping."""
        # Get all highlighter modules efficiently (one call)
        highlighters = system.manager.modules.get_modules_in_folder(
            'Highlighters',
            fetch_keys=('name', 'class',)
        )

        # Build extension to highlighter class mapping
        for _, highlighter_class in highlighters:
            if highlighter_class and hasattr(highlighter_class, 'associated_extensions'):
                for ext in highlighter_class.associated_extensions:
                    # Store without the dot prefix for easier lookup
                    ext_normalized = ext.lower().lstrip('.')
                    self.highlighter_map[ext_normalized] = highlighter_class

    class MenuBar(CustomMenu):
        def __init__(self, parent):
            super().__init__(parent)
            self.schema = [
                {
                    'text': 'File',
                    'submenu': [
                        {
                            'text': 'New',
                            'shortcut': QKeySequence.New,
                            'target': parent.new_file,
                        },
                        {
                            'text': 'Open',
                            'shortcut': QKeySequence.Open,
                            'target': parent.open_file,
                        },
                        {
                            'text': 'Save',
                            'shortcut': QKeySequence.Save,
                            'target': parent.save_file,
                        },
                        {
                            'text': 'Save As',
                            'shortcut': QKeySequence.SaveAs,
                            'target': parent.save_file_as,
                        },
                        {
                            'text': 'Close',
                            'shortcut': QKeySequence.Close,
                            'target': parent.close_tab,
                        },
                        {
                            'text': 'Close All',
                            'target': parent.close_all_tabs,
                        },
                    ],
                },
                {
                    'text': 'Edit',
                    'submenu': [
                        {
                            'type': 'create_standard',
                            'widget': lambda: parent.tab_widget.currentWidget(),
                        }
                    ],
                },
                {
                    'text': 'View',
                    'submenu': [
                        {
                            'text': 'Zoom In',
                            'shortcut': QKeySequence.ZoomIn,
                            'target': parent.zoom_in,
                        },
                        {
                            'text': 'Zoom Out',
                            'shortcut': QKeySequence.ZoomOut,
                            'target': parent.zoom_out,
                        },
                        {
                            'text': 'Reset Zoom',
                            'shortcut': 'Ctrl+0',
                            'target': parent.reset_zoom,
                        },
                        {
                            'type': 'separator',
                        },
                        {
                            'text': 'Word Wrap',
                            'checkable': True,
                            'checked_state': lambda: parent.tab_widget.currentWidget().lineWrapMode() == QPlainTextEdit.WidgetWidth,
                            'target': parent.toggle_word_wrap,
                        },
                        {
                            'text': 'Toggle Line Numbers',
                            'checkable': True,
                            'checked_state': lambda: parent.tab_widget.currentWidget().line_number_area.isVisible() if parent.tab_widget.currentWidget() else True,
                            'target': parent.toggle_line_numbers,
                        },
                    ],
                },
                {
                    'text': 'Search',
                    'submenu': [
                        {
                            'text': 'Find',
                            'shortcut': QKeySequence.Find,
                            'target': parent.show_find_dialog,
                        },
                        {
                            'text': 'Replace',
                            'shortcut': QKeySequence.Replace,
                            'target': parent.show_replace_dialog,
                        },
                    ],
                },
            ]            
            self.create_menubar(parent)

    def new_file(self):
        """Create a new empty file tab."""
        editor = CodeEditor()
        editor.cursorPositionChanged.connect(self.update_cursor_position)
        editor.selectionChanged.connect(self.update_selection_info)
        editor.textChanged.connect(lambda: self.mark_modified(editor))

        tab_index = self.tab_widget.addTab(editor, "Untitled")
        self.tab_widget.setCurrentIndex(tab_index)

        return editor

    def open_file(self, filepath=None):
        """Open a file in a new tab."""
        if not filepath:
            filepath, _ = QFileDialog.getOpenFileName(
                self,
                "Open File",
                "",
                "All Files (*);;Python Files (*.py);;Text Files (*.txt);;JavaScript Files (*.js)"
            )

        if not filepath:
            return

        # Check if file is already open
        for i in range(self.tab_widget.count()):
            editor = self.tab_widget.widget(i)
            if hasattr(editor, 'filepath') and editor.filepath == filepath:
                self.tab_widget.setCurrentIndex(i)
                return

        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                content = file.read()

            editor = CodeEditor()
            editor.setPlainText(content)
            editor.filepath = filepath
            editor.is_modified = False
            editor.cursorPositionChanged.connect(self.update_cursor_position)
            editor.selectionChanged.connect(self.update_selection_info)
            editor.textChanged.connect(lambda: self.mark_modified(editor))

            # Apply syntax highlighting based on file extension
            self.apply_syntax_highlighting(editor, filepath)

            filename = os.path.basename(filepath)
            tab_index = self.tab_widget.addTab(editor, filename)
            self.tab_widget.setCurrentIndex(tab_index)

            self.open_files[filepath] = editor

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open file: {str(e)}")

    def save_file(self):
        """Save the current file."""
        current_editor = self.tab_widget.currentWidget()
        if not current_editor:
            return

        if not hasattr(current_editor, 'filepath') or not current_editor.filepath:
            self.save_file_as()
            return

        try:
            with open(current_editor.filepath, 'w', encoding='utf-8') as file:
                file.write(current_editor.toPlainText())

            current_editor.is_modified = False
            tab_index = self.tab_widget.currentIndex()
            filename = os.path.basename(current_editor.filepath)
            self.tab_widget.setTabText(tab_index, filename)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save file: {str(e)}")

    def save_file_as(self):
        """Save the current file with a new name."""
        current_editor = self.tab_widget.currentWidget()
        if not current_editor:
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Save File As",
            "",
            "All Files (*);;Python Files (*.py);;Text Files (*.txt);;JavaScript Files (*.js)"
        )

        if not filepath:
            return

        try:
            with open(filepath, 'w', encoding='utf-8') as file:
                file.write(current_editor.toPlainText())

            current_editor.filepath = filepath
            current_editor.is_modified = False
            tab_index = self.tab_widget.currentIndex()
            filename = os.path.basename(filepath)
            self.tab_widget.setTabText(tab_index, filename)

            self.open_files[filepath] = current_editor
            self.apply_syntax_highlighting(current_editor, filepath)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save file: {str(e)}")

    def close_tab(self, index):
        """Close a tab."""
        editor = self.tab_widget.widget(index)

        if hasattr(editor, 'is_modified') and editor.is_modified:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "The file has unsaved changes. Do you want to save before closing?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
            )

            if reply == QMessageBox.Save:
                self.save_file()
            elif reply == QMessageBox.Cancel:
                return

        if hasattr(editor, 'filepath') and editor.filepath in self.open_files:
            del self.open_files[editor.filepath]

        self.tab_widget.removeTab(index)

        # Create new tab if no tabs left
        if self.tab_widget.count() == 0:
            self.new_file()

    def close_current_tab(self):
        """Close the current tab."""
        current_index = self.tab_widget.currentIndex()
        if current_index >= 0:
            self.close_tab(current_index)

    def close_all_tabs(self):
        """Close all open tabs."""
        while self.tab_widget.count() > 0:
            self.close_tab(0)

    def on_tab_changed(self, index):
        """Handle tab change."""
        if index >= 0:
            editor = self.tab_widget.widget(index)
            if editor:
                self.update_cursor_position()
                self.update_selection_info()

                # Update language combo based on file
                if hasattr(editor, 'filepath'):
                    self.detect_and_set_language(editor.filepath)

    def on_tree_double_click(self, index):
        """Handle double-click on file tree."""
        model = self.file_tree.model()
        filepath = model.filePath(index)

        if os.path.isfile(filepath):
            self.open_file(filepath)

    def mark_modified(self, editor):
        """Mark a file as modified."""
        if not hasattr(editor, 'is_modified'):
            editor.is_modified = False

        if not editor.is_modified:
            editor.is_modified = True
            index = self.tab_widget.indexOf(editor)
            if index >= 0:
                current_text = self.tab_widget.tabText(index)
                if not current_text.endswith("*"):
                    self.tab_widget.setTabText(index, current_text + "*")

    def apply_syntax_highlighting(self, editor, filepath):
        """Apply syntax highlighting based on file type."""
        ext = os.path.splitext(filepath)[1].lower()
        # Remove the dot prefix if present
        ext = ext.lstrip('.')

        # Look up highlighter class for this extension
        highlighter_class = self.highlighter_map.get(ext)

        if highlighter_class:
            # Create highlighter instance with editor's document
            highlighter = highlighter_class(editor.document())
            editor.highlighter = highlighter

            # Update language combo to match
            class_name = highlighter_class.__name__
            if class_name.endswith('Highlighter'):
                display_name = class_name[:-11]  # Remove "Highlighter"
            else:
                display_name = class_name

        #     index = self.language_combo.findText(display_name)
        #     if index >= 0:
        #         self.language_combo.setCurrentIndex(index)
        # else:
        #     # No highlighter for this extension
        #     editor.highlighter = None
        #     self.language_combo.setCurrentIndex(0)  # Set to "Plain Text"

    def detect_and_set_language(self, filepath):
        """Detect and set language in combo box."""
        return
        ext = os.path.splitext(filepath)[1].lower()
        ext = ext.lstrip('.')

        # Look up highlighter for this extension
        highlighter_class = self.highlighter_map.get(ext)

        if highlighter_class:
            class_name = highlighter_class.__name__
            if class_name.endswith('Highlighter'):
                display_name = class_name[:-11]
            else:
                display_name = class_name

            index = self.language_combo.findText(display_name)
            if index >= 0:
                self.language_combo.setCurrentIndex(index)
        else:
            self.language_combo.setCurrentIndex(0)  # "Plain Text"

    def on_language_changed(self, language):
        """Handle language selection change."""
        current_editor = self.tab_widget.currentWidget()
        if not current_editor:
            return

        if language == "Plain Text":
            # Remove any existing highlighter
            current_editor.highlighter = None
        else:
            # Find the highlighter class that matches this language name
            highlighter_class = None
            for ext, h_class in self.highlighter_map.items():
                class_name = h_class.__name__
                if class_name.endswith('Highlighter'):
                    display_name = class_name[:-11]
                else:
                    display_name = class_name

                if display_name == language:
                    highlighter_class = h_class
                    break

            if highlighter_class:
                highlighter = highlighter_class(current_editor.document())
                current_editor.highlighter = highlighter
            else:
                current_editor.highlighter = None

    def update_cursor_position(self):
        """Update cursor position in status bar."""
        current_editor = self.tab_widget.currentWidget()
        if current_editor:
            cursor = current_editor.textCursor()
            line = cursor.blockNumber() + 1
            column = cursor.columnNumber() + 1
            self.position_label.setText(f"Ln {line}, Col {column}")

    def update_selection_info(self):
        """Update selection info in status bar."""
        current_editor = self.tab_widget.currentWidget()
        if current_editor:
            cursor = current_editor.textCursor()
            if cursor.hasSelection():
                sel_text = cursor.selectedText()
                sel_lines = sel_text.count('\n') + 1
                sel_chars = len(sel_text)
                self.selection_label.setText(f"Sel: {sel_chars} chars, {sel_lines} lines")
            else:
                self.selection_label.setText("")

    # Search operations
    def show_find_dialog(self):
        """Show find dialog."""
        if not self.search_dialog:
            self.search_dialog = SearchDialog(self, replace_mode=False)
        else:
            self.search_dialog.set_mode(replace_mode=False)

        current_editor = self.tab_widget.currentWidget()
        if current_editor and current_editor.textCursor().hasSelection():
            self.search_dialog.search_input.setText(current_editor.textCursor().selectedText())

        self.search_dialog.show()
        self.search_dialog.raise_()
        self.search_dialog.activateWindow()

    def show_replace_dialog(self):
        """Show replace dialog."""
        if not self.search_dialog:
            self.search_dialog = SearchDialog(self, replace_mode=True)
        else:
            self.search_dialog.set_mode(replace_mode=True)

        current_editor = self.tab_widget.currentWidget()
        if current_editor and current_editor.textCursor().hasSelection():
            self.search_dialog.search_input.setText(current_editor.textCursor().selectedText())

        self.search_dialog.show()
        self.search_dialog.raise_()
        self.search_dialog.activateWindow()

    def find_next(self):
        """Find next occurrence."""
        if self.search_dialog and self.search_dialog.search_input.text():
            self.search_dialog.find_next()

    def find_previous(self):
        """Find previous occurrence."""
        if self.search_dialog and self.search_dialog.search_input.text():
            self.search_dialog.find_previous()

    # View operations
    def zoom_in(self):
        """Zoom in text."""
        current_editor = self.tab_widget.currentWidget()
        if current_editor:
            current_editor.zoomIn(2)

    def zoom_out(self):
        """Zoom out text."""
        current_editor = self.tab_widget.currentWidget()
        if current_editor:
            current_editor.zoomOut(2)

    def reset_zoom(self):
        """Reset zoom level."""
        current_editor = self.tab_widget.currentWidget()
        if current_editor:
            font = current_editor.font()
            font.setPointSize(10)
            current_editor.setFont(font)

    def toggle_line_numbers(self, checked):
        """Toggle line numbers."""
        for i in range(self.tab_widget.count()):
            editor = self.tab_widget.widget(i)
            editor.line_number_area.setVisible(checked)
            editor.setViewportMargins(editor.line_number_area_width() if checked else 0, 0, 0, 0)

    def toggle_word_wrap(self, checked):
        """Toggle word wrap."""
        for i in range(self.tab_widget.count()):
            editor = self.tab_widget.widget(i)
            if checked:
                editor.setLineWrapMode(QPlainTextEdit.WidgetWidth)
            else:
                editor.setLineWrapMode(QPlainTextEdit.NoWrap)

    def toggle_whitespace(self, checked):
        """Toggle whitespace visibility."""
        for i in range(self.tab_widget.count()):
            editor = self.tab_widget.widget(i)
            option = editor.document().defaultTextOption()
            if checked:
                option.setFlags(option.flags() | QTextOption.ShowTabsAndSpaces)
            else:
                option.setFlags(option.flags() & ~QTextOption.ShowTabsAndSpaces)
            editor.document().setDefaultTextOption(option)


class CodeEditor(QPlainTextEdit):
    """Enhanced text editor with line numbers and code features."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.line_number_area = LineNumberArea(self)
        self.filepath = None
        self.is_modified = False
        self.highlighter = None
        # self._line_number_area_visible = True  # Track line number visibility

        # Set default font
        font = QFont("Consolas", 10)
        font.setStyleHint(QFont.Monospace)
        self.setFont(font)

        # Connect signals
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)

        self.update_line_number_area_width(0)
        self.highlight_current_line()

        # Set tab width
        self.setTabStopDistance(4 * self.fontMetrics().horizontalAdvance(' '))

    def line_number_area_width(self):
        """Calculate width needed for line number area."""
        digits = 1
        max_num = max(1, self.blockCount())
        while max_num >= 10:
            max_num //= 10
            digits += 1
        space = 3 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def update_line_number_area_width(self, _):
        """Update the width of the line number area."""
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        """Update the line number area when scrolling."""
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        """Handle resize events."""
        super().resizeEvent(event)
        cr = self.contentsRect()
        line_number_area_width = self.line_number_area_width() if self.line_number_area.isVisible() else 0
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(),
                                                line_number_area_width, cr.height()))

    def line_number_area_paint_event(self, event):
        """Paint the line numbers."""
        painter = QPainter()
        if not painter.begin(self.line_number_area):
            return

        try:
            painter.fillRect(event.rect(), QColor(SECONDARY_COLOR))

            block = self.firstVisibleBlock()
            block_number = block.blockNumber()
            top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
            bottom = top + self.blockBoundingRect(block).height()

            while block.isValid() and top <= event.rect().bottom():
                if block.isVisible() and bottom >= event.rect().top():
                    number = str(block_number + 1)
                    painter.setPen(QColor(120, 120, 120))
                    painter.drawText(0, top, self.line_number_area.width() - 3,
                                   self.fontMetrics().height(),
                                   Qt.AlignRight, number)

                block = block.next()
                top = bottom
                bottom = top + self.blockBoundingRect(block).height()
                block_number += 1
        finally:
            painter.end()

    def highlight_current_line(self):
        """Highlight the current line."""
        extra_selections = []

        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            TEXT_COLOR = system.manager.config.get('display.text_color', '#c4c4c4')
            line_color = apply_alpha_to_hex(TEXT_COLOR, 0.1)
            selection.format.setBackground(QColor(line_color))
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)

        self.setExtraSelections(extra_selections)


class LineNumberArea(QWidget):
    """Widget for displaying line numbers."""

    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        """Return size hint."""
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        """Paint line numbers."""
        self.editor.line_number_area_paint_event(event)


class SearchDialog(QDialog):
    """Search and replace dialog."""

    def __init__(self, parent, replace_mode=False):
        super().__init__(parent)
        self.text_studio = parent
        self.replace_mode = replace_mode

        self.setWindowTitle("Replace" if replace_mode else "Find")
        self.setFixedSize(450, 250 if replace_mode else 200)

        layout = CVBoxLayout(self)

        # Search input
        search_group = QGroupBox("Find what:")
        search_layout = CHBoxLayout(search_group)
        self.search_input = QLineEdit()
        search_layout.addWidget(self.search_input)
        layout.addWidget(search_group)

        # Replace input (if in replace mode)
        if replace_mode:
            replace_group = QGroupBox("Replace with:")
            replace_layout = CHBoxLayout(replace_group)
            self.replace_input = QLineEdit()
            replace_layout.addWidget(self.replace_input)
            layout.addWidget(replace_group)

        # Options
        options_group = QGroupBox("Options")
        options_layout = CVBoxLayout(options_group)

        self.case_sensitive = QCheckBox("Case sensitive")
        self.whole_words = QCheckBox("Whole words only")
        self.regex = QCheckBox("Regular expression")

        options_layout.addWidget(self.case_sensitive)
        options_layout.addWidget(self.whole_words)
        options_layout.addWidget(self.regex)

        layout.addWidget(options_group)

        # Buttons
        button_layout = CHBoxLayout()

        self.find_next_btn = QPushButton("Find Next")
        self.find_prev_btn = QPushButton("Find Previous")
        self.find_next_btn.clicked.connect(self.find_next)
        self.find_prev_btn.clicked.connect(self.find_previous)

        button_layout.addWidget(self.find_next_btn)
        button_layout.addWidget(self.find_prev_btn)

        if replace_mode:
            self.replace_btn = QPushButton("Replace")
            self.replace_all_btn = QPushButton("Replace All")
            self.replace_btn.clicked.connect(self.replace)
            self.replace_all_btn.clicked.connect(self.replace_all)
            button_layout.addWidget(self.replace_btn)
            button_layout.addWidget(self.replace_all_btn)

        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.close)
        button_layout.addWidget(self.close_btn)

        layout.addLayout(button_layout)

    def set_mode(self, replace_mode):
        """Set dialog mode (find or replace)."""
        self.replace_mode = replace_mode
        self.setWindowTitle("Replace" if replace_mode else "Find")

    def get_search_flags(self):
        """Get search flags based on options."""
        flags = QTextDocument.FindFlags()

        if self.case_sensitive.isChecked():
            flags |= QTextDocument.FindCaseSensitively
        if self.whole_words.isChecked():
            flags |= QTextDocument.FindWholeWords

        return flags

    def find_next(self):
        """Find next occurrence."""
        current_editor = self.text_studio.tab_widget.currentWidget()
        if not current_editor:
            return

        search_text = self.search_input.text()
        if not search_text:
            return

        flags = self.get_search_flags()

        if self.regex.isChecked():
            regex = QRegularExpression(search_text)
            if self.case_sensitive.isChecked():
                regex.setPatternOptions(QRegularExpression.NoPatternOption)
            else:
                regex.setPatternOptions(QRegularExpression.CaseInsensitiveOption)
            found = current_editor.find(regex, flags)
        else:
            found = current_editor.find(search_text, flags)

        if not found:
            # Wrap around to beginning
            cursor = current_editor.textCursor()
            cursor.movePosition(QTextCursor.Start)
            current_editor.setTextCursor(cursor)

            if self.regex.isChecked():
                current_editor.find(regex, flags)
            else:
                current_editor.find(search_text, flags)

    def find_previous(self):
        """Find previous occurrence."""
        current_editor = self.text_studio.tab_widget.currentWidget()
        if not current_editor:
            return

        search_text = self.search_input.text()
        if not search_text:
            return

        flags = self.get_search_flags() | QTextDocument.FindBackward

        if self.regex.isChecked():
            regex = QRegularExpression(search_text)
            if self.case_sensitive.isChecked():
                regex.setPatternOptions(QRegularExpression.NoPatternOption)
            else:
                regex.setPatternOptions(QRegularExpression.CaseInsensitiveOption)
            found = current_editor.find(regex, flags)
        else:
            found = current_editor.find(search_text, flags)

        if not found:
            # Wrap around to end
            cursor = current_editor.textCursor()
            cursor.movePosition(QTextCursor.End)
            current_editor.setTextCursor(cursor)

            if self.regex.isChecked():
                current_editor.find(regex, flags)
            else:
                current_editor.find(search_text, flags)

    def replace(self):
        """Replace current selection."""
        if not self.replace_mode:
            return

        current_editor = self.text_studio.tab_widget.currentWidget()
        if not current_editor:
            return

        cursor = current_editor.textCursor()
        if cursor.hasSelection():
            cursor.insertText(self.replace_input.text())
            self.find_next()

    def replace_all(self):
        """Replace all occurrences."""
        if not self.replace_mode:
            return

        current_editor = self.text_studio.tab_widget.currentWidget()
        if not current_editor:
            return

        search_text = self.search_input.text()
        replace_text = self.replace_input.text()

        if not search_text:
            return

        # Move to beginning
        cursor = current_editor.textCursor()
        cursor.movePosition(QTextCursor.Start)
        current_editor.setTextCursor(cursor)

        count = 0
        flags = self.get_search_flags()

        if self.regex.isChecked():
            regex = QRegularExpression(search_text)
            if self.case_sensitive.isChecked():
                regex.setPatternOptions(QRegularExpression.NoPatternOption)
            else:
                regex.setPatternOptions(QRegularExpression.CaseInsensitiveOption)

            while current_editor.find(regex, flags):
                cursor = current_editor.textCursor()
                cursor.insertText(replace_text)
                count += 1
        else:
            while current_editor.find(search_text, flags):
                cursor = current_editor.textCursor()
                cursor.insertText(replace_text)
                count += 1

        QMessageBox.information(self, "Replace All", f"Replaced {count} occurrences.")
