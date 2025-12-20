"""Audio Message Role GUI Module.

This module provides the AudioBubble class, a specialized message role
for displaying and playing audio content in the chat interface. Audio roles
handle audio file display, playback controls, and audio content management
within conversations.

Key Features:
- Audio file display and metadata handling
- Audio playback controls and functionality
- Support for multiple audio formats
- Integration with media playback systems
- Audio file path and URL handling
- Interactive play/pause controls
- Audio content visualization
- Error handling for invalid audio files

Audio roles provide an interactive interface for playing and
managing audio content within conversations, enabling multimedia
communication and audio-based interactions with AI systems.
"""  # unchecked

import os
from utils.helpers import get_json_value, message_button
from plugins.workflows.bubbles import MessageBubble, MessageButton


class AudioBubble(MessageBubble):
    def __init__(self, parent, message):
        super().__init__(
            parent=parent,
            message=message,
            readonly=True,
        )

    def setMarkdownText(self, text):
        filepath = get_json_value(text, 'filepath', 'Error parsing audio')
        filename = os.path.basename(filepath)
        super().setMarkdownText(filename)

    @message_button('btn_play')
    class PlayButton(MessageButton):
        def __init__(self, parent):
            super().__init__(parent=parent,
                             icon_path=':/resources/icon-run-solid.png')

        def on_clicked(self):
            content = self.msg_container.message.content
            filepath = get_json_value(content, 'filepath', 'Error parsing audio')
            from utils.media import play_file
            play_file(filepath)