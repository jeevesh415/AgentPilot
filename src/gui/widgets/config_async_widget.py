"""Configuration Async Widget Module.

This module provides the ConfigAsyncWidget class, a specialized configuration widget
that supports asynchronous operations and threading. It extends the base ConfigWidget
to handle operations that need to run in separate threads without blocking the UI.

Key Features:
- Asynchronous configuration operations
- Thread-safe configuration management
- Integration with Qt's QRunnable for threading
- Main widget reference for cross-widget communication
- Non-blocking UI operations

The ConfigAsyncWidget provides a foundation for configuration widgets that need
to perform time-consuming operations while maintaining UI responsiveness.
"""  # unchecked

from PySide6.QtCore import QRunnable
from typing_extensions import override

from gui.widgets.config_widget import ConfigWidget
from gui.util import find_main_widget


class ConfigAsyncWidget(ConfigWidget):
    def __init__(self, parent):
        super().__init__(parent=parent)
        self.main = find_main_widget(self)
        pass

    @override
    def load(self):
        load_runnable = self.LoadRunnable(self)
        self.main.threadpool.start(load_runnable)

    class LoadRunnable(QRunnable):
        def __init__(self, parent):
            super().__init__()

        def run(self):
            pass