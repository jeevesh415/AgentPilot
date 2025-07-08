"""Assistant Message Bubble GUI Module.

This module provides the AssistantBubble class, a specialized message bubble
for displaying AI assistant responses in the chat interface. Assistant bubbles
are responsible for rendering and managing the display of AI-generated content
within the conversation view.

Key Features:
- AI assistant message display and formatting
- Integration with the message bubble framework
- Support for rich text and markdown content
- Conversation flow and message management
- Interactive message handling
- Theme and styling support
- Message history and context display

Assistant bubbles provide the visual representation of AI responses,
enabling users to view and interact with AI-generated content in a
user-friendly chat interface.
"""  # unchecked

from gui.bubbles import MessageBubble


class AssistantBubble(MessageBubble):
    def __init__(self, parent, message):
        super().__init__(parent=parent, message=message)
