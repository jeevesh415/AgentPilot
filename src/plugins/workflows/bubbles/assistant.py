"""Assistant Message Role GUI Module.

This module provides the AssistantBubble class, a specialized message role
for displaying AI assistant responses in the chat interface. Assistant roles
are responsible for rendering and managing the display of AI-generated content
within the conversation view.

Key Features:
- AI assistant message display and formatting
- Integration with the message role framework
- Support for rich text and markdown content
- Conversation flow and message management
- Interactive message handling
- Theme and styling support
- Message history and context display

Assistant roles provide the visual representation of AI responses,
enabling users to view and interact with AI-generated content in a
user-friendly chat interface.
"""  # unchecked

from plugins.workflows.bubbles import MessageBubble


class AssistantBubble(MessageBubble):
    def __init__(self, parent, message):
        super().__init__(parent=parent, message=message)
