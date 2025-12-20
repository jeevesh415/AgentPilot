"""Video Message Role GUI Module.

This module provides the VideoBubble class, a specialized message role
for displaying videos in the chat interface. Video roles handle video
loading, display, playback controls, and various video formats within
conversations.

Key Features:
- Video display and rendering capabilities
- Support for multiple video formats and sources
- Playback controls (play, pause, seek, volume)
- Video loading from files and URLs
- Error handling for invalid or corrupted videos
- Integration with the message role framework
- Dynamic video sizing and scaling
- Video metadata and path handling

Video roles provide a rich multimedia interface for viewing videos
within conversations, enabling visual content sharing and
media communication with AI systems.
"""  # unchecked

from PySide6.QtCore import QUrl, Qt, QRectF
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QGraphicsVideoItem
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QSlider, QLabel, QSizePolicy, QGraphicsView, QGraphicsScene
)

from utils.helpers import get_json_value
from gui import system


class VideoBubble(QWidget):
    def __init__(self, parent, message):
        super().__init__(parent=parent)
        self.main = parent.parent.main
        self.parent = parent
        self.msg_id = message.id
        self.member_id = message.member_id
        self.role = message.role
        self.log = message.log
        self.text = ''
        self.collapsed = False

        # Video player components
        self.video_item = None
        self.video_view = None
        self.video_scene = None
        self.media_player = None
        self.audio_output = None
        self.play_button = None
        self.position_slider = None
        self.duration_label = None

        # Setup layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        self.main_layout.setSpacing(5)

        # Apply styling
        role_config = system.manager.roles.get(self.role, {})
        bg_color = role_config.get('bubble_bg_color', '#252427')
        text_color = role_config.get('bubble_text_color', '#999999')
        self.setStyleSheet(f"background-color: {bg_color}; color: {text_color};")

        # Set size policy
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # Set message content
        self.set_message(message)

    def set_message(self, message):
        """Initialize the video player with message content"""
        self.text = message.content
        filepath = get_json_value(self.text, 'filepath')
        url = get_json_value(self.text, 'url')

        if url or filepath:
            try:
                self.setup_video_player(filepath, url)
            except Exception as e:
                print(f"Error loading video: {e}")
                error_label = QLabel(f"Error loading video: {filepath or url}")
                self.main_layout.addWidget(error_label)
        else:
            error_label = QLabel("No valid video path or URL provided")
            self.main_layout.addWidget(error_label)

    def setup_video_player(self, filepath, url):
        """Setup the video player with controls using QGraphicsVideoItem"""
        # Create graphics scene and view for video rendering
        self.video_scene = QGraphicsScene(self)
        self.video_view = QGraphicsView(self.video_scene, self)
        # self.video_view.setMinimumSize(640, 360)
        # self.video_view.setMaximumHeight(360)
        self.video_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.video_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.video_view.setStyleSheet("border: none; background-color: black;")
        self.main_layout.addWidget(self.video_view)

        # Create video item
        self.video_item = QGraphicsVideoItem()
        self.video_item.setSize(QRectF(0, 0, 640, 360).size())
        self.video_scene.addItem(self.video_item)

        # Create and add controls
        self.create_controls()
        self.main_layout.addWidget(self.controls_widget)

        # Create media player
        self.media_player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.media_player.setAudioOutput(self.audio_output)

        # Set video output to graphics item
        self.media_player.setVideoOutput(self.video_item)

        # Connect signals
        self.media_player.durationChanged.connect(self.update_duration)
        self.media_player.positionChanged.connect(self.update_position)
        self.media_player.errorOccurred.connect(self.handle_error)
        self.media_player.mediaStatusChanged.connect(self.on_media_status_changed)

        # Make video view clickable for play/pause
        self.video_view.mousePressEvent = lambda event: self.toggle_playback() if event.button() == Qt.LeftButton else None

        # Set video source
        if filepath:
            self.media_player.setSource(QUrl.fromLocalFile(filepath))
        elif url:
            self.media_player.setSource(QUrl(url))

    def create_controls(self):
        """Create playback control widgets"""
        self.controls_widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # Play/Pause button
        self.play_button = QPushButton("▶")
        self.play_button.setFixedSize(30, 30)
        self.play_button.clicked.connect(self.toggle_playback)
        layout.addWidget(self.play_button)

        # Position slider
        self.position_slider = QSlider(Qt.Horizontal)
        self.position_slider.sliderMoved.connect(self.set_position)
        layout.addWidget(self.position_slider)

        # Duration label
        self.duration_label = QLabel("00:00 / 00:00")
        self.duration_label.setFixedWidth(80)
        layout.addWidget(self.duration_label)

        self.controls_widget.setLayout(layout)

    def toggle_playback(self):
        """Toggle between play and pause"""
        if self.media_player.playbackState() == QMediaPlayer.PlayingState:
            self.media_player.pause()
            self.play_button.setText("▶")
        else:
            self.media_player.play()
            self.play_button.setText("⏸")

    def set_position(self, position):
        """Set video position from slider"""
        self.media_player.setPosition(position)

    def update_duration(self, duration):
        """Update slider range and duration label"""
        self.position_slider.setRange(0, duration)
        self.duration_label.setText(f"00:00 / {self.format_time(duration)}")

    def update_position(self, position):
        """Update slider position and time label"""
        if not self.position_slider.isSliderDown():
            self.position_slider.setValue(position)

        duration = self.media_player.duration()
        self.duration_label.setText(
            f"{self.format_time(position)} / {self.format_time(duration)}"
        )

    @staticmethod
    def format_time(ms):
        """Format milliseconds to MM:SS"""
        seconds = ms // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"

    def setMarkdownText(self, text):
        """Compatibility method for MessageBubble interface"""
        self.text = text
        # Re-parse and reload video if needed
        filepath = get_json_value(text, 'filepath')
        url = get_json_value(text, 'url')
        if (filepath or url) and self.media_player:
            if filepath:
                self.media_player.setSource(QUrl.fromLocalFile(filepath))
            elif url:
                self.media_player.setSource(QUrl(url))

    def append_text(self, text):
        """Compatibility method for MessageBubble interface"""
        # Not applicable for video bubbles
        pass

    def toPlainText(self):
        """Compatibility method for MessageBubble interface"""
        return self.text

    def handle_error(self, error, error_string):
        """Handle media player errors"""
        print(f"Media player error: {error} - {error_string}")

    def on_media_status_changed(self, status):
        """Handle media status changes to show first frame"""
        if status == QMediaPlayer.LoadedMedia:
            # Video is loaded, show first frame by playing and immediately pausing
            self.media_player.play()
            self.media_player.pause()
            self.play_button.setText("▶")
