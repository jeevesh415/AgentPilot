"""File Explorer Page Module.

This module provides a comprehensive file explorer interface for Agent Pilot,
enabling users to navigate, manage, and interact with files across all
operating systems. The file explorer serves as a unified interface for
file operations and system navigation.

Key Features:
- Cross-platform file system navigation
- File and directory operations (create, rename, delete, copy, move)
- Multi-pane view with tree navigation and detailed file listing
- File type icons and thumbnail previews
- Search and filtering capabilities
- Context menus for quick operations
- Drag and drop support
- Bookmarks and favorite locations
- File properties and metadata display
- Integration with system file associations

The page provides a full-featured file management experience while maintaining
consistency with the Agent Pilot interface and supporting workflows that
require file system access.
"""


from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from gui.widgets.file_tree import FileTree
from utils.helpers import set_module_type


@set_module_type('Pages')
class Page_Files(FileTree):
    display_name = 'Files'
    icon_path = ":/resources/icon-files.png"
    page_type = 'any'

    def __init__(self, parent):
        super().__init__(
            parent=parent, 
            files_in_tree=False,
        )
