
"""Result Message Role GUI Module.

This module provides the ResultBubble class, a specialized message role
for displaying execution results and output content in the chat interface.
Result roles handle the display of various types of execution results,
including code output, tool results, and system responses.

Key Features:
- Execution result display and formatting
- Support for various output formats
- JSON result parsing and visualization
- Integration with execution systems
- Output content formatting and styling
- Error and success result handling
- Result metadata and context display
- Integration with the message role framework

Result roles provide a clear interface for viewing execution
results and system outputs within conversations, enabling users
to understand the outcomes of AI actions and system operations.
"""  # unchecked

from utils.helpers import get_json_value
from plugins.workflows.bubbles import MessageBubble


class ResultBubble(MessageBubble):
    def __init__(self, parent, message):
        super().__init__(
            parent=parent,
            message=message,
        )

    def setMarkdownText(self, text):
        display_text = get_json_value(text, 'output', 'Error parsing result')
        super().setMarkdownText(text, display_text=display_text)
