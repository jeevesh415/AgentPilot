"""
Video Studio - Full-featured video editor similar to Kdenlive.
Provides timeline editing, multi-track support, effects, transitions, and export.
"""
from decimal import Decimal
from functools import partial
import os

import time
from typing import Any, Dict
from moviepy import VideoFileClip, AudioFileClip


from PySide6.QtWidgets import (
    QApplication, QComboBox, QHBoxLayout, QMenu, QVBoxLayout, QWidget, QSplitter, QLabel,
    QPushButton, QListWidget, QGraphicsView, QGraphicsScene, QGraphicsRectItem,
    QFileDialog, QMessageBox, QListWidgetItem, QGraphicsItem, QGraphicsLineItem,
    QGraphicsObject, QGraphicsPixmapItem, QDialog
)
from PySide6.QtCore import (
    QRectF, Qt, Signal, QUrl, QMimeData, QPointF, Slot, QTimer, QObject, QSizeF
)
from PySide6.QtGui import (
    QColor, QCursor, QIcon, QImage, QKeySequence, QPen, QBrush, QPixmap, QTransform, QPainter,
    QPainterPath
)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

from gui.util import CustomMenu, TreeDialog, clear_layout, colorize_pixmap, find_main_widget, CVBoxLayout, CHBoxLayout, get_member_settings_class
from gui import system
from gui.widgets.config_widget import ConfigWidget
from plugins.workflows.widgets.workflow_settings import HeaderFields
from gui.widgets.config_fields import ConfigFields
from utils.helpers import set_module_type

from PySide6.QtGui import QPixmap

from PySide6.QtCore import QThread, Signal, QObject
import numpy as np
from moviepy import VideoFileClip


@set_module_type('Studios')
class VideoStudio(ConfigWidget):
    """
    Full-featured video editor studio similar to Kdenlive.
    """
    associated_extensions = ['mp4', 'avi', 'mov', 'mkv', 'webm']

    def __init__(self, parent=None, full_screen=True):
        super().__init__(parent)
        self.main = find_main_widget(self)
        self.current_clip = None
        self.full_screen = full_screen

        # Project Settings
        self.project_width = 1920
        self.project_height = 1080
        self.project_fps = 30

        self.layout = CVBoxLayout(self)

        # self.media_bin = MediaBin()

        self.timeline = TimelineView(self)
        self.preview_panel = VideoPreviewPanel(self)
        self.member_config_widget = MemberConfigWidget(self)

        self.menubar = self.MenuBar(self)

        # Create track control panel
        self.track_control_panel = TrackControlPanel(self)

        # Create horizontal container for track controls + timeline
        timeline_with_controls = QWidget()
        timeline_h_layout = CHBoxLayout(timeline_with_controls)
        timeline_h_layout.addWidget(self.timeline)
        timeline_h_layout.addWidget(self.track_control_panel)

        self.timeline_panel = QWidget()
        timeline_layout = CVBoxLayout(self.timeline_panel)
        self.timeline_toolbar = self.TimelineContextMenu(self)
        timeline_layout.addWidget(self.timeline_toolbar)
        timeline_layout.addWidget(timeline_with_controls)

        main_splitter = QSplitter(Qt.Vertical)
        # main_splitter.addWidget(self.media_bin)
        main_splitter.addWidget(self.preview_panel)
        main_splitter.addWidget(self.timeline_panel)
        main_splitter.addWidget(self.member_config_widget)
        main_splitter.setSizes([250, 1000, 250])

        self.set_fullscreen(self.full_screen)

        self.timeline.scene.selectionChanged.connect(self.on_selection_changed)
        
        self.layout.addWidget(self.menubar)
        self.layout.addWidget(main_splitter)

        self.load_config({})
    
    def load_config(self, json_config=None):
        if json_config is None:
            json_config = self.config

        default_tracks = [
            {
                'name': 'Track 1',
            },
            {
                'name': 'Track 2',
            },
        ]
        self.timeline.clips = json_config.get('clips', {})
        self.timeline.tracks = json_config.get('tracks', default_tracks)
        
        self.project_width = json_config.get('project_width', 1920)
        self.project_height = json_config.get('project_height', 1080)
        self.project_fps = json_config.get('project_fps', 30)
        
        if hasattr(self, 'preview_panel'):
            self.preview_panel.update_dimensions()
    
    # def save_config(self):
    #     self.timeline.tracks = [track_control.get_config() for track_control in self.track_control_panel.track_controls]

    def load(self):
        # self.load_clips()
        self.load_tracks()
    
    def load_clips(self):
        for _, clip in self.timeline.clips.items():
            self.timeline.scene.removeItem(clip)
        # self.timeline.clips = {}

        clips_data = self.config.get('clips', [])
        # Iterate over the parsed 'members' data and add them to the scene
        for clip_info in clips_data:
            pass

        # self.view.fit_to_all()
    
    def load_tracks(self):
        for track_object in self.timeline.scene.items():
            if isinstance(track_object, TimelineView.MediaMember):
                continue
            if isinstance(track_object, TimelineView.PlayheadItem):
                continue
            self.timeline.scene.removeItem(track_object)

        for track_index, _ in enumerate(self.timeline.tracks):
            track = self.timeline.scene.addRect(
                0, track_index * 60, 10000, 60,
                QPen(QColor(80, 80, 80)), 
                QBrush(QColor(40, 40, 40))
            )
            track.setZValue(-1)
        
        self.track_control_panel.load()

        # Update scene and playhead height
        timeline_height = len(self.timeline.tracks) * 60
        self.timeline.scene.setSceneRect(0, 0, 10000, timeline_height)
        if self.timeline.playhead_item:
            self.timeline.playhead_item.setLine(0, 0, 0, timeline_height)

    def get_config(self):
        return {
            'tracks': self.track_control_panel.get_config(), # self.timeline.tracks,
            'clips': self.timeline.clips,
            'project_width': self.project_width,
            'project_height': self.project_height,
            'project_fps': self.project_fps,
        }
    
    def save_config(self):
        pass

    def on_selection_changed(self):
        selected_objects = self.timeline.scene.selectedItems()
        # selected_videos = [x for x in selected_objects if isinstance(x, self.timeline.VideoClip)]
        # selected_images = [x for x in selected_objects if isinstance(x, self.timeline.ImageClip)]

        if len(selected_objects) == 1:
            clip = selected_objects[0]
            self.member_config_widget.display_member(member=clip)
            if hasattr(self.member_config_widget.config_widget, 'reposition_view'):
                self.member_config_widget.config_widget.reposition_view()
        else:
            self.member_config_widget.hide()

        self.timeline_toolbar.reload_predicates()

    def set_fullscreen(self, fullscreen):
        """Toggle fullscreen mode."""
        self.full_screen = fullscreen
        # self.media_bin.setVisible(not fullscreen)
        self.timeline_panel.setVisible(not fullscreen)
        self.menubar.setVisible(not fullscreen)
        if not fullscreen:
            self.preview_panel.studio_button.hide()

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
                            'target': parent.new_project,
                        },
                        {
                            'text': 'Open',
                            'shortcut': QKeySequence.Open,
                            'target': parent.open_file,
                        },
                        {
                            'text': 'Save As',
                            'shortcut': QKeySequence.SaveAs,
                            'target': parent.save_project,
                        },
                    ],
                },
                {
                    'text': 'Edit',
                    'submenu': [
                        # {
                        #     'type': 'create_standard',
                        #     'widget': lambda: next(parent.timeline.scene.selectedItems(), None),
                        # }
                        {
                            'text': 'Project Settings',
                            'target': parent.project_settings,
                        }
                    ],
                },
                {
                    'text': 'View',
                    'submenu': [
                        {
                            'text': 'Zoom In',
                            'shortcut': QKeySequence.ZoomIn,
                            'target': parent.timeline.zoom_in,
                        },
                        {
                            'text': 'Zoom Out',
                            'shortcut': QKeySequence.ZoomOut,
                            'target': parent.timeline.zoom_out,
                        },
                    ],
                },
            ]
            self.create_menubar(parent)

    class TimelineContextMenu(CustomMenu):
        def __init__(self, parent):
            super().__init__(parent)
            self.schema = [
                {
                    'text': 'Add',
                    'icon_path': ':/resources/icon-new.png',
                    'target': lambda: self.show_add_context_menu(),
                },
                {
                    'type': 'separator',
                },
                {
                    'text': 'Copy',
                    'icon_path': ':/resources/icon-copy.png',
                    # 'target': self.copy_selected_items,
                    'enabled': lambda: self.has_selected_clips(),
                },
                {
                    'text': 'Paste',
                    'icon_path': ':/resources/icon-paste.png',
                    # 'target': self.paste_items,
                    'enabled': lambda: self.has_copied_items(),
                },
                {
                    'text': 'Delete',
                    'icon_path': ':/resources/icon-delete-2.png',
                    # 'target': self.delete_selected_items,
                    'enabled': lambda: self.has_selected_clips(),
                },
                {
                    'text': 'Split',
                    'icon_path': ':/resources/icon-split.png',
                    # 'target': parent.split_clip,
                    'enabled': lambda: self.has_selected_clips(),
                },
                {
                    'type': 'separator',
                },
                {
                    'text': 'Group',
                    'icon_path': ':/resources/icon-screenshot.png',
                    # 'target': self.group_selected_items,
                    'enabled': lambda: self.selected_clip_count() > 1,
                },
                {
                    'flatmenu': self.video_menu,
                    'prefix': 'video_',
                    'visibility_predicate': lambda: self.selected_clip_type() == 'video',
                },
                {
                    'flatmenu': self.image_menu,
                    'prefix': 'image_',
                    'visibility_predicate': lambda: self.selected_clip_type() == 'image',
                },
                {
                    'type': 'stretch',
                },
                {
                    'text': 'Zoom Out',
                    'icon_path': ':/resources/icon-minus.png',
                    'target': parent.timeline.zoom_out,
                },
                {
                    'text': 'Zoom In',
                    'icon_path': ':/resources/icon-new.png',
                    'target': parent.timeline.zoom_in,
                },
            ]
            self.create_toolbar(parent)
        
        @property
        def video_menu(self):
            return [
                {
                    'text': 'Remix',
                    'tooltip': 'Remix video',
                    'icon_path': ':/resources/icon-wand.png',
                },
                {
                    'text': 'Effects',
                    'tooltip': 'Apply effects to video',
                    'icon_path': ':/resources/icon-effects.png',
                },
                {
                    'text': 'Extend',
                    'tooltip': 'Extend video',
                    'visibility_predicate': lambda: self.selected_clip_type() == 'video',
                    'icon_path': ':/resources/icon-extend.png',
                    'submenu': [
                        {
                            'text': 'Extend Left',
                            'tooltip': 'Extend video before first frame',
                        },
                        {
                            'text': 'Extend Right',
                            'tooltip': 'Extend video after last frame',
                        },
                    ],
                },
            ]
        
        @property
        def image_menu(self):
            return [
                {
                    'text': 'Remix',
                    'tooltip': 'Remix image',
                    'icon_path': ':/resources/icon-wand.png',
                },
                {
                    'text': 'Effects',
                    'tooltip': 'Apply effects to image',
                    'icon_path': ':/resources/icon-effects.png',
                },
            ]
        
        def selected_clip_count(self):
            return len(self.parent.timeline.scene.selectedItems())
        
        def has_selected_clips(self):
            return self.selected_clip_count() > 0
        
        def only_one_selected_clip(self):
            return self.selected_clip_count() == 1
        
        def selected_clip_type(self):
            if not self.only_one_selected_clip():
                return None
            return self.parent.timeline.scene.selectedItems()[0].member_type
            
        def has_copied_items(self):
            try:
                clipboard = QApplication.clipboard()
                copied_data = clipboard.text()
                start_text = 'WORKFLOW_MEMBERS:'
                return copied_data.startswith(start_text)

            except Exception as e:
                return False

        def create_new_member_menu(self, parent=None):
            menu = QMenu('Add', parent)

            member_modules = system.manager.modules.get_modules_in_folder(
                module_type='Members',
                fetch_keys=('name', 'kind_folder', 'class',)
            )
            for module_name, module_kind, module_class in member_modules:
                if module_kind != 'media':
                    continue
                default_name = getattr(module_class, 'default_name', module_name.capitalize())
                workflow_insert_mode = getattr(module_class, 'workflow_insert_mode', None)
                icon_path = getattr(module_class, 'default_avatar', None)
                if icon_path:
                    icon = QIcon(colorize_pixmap(QPixmap(icon_path)))
                if workflow_insert_mode == 'single':
                    menu.addAction(icon, module_name.replace('_', ' ').title(), partial(
                        self.parent.timeline.add_insertable_entity,
                        {"_TYPE": module_name, "name": default_name}
                    ))
                # elif workflow_insert_mode == 'list':
                #     menu.addAction(module_name.replace('_', ' ').title(), partial(self.choose_member, module_name))
                else:
                    continue
            return menu

        def show_add_context_menu(self):
            menu = self.create_new_member_menu()
            menu.exec_(QCursor.pos())

        def choose_member(self, list_type):
            self.parent.set_edit_mode(True)
            list_dialog = TreeDialog(
                parent=self,
                title="Add Member",
                list_type=list_type,
                callback=self.add_insertable_entity,
                show_blank=True,
            )
            list_dialog.open()
        
        def select_clip(self, item):
            # show popup member widget
            self.parent.member_config_widget.display_member(member=item)

    def new_project(self):
        """Create new project."""
        reply = QMessageBox.question(
            self,
            "New Project",
            "Create a new project? Unsaved changes will be lost.",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.clear_project()
    
    def clear_project(self):
        """Clear project."""
        for clip in self.timeline.clips.values():
            self.timeline.scene.removeItem(clip)
        self.timeline.clips.clear()
        # self.media_bin.media_list.clear()

    def open_project(self):
        return

    def save_project(self):
        json = self.get_config()
        return

    def open_file(self):
        return

    def cut_clip(self):
        return

    def split_clip(self):
        return

    def delete_clip(self):
        return

    def export_project(self):
        return

    def project_settings(self):
        """Open project settings dialog."""
        dialog = ProjectSettingsDialog(self)
        if dialog.exec_():
            settings = dialog.get_config()
            self.project_width = settings['width']
            self.project_height = settings['height']
            self.project_fps = settings['fps']
            
            self.preview_panel.update_dimensions()
            # self.save_config() # Optional: auto-save on settings change


class ProjectSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Project Settings")
        self.resize(400, 300)
        self.layout = QVBoxLayout(self)
        
        # Config Fields
        self.config_fields = ConfigFields(
            self,
            schema=[
                {
                    'text': 'Width',
                    'key': 'width',
                    'type': int,
                    'default': parent.project_width,
                },
                {
                    'text': 'Height',
                    'key': 'height',
                    'type': int,
                    'default': parent.project_height,
                },
                {
                    'text': 'FPS',
                    'key': 'fps',
                    'type': (15, 23.976, 24, 25, 29.97, 30, 50, 59.94, 60),
                    'default': parent.project_fps,
                },
            ]
        )
        self.config_fields.load_config({}) # Load defaults from schema
        self.config_fields.build_schema()
        self.config_fields.load()
        self.layout.addWidget(self.config_fields)
        
        # Buttons
        button_box = QWidget()
        button_layout = QHBoxLayout(button_box)
        button_layout.setContentsMargins(0, 0, 0, 0)
        
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_ok = QPushButton("OK")
        self.btn_ok.clicked.connect(self.accept)
        
        button_layout.addStretch()
        button_layout.addWidget(self.btn_cancel)
        button_layout.addWidget(self.btn_ok)
        
        self.layout.addWidget(button_box)

    def get_config(self):
        self.config_fields.update_config()
        return self.config_fields.get_config()


class TimelineView(QGraphicsView):
    """Timeline view for video editing with multiple tracks."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.studio = parent
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setAcceptDrops(True)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

        # self.members_in_view: Dict[str, self.timeline.MediaMember] = {}
        self.new_members = None
    
        self.clips = {}
        self.tracks = []
        self.playhead_pos = 0
        self.playhead_item = None
        self.pixels_per_second = 10  # Base scale factor
        self._updating_playhead = False  # Flag to prevent feedback loop

        # Throttle timer for frame requests during scrubbing
        self._scrub_timer = QTimer()
        self._scrub_timer.setSingleShot(True)
        self._scrub_timer.timeout.connect(self._perform_frame_request)
        self._pending_frame_time = None
        self._scrub_throttle_ms = 30  # 30ms = ~33fps max during scrubbing

        # Initialize timeline with default tracks.
        self.scene.clear()
        self.tracks = []
        
        self.scene.setSceneRect(0, 0, 10000, 600)
        
        # Create draggable playhead
        self.playhead_item = self.PlayheadItem(len(self.tracks) * 60)
        self.playhead_item.timeline_view = self
        self.scene.addItem(self.playhead_item)
    
    def set_playhead_position(self, time_seconds):
        """Set playhead position in seconds."""
        self.playhead_pos = time_seconds
        if self.playhead_item:
            x = time_seconds * self.pixels_per_second
            self._updating_playhead = True  # Set flag before programmatic update
            self.playhead_item.setPos(x, 0)
            self._updating_playhead = False  # Clear flag after update

    def get_playhead_position(self):
        """Get current playhead position in seconds from playhead's actual position."""
        if self.playhead_item:
            x = self.playhead_item.pos().x()
            return x / self.pixels_per_second
        return 0

    def _on_playhead_moved(self):
        """Only render frame manually if not playing (scrub)."""
        time_seconds = self.get_playhead_position()
        self.playhead_pos = time_seconds

        if not self.studio.preview_panel.is_playing:
            t = max(0.0, float(time_seconds))
            # Store pending time and start/restart timer
            self._pending_frame_time = t
            self._scrub_timer.stop()
            self._scrub_timer.start(self._scrub_throttle_ms)

    def _perform_frame_request(self):
        """Actually perform the frame request after throttle delay."""
        if self._pending_frame_time is not None:
            self.studio.preview_panel.request_single_frame(self._pending_frame_time)
            self._pending_frame_time = None

    def zoom_in(self):
        """Zoom in on timeline."""
        self.scale(1.2, 1.0)

    def zoom_out(self):
        """Zoom out on timeline."""
        self.scale(1.0 / 1.2, 1.0)

    def add_insertable_entity(self, item, del_pairs=None):
        if self.new_members:
            return

        all_items = [(QPointF(0, 0), item)]

        self.new_members = [
            (
                pos,
                self.MediaMember(
                    timeline_view=self,
                    member_id=None,
                    start_time=Decimal(0),
                    track_index=None,
                    member_config=config,
                ),
            ) for pos, config in all_items
        ]
        for _, entity in self.new_members:
            self.scene.addItem(entity)

        self.setFocus()

    def add_entity(self):
        start_member_id = int(self.next_available_member_id())

        member_index_id_map = {}
        for i, enitity_tup in enumerate(self.new_members):
            entity_id = str(start_member_id + i)
            pos, entity = enitity_tup
            entity_config = entity.member_config

            member = self.MediaMember(
                timeline_view=self,
                member_id=entity_id,
                start_time=Decimal(pos.x() / 10.0),
                track_index=pos.y() / 60,
                member_config=entity_config,
            )
            # set z
            # member.setZValue(1)
            self.scene.addItem(member)
            self.clips[entity_id] = member
            member_index_id_map[i] = entity_id

        self.cancel_new_entity()

    def cancel_new_entity(self):
        # Remove the new entity from the scene and delete it
        if self.new_members:
            for pos, entity in self.new_members:
                self.scene.removeItem(entity)

        self.new_members = None
        # self.del_pairs = None
        self.update()
        
    def next_available_member_id(self) -> str:
        member_ids = [int(k) for k in self.clips.keys()] + [0]
        return str(max(member_ids) + 1)

    def contextMenuEvent(self, event):
        studio_menu = self.studio.timeline_toolbar
        schema = [item.copy() for item in studio_menu.schema]
        schema[0].pop('target')
        schema[0]['submenu'] = studio_menu.create_new_member_menu()
        menu = CustomMenu(parent=self, schema=schema)
        menu.show_popup_menu()
    
    def wheelEvent(self, event):
        """Handle mouse wheel event for zooming with Ctrl."""
        if event.modifiers() == Qt.ControlModifier:
            # Perform zoom
            if event.angleDelta().y() > 0:
                self.zoom_in()
            else:
                self.zoom_out()

            event.accept()
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = self.mapToScene(event.pos())
            item = self.scene.itemAt(pos, self.transform())

            # If click in empty area (not on a clip), move playhead to clicked time
            if not isinstance(item, self.MediaMember):
                is_ctrl_held = event.modifiers() & Qt.ControlModifier
                if is_ctrl_held:
                    self.scene.clearSelection()
                    time_seconds = pos.x() / self.pixels_per_second
                    if time_seconds < 0:
                        time_seconds = 0
                    self.set_playhead_position(time_seconds)

        # self.dragging_clips = self.scene.selectedItems()
        super().mousePressEvent(event)

    def dragEnterEvent(self, event):
        """Handle drag enter event."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        """Handle drag move event."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        """Handle drop event - add clips to timeline."""
        mime_data = event.mimeData()

        # # Get drop position in scene coordinates
        # pos = self.mapToScene(event.pos())
        # time_seconds = pos.x() / self.pixels_per_second
        # track_index = int(pos.y() / 60)

        # # Ensure track index is valid
        # if track_index < 0:
        #     track_index = 0
        # elif track_index >= len(self.tracks):
        #     track_index = len(self.tracks) - 1

        filepaths = []

        # Handle files dropped from file manager or MediaBin
        if mime_data.hasUrls():
            for url in mime_data.urls():
                filepath = url.toLocalFile()
                if os.path.exists(filepath):
                    filepaths.append(filepath)
        
        if len(filepaths) > 1:
            raise NotImplementedError()

        config = {
            "_TYPE": "video",
            "name": "Video",
            "mode": "Browse",
            "browse.path": filepaths[0],
        }
        self.add_insertable_entity(config)

        if filepaths:
            event.acceptProposedAction()
        else:
            event.ignore()

    def _get_snap_candidates(self):
        """Get all potential snap points from other clips."""
        snap_points = []
        for clip in self.clips.values():
            if clip.isSelected():
                continue
            clip_start = clip.pos().x()
            clip_end = clip.pos().x() + clip.rect().width()
            snap_points.extend([clip_start, clip_end])

        return snap_points

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)

    def mousePressEvent(self, event):
        if self.new_members:
            self.add_entity()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        mouse_point = self.mapToScene(event.pos())
        # Get mouse position in global (screen) coordinates
        
        if self.new_members:
            for pos, entity in self.new_members:
                # entity.setCentredPos(mouse_point + pos)
                # snap to tracks

                # new_y = max(0, round(mouse_point.y() / 60) * 60)
                new_y = mouse_point.y() // 60 * 60
                mouse_point.setY(new_y)
                # snap to clips
                # snapped_x = self._apply_snapping(max(0, mouse_point.x()))
                # mouse_point.setX(snapped_x)
                entity.setCentredPos(mouse_point)

            if self.scene:
                self.scene.update()
            self.update()

        super().mouseMoveEvent(event)

    # def keyPressEvent(self, event):
    #     if event.key() == Qt.Key_Escape:
    #         if self.parent.new_lines or self.parent.adding_line:
    #             self.parent.cancel_new_line()
    #         if self.parent.new_members:
    #             self.parent.cancel_new_entity()
    #         event.accept()

    #     elif event.key() == Qt.Key_Delete:
    #         if self.parent.new_lines or self.parent.adding_line:
    #             self.parent.cancel_new_line()
    #             event.accept()
    #             return
    #         if self.parent.new_members:
    #             self.parent.cancel_new_entity()
    #             event.accept()
    #             return

    #         self.parent.workflow_buttons.delete_selected_items()  # !404!
    #         event.accept()
    #     elif event.modifiers() == Qt.ControlModifier:
    #         if event.key() == Qt.Key_C:
    #             self.parent.workflow_buttons.copy_selected_items()  # !404!
    #             event.accept()
    #         elif event.key() == Qt.Key_V:
    #             self.parent.workflow_buttons.paste_items()  # !404!
    #             event.accept()
    #     else:
    #         super().keyPressEvent(event)


    class PlayheadItem(QGraphicsLineItem):
        """Draggable playhead indicator for the timeline."""

        def __init__(self, height, parent=None):
            super().__init__(0, 0, 0, height, parent)
            pen = QPen(QColor(255, 0, 0), 2)
            pen.setCosmetic(True)
            self.setPen(pen)
            self.setFlag(QGraphicsItem.ItemIsMovable, True)
            self.setFlag(QGraphicsItem.ItemIsSelectable, False)
            self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
            # set to fixed 1px width ( pen)
            self.setZValue(100)  # Ensure playhead is on top
            self.timeline_view = None

        def itemChange(self, change, value):
            """Constrain playhead to vertical movement only."""
            if change == QGraphicsItem.ItemPositionChange and self.timeline_view:
                self.timeline_view.scene.clearSelection()
                new_pos = QPointF(value)
                # Keep y = 0
                new_pos.setY(0)
                # Constrain to non-negative x
                if new_pos.x() < 0:
                    new_pos.setX(0)
                return new_pos
            elif change == QGraphicsItem.ItemPositionHasChanged and self.timeline_view:  # different from ItemPositionChange
                # Only notify timeline if this is a user-initiated drag, not a programmatic update
                if not self.timeline_view._updating_playhead:
                    self.timeline_view.studio.preview_panel.stop_playback()
                    self.timeline_view._on_playhead_moved()
            return super().itemChange(change, value)

    class MediaMember(QGraphicsRectItem):  # akin to DraggableMember
        (NoHandle, Left, Right) = range(3)
        """Represents a media clip on the timeline."""
        def __init__(
            self,
            timeline_view,
            member_id: str,
            start_time: Decimal,
            track_index: int,
            member_config: Dict[str, Any]
    ):
            super().__init__()
            self.timeline_view = timeline_view
            self.member_id = member_id
            self.member_config = member_config
            self.member_type = member_config.get('_TYPE', 'video')
            # self.config = config
            self.filepath = '/home/jb/dwhelper/Watch Fawlty Towers Season 1 Episode 1 A Touch of Class online f-01.mp4'  # todo
            # self.filepath = '/home/jb/CursorProjects/AgentPilot/screenshots/Screenshot_2025-08-19_04-02-27.png'  # todo
            # duration in seconds (float)
            self.duration = get_media_duration(self.filepath)
            self.track_index = track_index or 0

            # start_time as seconds (float)
            self.start_time = float(start_time) if start_time is not None else 0.0
            self.in_point = 0.0
            self.out_point = self.duration

            # Transformation attributes for video preview
            self.scale = member_config.get('scale', 1.0)
            self.pos_x = member_config.get('pos_x', 0.0)
            self.pos_y = member_config.get('pos_y', 0.0)
            self.rotation = member_config.get('rotation', 0.0)

            # --- State for resizing logic ---
            self.is_resizing = False
            self.current_resize_handle = self.NoHandle

            pps = 10
            self.setRect(0, 0, self.duration * pps, 50)
            self.setBrush(QBrush(QColor(100, 150, 200)))
            self.setPen(QPen(QColor(50, 75, 100), 2))
            self.setFlag(QGraphicsItem.ItemIsMovable)
            self.setFlag(QGraphicsItem.ItemIsSelectable)
            self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
            self.setAcceptHoverEvents(True)

            # position clip using start_time
            self.setPos(self.start_time * pps, self.track_index * 60)

            self.filename = os.path.basename(self.filepath)

        def setCentredPos(self, pos):
            self.setPos(pos.x() - self.boundingRect().width() / 2, pos.y() - self.boundingRect().height() / 2)

        def itemChange(self, change, value):
            if change == QGraphicsItem.ItemPositionChange:
                new_pos = QPointF(value)

                # Snap Y to track rows
                new_y = max(0, round(new_pos.y() / 60) * 60)
                new_pos.setY(new_y)

                # Snap X to other clips, then constrain to non-negative
                snapped_x = self._apply_snapping(max(0, new_pos.x()))
                # print(self.__class__.__name__, ' snapped_x: ', snapped_x)
                new_pos.setX(snapped_x)

                # Update clip properties
                self.start_time = new_pos.x() / 10.0
                self.track_index = int(new_pos.y() / 60)

                return new_pos
            return super().itemChange(change, value)

        def _apply_snapping(self, x_pos, snap_threshold=15):
            """Apply horizontal snapping to nearby clip edges."""
            snap_points = self.timeline_view._get_snap_candidates()

            if not snap_points:
                return x_pos

            clip_start = x_pos
            clip_end = x_pos + self.rect().width()

            # Find closest snap point for either clip start or end
            for snap_point in snap_points:
                for clip_edge in [clip_start, clip_end]:
                    distance = abs(clip_edge - snap_point)
                    if distance < snap_threshold:
                        return x_pos + (snap_point - clip_edge)

            return x_pos

        def get_handle_at(self, pos: QPointF):
            # Get the bounding rect directly (no proxy)
            rect = self.boundingRect()
            # Use a fixed handle size for consistent grip detection
            handle_size = 10  # Fixed 10 pixel grip zone for left/right edges

            # Only check for left and right handles (no vertical resizing)
            on_left = abs(pos.x() - rect.left()) < handle_size
            on_right = abs(pos.x() - rect.right()) < handle_size

            if on_left: return self.Left
            if on_right: return self.Right
            return self.NoHandle

        def set_cursor_for_handle(self, handle):
            if handle in (self.Left, self.Right):
                self.setCursor(Qt.SizeHorCursor)
            else:
                self.setCursor(Qt.ArrowCursor)

        def mousePressEvent(self, event):
            handle = self.get_handle_at(event.pos())
            if handle != self.NoHandle and self.isSelected():
                self.is_resizing = True
                self.current_resize_handle = handle
                # Store original rect and position separately
                self.original_rect = self.rect()
                self.original_pos = self.pos()
                self.original_mouse_pos = event.scenePos()
                self.setFlag(QGraphicsItem.ItemIsMovable, False)
                event.accept()
            else:
                super().mousePressEvent(event)

        def mouseMoveEvent(self, event):
            if self.is_resizing:
                delta = event.scenePos() - self.original_mouse_pos
                new_rect = QRectF(self.original_rect)
                handle = self.current_resize_handle
                new_pos = QPointF(self.original_pos)

                # Only handle left/right resizing
                if handle == self.Left:
                    # Resizing from left edge - keep right edge fixed
                    new_width = self.original_rect.width() - delta.x()
                    # Ensure minimum width of 20 pixels
                    if new_width > 20:
                        new_rect.setWidth(new_width)
                        # Move position to match the new left edge
                        new_pos.setX(self.original_pos.x() + delta.x())
                    else:
                        # If we hit minimum width, calculate the max delta we can apply
                        max_delta = self.original_rect.width() - 20
                        new_rect.setWidth(20)
                        new_pos.setX(self.original_pos.x() + max_delta)

                elif handle == self.Right:
                    # Resizing from right edge - keep left edge fixed
                    new_width = self.original_rect.width() + delta.x()
                    # Ensure minimum width of 20 pixels
                    if new_width > 20:
                        new_rect.setWidth(new_width)
                    else:
                        new_rect.setWidth(20)
                    # Position stays the same when resizing from right

                # Update position and rect
                self.prepareGeometryChange()
                self.setPos(new_pos)
                self.setRect(new_rect)

                # Update duration based on new width (important for timeline logic)
                pps = self.timeline_view.pixels_per_second
                self.duration = new_rect.width() / pps

                # Update start_time when dragging left edge
                if handle == self.Left:
                    self.start_time = new_pos.x() / pps
                    # Adjust in_point to maintain the same visible content
                    delta_seconds = (new_pos.x() - self.original_pos.x()) / pps
                    self.in_point = max(0, self.in_point - delta_seconds)

                event.accept()
            else:
                super().mouseMoveEvent(event)

        def mouseReleaseEvent(self, event):
            if self.is_resizing:
                self.is_resizing = False
                self.current_resize_handle = self.NoHandle
                self.setFlag(QGraphicsItem.ItemIsMovable, True)
                # self.save_pos()
                event.accept()
            else:
                super().mouseReleaseEvent(event)
                # self.save_pos()

        # # def save_pos(self):
        # #     new_loc_x = max(0, int(self.x()))
        # #     new_loc_y = max(0, int(self.y()))

        # #     current_size = self.member_proxy.size() # * self.member_proxy.scale()

        # #     members = self.workflow_settings.config.get('members', [])
        # #     member = next((m for m in members if m['id'] == self.id), None)

        # #     if member:
        # #         pos_changed = new_loc_x != member.get('loc_x') or new_loc_y != member.get('loc_y')
        # #         size_changed = not math.isclose(current_size.width(), member.get('width', 0)) or \
        # #                     not math.isclose(current_size.height(), member.get('height', 0))
        # #         if not pos_changed and not size_changed:
        # #             return

        # #     self.workflow_settings.update_config()

        def hoverMoveEvent(self, event):
            if self.is_resizing or not self.isSelected():  # or self.workflow_settings.view.mini_view:
                self.setCursor(Qt.ArrowCursor)
                super().hoverMoveEvent(event)
                return

            handle = self.get_handle_at(event.pos())
            if handle > 0:
                pass
            self.set_cursor_for_handle(handle)
            super().hoverMoveEvent(event)

        def hoverLeaveEvent(self, event):
            self.setCursor(Qt.ArrowCursor)
            super().hoverLeaveEvent(event)


class MemberConfigWidget(ConfigWidget):  # todo dedupe
    def __init__(self, parent):
        super().__init__(parent=parent)
        self.layout = CVBoxLayout(self)
        # self.object = None
        self.config_widget = None
        self.member_header_widget = HeaderFields(self)
        self.layout.addWidget(self.member_header_widget)
        self.hide()
    
    def load_config(self, json_config=None):
        super().load_config(json_config)
        self.member_header_widget.load_config(json_config)

    def get_config(self):
        if not self.config_widget:
            return {}
        header_config = self.member_header_widget.get_config()
        config = self.config_widget.get_config()
        return config | header_config

    def update_config(self):
        self.save_config()

    def save_config(self):
        if not self.config_widget:
            return
        config = self.get_config()

        studio = self.parent
        member_id = self.config_widget.member_id
        studio.timeline.clips[member_id].member_config = config
        studio.update_config()

    def display_member(self, **kwargs):
        clear_layout(self.layout, skip_count=1)
        member_type = kwargs.get('member_type', None)  # member.member_type)
        member_config = kwargs.get('member_config', None)  # , member.member_config)
        member_id = kwargs.get('member_id', None)  # , member.id)
        member = kwargs.get('member', None)  # member.member_type
        if member:
            member_type = member.member_type
            member_config = member.member_config
            member_id = member.member_id

        member_settings_class = get_member_settings_class(member_type)
        
        self.member_header_widget.setVisible(member_settings_class is not None)
        if not member_settings_class:
            return
        
        kwargs = {}
        self.config_widget = member_settings_class(self, **kwargs)
        self.config_widget.member_id = member_id
        self.rebuild_member(config=member_config)

        self.show()

    def rebuild_member(self, config):
        clear_layout(self.layout, skip_count=1)  # 
        member_type = config.get('_TYPE', 'video')

        member_class = system.manager.modules.get_module_class('Members', module_name=member_type)
        if member_class:
            default_avatar = getattr(member_class, 'default_avatar', '')
            self.member_header_widget.widgets[0].schema[0]['default'] = default_avatar
            self.member_header_widget.build_schema()

        self.member_header_widget.load_config(config)
        self.member_header_widget.load()
        
        self.config_widget.load_config(config)
        self.config_widget.build_schema()
        self.config_widget.load()
        self.layout.addWidget(self.config_widget)

        if hasattr(self.config_widget, 'reposition_view'):
            self.config_widget.reposition_view()


class TrackControlPanel(QWidget):
    """Panel containing controls for timeline tracks"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.studio = parent
        self.track_controls = []
        
        self.layout = CVBoxLayout(self)

        # Container for track controls
        self.tracks_container = QWidget()
        self.tracks_layout = CVBoxLayout(self.tracks_container)

        # Add track button at bottom
        self.add_track_btn = QPushButton("+ Add Track")
        self.add_track_btn.clicked.connect(self.on_add_track)

        # Layout assembly
        self.layout.addWidget(self.tracks_container)
        self.layout.addStretch(1)
        self.layout.addWidget(self.add_track_btn)
    
    def load(self):
        for track_control in self.track_controls:
            self.tracks_layout.removeWidget(track_control)
            track_control.deleteLater()
        self.track_controls = []

        tracks = self.studio.timeline.tracks
        for track_index, track_config in enumerate(tracks):
            track_control = self.TrackControl(self, track_index, track_config)
            self.track_controls.append(track_control)
            self.tracks_layout.addWidget(track_control)
    
    def get_config(self):
        return [track_control.get_config() for track_control in self.track_controls]

    def on_add_track(self):
        """Add a new track"""
        track_index = len(self.studio.timeline.tracks)
        track_config = {}
        self.studio.timeline.tracks.append(track_config)
        self.studio.load()
    
    def remove_track(self, track_index):
        self.studio.timeline.tracks.pop(track_index)
        self.studio.load()
    
    # def update_config(self):
    #     return  # block propagation
    
    class TrackControl(ConfigFields):
        def __init__(self, parent, track_index, track_config):
            super().__init__(parent)
            self.track_index = track_index
            self.setFixedHeight(60)
            # self.setProperty('class', 'track-control')  # Set CSS class for styling
            self.schema = [
                {
                    'type': str,
                    'text': 'Track Name',
                    'transparent': True,
                    'default': 'Track 1',
                    'stretch_x': True,
                    'label_position': None,
                    'row_key': 0,
                },
                # {
                #     'text': 'M',
                #     'type': 'button_toggle',
                #     'label_position': None,
                #     'default': False,
                #     'tooltip': 'Mute track',
                #     'row_key': 0,
                # },
                # {
                #     'text': 'S',
                #     'type': 'button_toggle',
                #     'label_position': None,
                #     'default': False,
                #     'tooltip': 'Solo track',
                #     'row_key': 0,
                # },
                {
                    'text': 'X',
                    'type': 'button',
                    'target': partial(parent.remove_track, self.track_index),
                    'label_position': None,
                    'default': False,
                    'tooltip': 'Remove track',
                    'row_key': 0,
                },
                {
                    'text': 'Volume',
                    'type': int,
                    'style': 'slider',
                    'minimum': 0,
                    'maximum': 100,
                    'default': 100,
                    'width': 50,
                    'label_position': None,
                    'row_key': 1,
                },
                {
                    'text': 'Pan',
                    'type': int,
                    'style': 'slider',
                    'minimum': -100,
                    'maximum': 100,
                    'default': 0,
                    'width': 50,
                    'left_label': 'L',
                    'right_label': 'R',
                    'show_slider_fill': False,
                    'slider_snap_to': 20,
                    'label_position': None,
                    'row_key': 1,
                },
            ]
            self.load_config(track_config)
            self.build_schema()
            self.load()

        # def update_config(self):
        #     """Propagate track config changes to VideoStudio.timeline.tracks."""
        #     super().update_config()
        #     studio = self.parent.studio
        #     studio.timeline.tracks[self.track_index] = self.get_config()


class PreviewClipItem(QGraphicsObject):
    """
    A transformable graphics item for the video preview.
    Wraps the video frame and provides handles for moving, resizing, and rotating.
    """
    # Handle constants
    NoHandle = 0
    TopLeft = 1
    TopRight = 2
    BottomLeft = 3
    BottomRight = 4
    # RotateHandle = 5  <-- Removed

    def __init__(self, media_member, parent=None):
        super().__init__(parent)
        self.preview_panel = self._get_preview_panel()
        self.media_member = media_member
        self.pixmap = None
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        
        # Visual settings
        self.handle_size = 10
        self.handle_brush = QBrush(QColor(255, 255, 255))
        self.handle_pen = QPen(QColor(0, 0, 0), 1)
        # self.border_pen = QPen(QColor(0, 120, 215), 2, Qt.DashLine)
        
        # State
        self.is_resizing = False
        self.is_rotating = False
        self.current_handle = self.NoHandle
        self.start_mouse_pos = QPointF()
        self.start_geometry = QRectF()
        self.start_rotation = 0.0
        self.start_scale = 1.0
        self.start_pos = QPointF()
        
        # Initialize transform from member
        self.update_from_member()

    def update_from_member(self):
        """Sync visual state from MediaMember data."""
        self.setPos(self.media_member.pos_x, self.media_member.pos_y)
        self.setRotation(self.media_member.rotation)
        self.setScale(self.media_member.scale)
        self.update_transform_origin()
        self.update()

    def update_transform_origin(self):
        """Set transform origin to center of content."""
        rect = self.content_rect()
        self.setTransformOriginPoint(rect.center())

    def set_pixmap(self, pixmap):
        self.pixmap = pixmap
        self.prepareGeometryChange()
        self.update_transform_origin()
        self.update()

    def boundingRect(self):
        if self.pixmap:
            w = self.pixmap.width()
            h = self.pixmap.height()
            # Include space for handles
            margin = self.handle_size
            return QRectF(-margin, -margin, w + 2*margin, h + 2*margin)
        return QRectF()

    def content_rect(self):
        if self.pixmap:
            return QRectF(0, 0, self.pixmap.width(), self.pixmap.height())
        return QRectF()

    def _get_preview_panel(self):
        """Get the VideoPreviewPanel from the scene."""
        scene = self.scene()
        if not scene:
            return None
        # The scene's parent should be the QGraphicsView, and its parent is the VideoPreviewPanel
        for view in scene.views():
            if view.parent() and isinstance(view.parent(), VideoPreviewPanel):
                return view.parent()
        return None

    def _get_canvas_rect_local(self):
        """Get canvas rect in local coordinates."""
        scene = self.scene()
        if not scene:
            return None
        # Find canvas rect (z-index -100)
        for item in scene.items():
            if isinstance(item, QGraphicsRectItem) and item.zValue() == -100:
                # Map canvas rect to local coordinates
                return self.mapRectFromScene(item.rect())
        return None

    def paint(self, painter, option, widget):
        if not self.pixmap:
            return

        canvas_local = self._get_canvas_rect_local()
        content = self.content_rect()

        if canvas_local:
            painter.save()
            # Draw outside canvas at 50% opacity
            outside_path = QPainterPath()
            outside_path.addRect(content)
            inside_path = QPainterPath()
            inside_path.addRect(canvas_local.intersected(content))
            outside_path = outside_path.subtracted(inside_path)

            painter.setClipPath(outside_path)
            painter.setOpacity(0.1)
            painter.drawPixmap(0, 0, self.pixmap)

            # Draw inside canvas at full opacity
            painter.setClipRect(canvas_local.intersected(content))
            painter.setOpacity(1.0)
            painter.drawPixmap(0, 0, self.pixmap)
            painter.restore()
        else:
            painter.drawPixmap(0, 0, self.pixmap)

        # Draw selection UI if selected
        if self.isSelected():
            rect = content

            # Draw border
            # painter.setPen(self.border_pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(rect)

            # Draw handles
            painter.setPen(self.handle_pen)
            painter.setBrush(self.handle_brush)

            # Corners
            handles = [
                (rect.topLeft(), self.TopLeft),
                (rect.topRight(), self.TopRight),
                (rect.bottomLeft(), self.BottomLeft),
                (rect.bottomRight(), self.BottomRight)
            ]

            hs = self.handle_size
            hs2 = hs / 2

            for pt, _ in handles:
                painter.drawRect(QRectF(pt.x() - hs2, pt.y() - hs2, hs, hs))

            # Rotation handle removed

    def get_handle_at(self, pos):
        if not self.isSelected():
            return self.NoHandle
            
        rect = self.content_rect()
        hs = self.handle_size
        hs2 = hs / 2
        
        # Check corners
        corners = [
            (rect.topLeft(), self.TopLeft),
            (rect.topRight(), self.TopRight),
            (rect.bottomLeft(), self.BottomLeft),
            (rect.bottomRight(), self.BottomRight)
        ]
        
        for pt, handle in corners:
            handle_rect = QRectF(pt.x() - hs2, pt.y() - hs2, hs, hs)
            if handle_rect.contains(pos):
                return handle

        return self.NoHandle

    def mousePressEvent(self, event):
        handle = self.get_handle_at(event.pos())
        
        # Check for Ctrl+Drag rotation
        if event.modifiers() & Qt.ControlModifier:
            self.is_rotating = True
            self.start_mouse_pos = event.scenePos()
            self.start_rotation = self.rotation()
            self.setFlag(QGraphicsItem.ItemIsMovable, False) # Disable move while rotating
            event.accept()
            return

        if handle != self.NoHandle:
            self.is_resizing = True
            self.current_handle = handle
            self.start_mouse_pos = event.scenePos()
            self.start_geometry = self.content_rect()
            self.start_scale = self.scale()
            self.start_pos = self.pos()
            
            # Determine opposite corner for anchoring
            rect = self.content_rect()
            if handle == self.TopLeft:
                self.opposite_corner_local = rect.bottomRight()
            elif handle == self.TopRight:
                self.opposite_corner_local = rect.bottomLeft()
            elif handle == self.BottomLeft:
                self.opposite_corner_local = rect.topRight()
            elif handle == self.BottomRight:
                self.opposite_corner_local = rect.topLeft()
                
            # Store opposite corner in scene coordinates (fixed point)
            self.opposite_corner_scene = self.mapToScene(self.opposite_corner_local)
            
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_resizing:
            current_pos = event.scenePos()

            # Calculate new scale based on distance change relative to opposite corner
            # We project the mouse movement onto the diagonal to maintain aspect ratio logic if needed,
            # but for uniform scaling we can just use distance ratio.

            start_dist = (self.start_mouse_pos - self.opposite_corner_scene).manhattanLength()
            current_dist = (current_pos - self.opposite_corner_scene).manhattanLength()

            if start_dist > 0:
                scale_factor = current_dist / start_dist
                new_scale = self.start_scale * scale_factor

                # Apply new scale
                self.setScale(new_scale)

                # Correct position to keep opposite corner fixed
                # After scaling, the opposite corner (in local coords) will map to a new scene position.
                # We need to shift the item so that it maps back to self.opposite_corner_scene.

                new_opposite_scene = self.mapToScene(self.opposite_corner_local)
                correction = self.opposite_corner_scene - new_opposite_scene
                self.setPos(self.pos() + correction)

                # Update model
                self.media_member.scale = new_scale
                self.media_member.member_config['scale'] = new_scale
                self.media_member.pos_x = self.pos().x()
                self.media_member.pos_y = self.pos().y()
                self.media_member.member_config['pos_x'] = self.pos().x()
                self.media_member.member_config['pos_y'] = self.pos().y()

        elif self.is_rotating:
            center = self.mapToScene(self.transformOriginPoint())
            current_pos = event.scenePos()
            
            angle = np.degrees(np.arctan2(current_pos.y() - center.y(), current_pos.x() - center.x()))
            start_angle = np.degrees(np.arctan2(self.start_mouse_pos.y() - center.y(), self.start_mouse_pos.x() - center.x()))
            
            delta_angle = angle - start_angle
            new_rotation = self.start_rotation + delta_angle
            
            self.setRotation(new_rotation)
            self.media_member.rotation = new_rotation
            self.media_member.member_config['rotation'] = new_rotation
            
        else:
            super().mouseMoveEvent(event)
            
    def mouseReleaseEvent(self, event):
        self.is_resizing = False
        self.is_rotating = False
        self.current_handle = self.NoHandle
        self.setFlag(QGraphicsItem.ItemIsMovable, True)  # Re-enable move

        # Hide snap lines when drag ends
        preview_panel = self._get_preview_panel()
        if preview_panel:
            preview_panel.hide_snap_lines()

        super().mouseReleaseEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            new_pos = QPointF(value)

            # Apply snapping if we have a preview panel
            preview_panel = self._get_preview_panel()
            if preview_panel and not self.is_resizing and not self.is_rotating:
                snapped_pos, active_lines = preview_panel.calculate_snap(self, new_pos)
                preview_panel.show_snap_lines(active_lines)
                new_pos = snapped_pos

            # Update member position
            self.media_member.pos_x = new_pos.x()
            self.media_member.pos_y = new_pos.y()
            self.media_member.member_config['pos_x'] = new_pos.x()
            self.media_member.member_config['pos_y'] = new_pos.y()

            return new_pos

        return super().itemChange(change, value)

    def hoverMoveEvent(self, event):
        # Check for Ctrl key for rotation cursor
        if event.modifiers() & Qt.ControlModifier:
             self.setCursor(Qt.PointingHandCursor) # Rotation cursor
             super().hoverMoveEvent(event)
             return

        handle = self.get_handle_at(event.pos())
        if handle in (self.TopLeft, self.BottomRight):
            self.setCursor(Qt.SizeFDiagCursor)
        elif handle in (self.TopRight, self.BottomLeft):
            self.setCursor(Qt.SizeBDiagCursor)
        else:
            self.setCursor(Qt.SizeAllCursor if self.isSelected() else Qt.ArrowCursor)
        super().hoverMoveEvent(event)


class VideoPreviewPanel(QWidget):
    """Enhanced video preview panel with playback controls."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.studio = parent
        self.playback_workers = {}  # clip_id -> (thread, worker)

        # Snap lines for preview items
        self.snap_lines = []  # List of QGraphicsLineItem for visual feedback
        self.snap_threshold_percent = 0.05  # 5% of canvas dimension
        
        self.seek_decode_thread = QThread()
        self.seek_decode_worker = VideoDecodeWorker()
        self.seek_decode_worker.moveToThread(self.seek_decode_thread)
        self.seek_decode_worker.frame_decoded.connect(lambda frame, time_seconds, clip_id: self.on_frame_decoded(frame, time_seconds, clip_id, set_playhead=False))
        self.seek_decode_thread.start()

        # Master timeline clock
        self.timeline_worker = None
        self.timeline_thread = None

        # state
        self.is_playing = False
        self.playback_speed = 1.0
        self.audio_player = _AudioPlayer(studio=self.studio)

        # Floating "Open in studio" button
        self.studio_button = QPushButton("Open in studio", self)
        self.studio_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(50, 50, 50, 200);
                color: white;
                border: 1px solid #666;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: rgba(70, 70, 70, 220);
            }
        """)
        self.studio_button.setCursor(Qt.PointingHandCursor)
        self.studio_button.clicked.connect(lambda: self.studio.set_fullscreen(False))
        self.studio_button.hide()


        self.studio_button.clicked.connect(lambda: self.studio.set_fullscreen(False))
        self.studio_button.hide()


        # self.preview_widget = QLabel()
        # self.preview_widget.setAlignment(Qt.AlignCenter)
        # self.preview_widget.setMinimumSize(320, 180)
        # self.preview_widget.setStyleSheet("background: #111; color: #fff;")
        
        # Graphics View for Preview
        self.scene = QGraphicsScene(self)
        self.preview_view = QGraphicsView(self.scene)
        self.preview_view.setRenderHint(QPainter.Antialiasing)
        self.preview_view.setRenderHint(QPainter.SmoothPixmapTransform)
        self.preview_view.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.preview_view.setBackgroundBrush(QBrush(QColor(20, 20, 20)))
        self.preview_view.setAlignment(Qt.AlignCenter)

        self.setup_ui()
        self.update_dimensions()

        # Enable mouse tracking to detect hover
        self.setMouseTracking(True)

    def setup_ui(self):
        """Build the preview panel UI."""
        layout = QVBoxLayout(self)

        # Frame preview widget
        layout.addWidget(self.preview_view)

        # Control panel
        controls = QHBoxLayout()
        
        # Play/Pause button
        self.play_button = QPushButton("▶")
        self.play_button.setFixedSize(40, 40)
        self.play_button.clicked.connect(self.toggle_playback)
        controls.addWidget(self.play_button)
        
        self.time_label = QLabel("00:00:00.00")
        self.time_label.setStyleSheet("QLabel { color: #fff; background: #222; padding: 5px; }")
        controls.addWidget(self.time_label)

        controls.addStretch()

        # Speed control
        controls.addWidget(QLabel("Speed:"))
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["0.25x", "0.5x", "1x", "1.5x", "2x"])
        self.speed_combo.setCurrentText("1x")
        controls.addWidget(self.speed_combo)
        
        # Mute button for audio
        self.mute_button = QPushButton("🔊")
        self.mute_button.setFixedSize(40, 40)
        self.mute_button.setCheckable(True)
        self.mute_button.setToolTip("Mute audio")
        self.mute_button.clicked.connect(self.toggle_mute)
        controls.addWidget(self.mute_button)

        layout.addLayout(controls)

    def update_dimensions(self):
        """Update scene dimensions and canvas indicator based on project settings."""
        width = getattr(self.studio, 'project_width', 1920)
        height = getattr(self.studio, 'project_height', 1080)

        # Scene rect is larger than canvas to allow off-canvas positioning
        margin = max(width, height)
        self.scene.setSceneRect(-margin, -margin, width + 2 * margin, height + 2 * margin)

        # Create or update canvas indicator
        if not hasattr(self, 'canvas_rect'):
            # Canvas background (what will be rendered)
            self.canvas_rect = self.scene.addRect(
                0, 0, width, height,
                QPen(Qt.NoPen),
                QBrush(QColor(30, 30, 30))  # Dark background for canvas area
            )
            self.canvas_rect.setZValue(-100)  # Behind everything

        else:
            # Update existing canvas rect and border
            self.canvas_rect.setRect(0, 0, width, height)

        # Fit view to show the canvas
        self.fit_canvas_in_view()
    
    # ---------- Playback control ----------
    def start_playback(self):
        """Start playback using master timeline worker."""
        if self.is_playing:
            return

        timeline_time = self.studio.timeline.get_playhead_position()
        
        # Start master clock
        self.timeline_thread = QThread()
        self.timeline_worker = TimelinePlaybackWorker(start_time=timeline_time)
        self.timeline_worker.moveToThread(self.timeline_thread)
        self.timeline_thread.started.connect(self.timeline_worker.run)
        self.timeline_worker.time_updated.connect(self.on_time_updated)
        self.timeline_worker.finished.connect(self.timeline_thread.quit)
        self.timeline_thread.start()

        # Start audio playback
        self.audio_player.play(timeline_time)

        self.is_playing = True
        self.play_button.setText("⏸")

    def stop_playback(self):
        """Stop playback and terminate all workers."""
        self.is_playing = False
        self.play_button.setText("▶")

        # Stop audio playback
        self.audio_player.stop()

        # Stop master clock
        if self.timeline_worker:
            self.timeline_worker.stop()
        if self.timeline_thread and self.timeline_thread.isRunning():
            self.timeline_thread.quit()
            self.timeline_thread.wait()
        self.timeline_worker = None
        self.timeline_thread = None

        # Stop all clip workers
        for clip_id, (thread, worker) in self.playback_workers.items():
            worker.stop()
            if thread.isRunning():
                thread.quit()
                thread.wait()
        
        self.playback_workers.clear()

    def on_time_updated(self, current_time: float):
        """Called by master clock every frame."""
        # Update UI
        self.studio.timeline.set_playhead_position(current_time)
        
        hours = int(current_time // 3600)
        minutes = int((current_time % 3600) // 60)
        seconds = int(current_time % 60)
        centiseconds = int((current_time % 1) * 100)
        self.time_label.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}")

        # Sync clip workers
        self.sync_playback_workers(current_time)

    def sync_playback_workers(self, current_time: float):
        """Start/stop decode workers based on active clips at current_time."""
        active_clips = self.get_active_clips_at_time(current_time)
        active_ids = {c.member_id for c in active_clips}

        # 1. Stop workers for clips that are no longer active
        # Use list(keys) to avoid runtime error during modification
        for clip_id in list(self.playback_workers.keys()):
            if clip_id not in active_ids:
                thread, worker = self.playback_workers[clip_id]
                worker.stop()
                if thread.isRunning():
                    thread.quit()
                    thread.wait()
                del self.playback_workers[clip_id]
                
                # Also hide/remove the preview item
                target_clip = self.studio.timeline.clips.get(clip_id)
                if target_clip:
                    for item in self.scene.items():
                        if isinstance(item, PreviewClipItem) and item.media_member == target_clip:
                            self.scene.removeItem(item)
                            break

        # 2. Start workers for new active clips
        for clip in active_clips:
            clip_id = clip.member_id
            if clip_id in self.playback_workers:
                continue
            
            filepath = clip.filepath
            if not os.path.exists(filepath):
                continue

            # Calculate start time for this clip
            clip_start_on_timeline = float(getattr(clip, "start_time", 0.0))
            in_point = float(getattr(clip, "in_point", 0.0))
            
            # Where are we in the clip?
            clip_local_time = current_time - clip_start_on_timeline + in_point
            clip_local_time = max(0.0, clip_local_time)

            # Create worker
            thread = QThread()
            worker = VideoDecodeWorker(filepath=filepath, start_time=clip_local_time, fps=30.0, clip_id=clip_id)
            worker.moveToThread(thread)
            thread.started.connect(worker.run)
            
            # Store timeline offset
            timeline_offset = clip_start_on_timeline - in_point
            
            worker.frame_decoded.connect(
                lambda frame, clip_time, cid=clip_id, offset=timeline_offset: 
                self.on_frame_decoded(frame, clip_time + offset, cid, set_playhead=False)
            )
            worker.finished.connect(thread.quit)
            
            thread.start()
            self.playback_workers[clip_id] = (thread, worker)
    
    def on_frame_decoded(self, frame, time_seconds, clip_id, set_playhead=True):
        """Called when a new frame is decoded by worker."""
        if frame is None:
            return

        # Convert numpy array → QPixmap
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        qimg = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()
        pixmap = QPixmap.fromImage(qimg)
        
        # Find or create PreviewClipItem for this clip_id
        preview_item = None
        target_clip = self.studio.timeline.clips.get(clip_id)

        if target_clip:
            for item in self.scene.items():
                if isinstance(item, PreviewClipItem) and item.media_member == target_clip:
                    preview_item = item
                    break

            if not preview_item:
                preview_item = PreviewClipItem(target_clip)
                self.scene.addItem(preview_item)

            preview_item.set_pixmap(pixmap)
            preview_item.setVisible(True)

        # Note: We no longer set playhead here during playback, 
        # as TimelinePlaybackWorker handles it.
        # We might still use set_playhead=True for seek operations (request_single_frame).
        if set_playhead:
            self.studio.timeline.set_playhead_position(time_seconds)
            
            # Update label
            hours = int(time_seconds // 3600)
            minutes = int((time_seconds % 3600) // 60)
            seconds = int(time_seconds % 60)
            centiseconds = int((time_seconds % 1) * 100)
            self.time_label.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}")

    # ---------- Clip helpers ----------
    def get_active_clips_at_time(self, time_seconds: float):
        """
        Return list of timeline clip objects active at `time_seconds`.
        A clip object is expected to have: start_time, in_point, out_point, filepath, track_index.
        """
        if not hasattr(self.studio.timeline, "clips"):
            return []
        active = []
        for clip in self.studio.timeline.clips.values():
            clip_start = clip.start_time
            clip_in = clip.in_point
            clip_out = clip.out_point
            clip_length = max(0.0, clip_out - clip_in)
            if clip_length <= 0:
                continue
            # active when timeline time is within clip timeline range
            if (time_seconds >= clip_start) and (time_seconds < (clip_start + clip_length)):
                active.append(clip)
        return active

    def request_single_frame(self, time_seconds: float):
        """Request a single frame decode in background for all active clips."""
        active = self.get_active_clips_at_time(time_seconds)

        # Identify clips that are no longer active and hide/remove their preview items
        active_ids = {c.member_id for c in active}
        for item in self.scene.items():
            if isinstance(item, PreviewClipItem):
                if item.media_member.member_id not in active_ids:
                    # Option 1: Remove item
                    self.scene.removeItem(item)
                    # Option 2: Hide item (might be better for performance if it comes back)
                    # item.setVisible(False)

        if not active:
            return

        for clip in active:
            filepath = clip.filepath
            clip_id = clip.member_id
            if not os.path.exists(filepath):
                continue

            # Timeline → clip-local mapping
            clip_start_on_timeline = float(getattr(clip, "start_time", 0.0))
            in_point = float(getattr(clip, "in_point", 0.0))
            duration = float(getattr(clip, "duration", 0.0))

            local_t = time_seconds - clip_start_on_timeline + in_point

            # Clamp to valid range [0, duration]
            if duration > 0.0:
                local_t = max(0.0, min(local_t, duration))
            else:
                local_t = max(0.0, local_t)

            # Emit request with specific filepath and clip_id
            self.seek_decode_worker.decode_request.emit(filepath, local_t, clip_id)

    def toggle_playback(self):
        """Toggle play/pause state."""
        if self.is_playing:
            self.stop_playback()
        else:
            self.start_playback()

    def toggle_mute(self):
        """Toggle audio mute."""
        is_muted = self.mute_button.isChecked()

        if is_muted:
            self.mute_button.setText("🔇")
            self.audio_player.set_muted(True)
        else:
            self.mute_button.setText("🔊")
            self.audio_player.set_muted(False)

            # Resume audio if playing
            if self.is_playing:
                current_time = self.studio.timeline.get_playhead_position()
                active_clips = self.get_active_clips_at_time(current_time)
                clips_data = []
                for clip in active_clips:
                    clips_data.append({
                        'filepath': clip.filepath,
                        'start_time': clip.start_time,
                        'in_point': clip.in_point,
                        'out_point': clip.out_point,
                        'track_index': clip.track_index
                    })
                self.audio_player.play(clips_data, current_time)

    def position_studio_button(self):
        """Position the studio button in the top right corner."""
        if not hasattr(self, 'studio_button'):
            return
        button_width = self.studio_button.sizeHint().width()
        button_height = self.studio_button.sizeHint().height()
        margin = 10
        x = self.width() - button_width - margin
        y = margin
        self.studio_button.setGeometry(x, y, button_width, button_height)
        self.studio_button.raise_()

    def resizeEvent(self, event):
        """Handle widget resize to reposition studio button and fit canvas in view."""
        super().resizeEvent(event)
        self.position_studio_button()
        self.fit_canvas_in_view()

    def fit_canvas_in_view(self):
        """Fit the canvas (project dimensions) into the view with some padding."""
        if not hasattr(self, 'preview_view') or not hasattr(self, 'canvas_rect'):
            return
        # Fit to the canvas rect (project dimensions), not the entire scene
        canvas_rect = self.canvas_rect.rect()
        # Add small padding around the canvas
        padding = 20
        padded_rect = QRectF(
            canvas_rect.x() - padding,
            canvas_rect.y() - padding,
            canvas_rect.width() + 2 * padding,
            canvas_rect.height() + 2 * padding
        )
        self.preview_view.fitInView(padded_rect, Qt.KeepAspectRatio)

    def get_canvas_snap_lines(self):
        """
        Return snap line positions for the canvas.
        Returns dict with keys: left, right, top, bottom, vcenter, hcenter
        Values are in scene coordinates.
        """
        if not hasattr(self, 'canvas_rect'):
            return {}
        rect = self.canvas_rect.rect()
        return {
            'left': rect.left(),
            'right': rect.right(),
            'top': rect.top(),
            'bottom': rect.bottom(),
            'vcenter': rect.center().x(),
            'hcenter': rect.center().y(),
        }

    def get_snap_threshold(self):
        """Get snap threshold in scene units (5% of canvas width/height)."""
        if not hasattr(self, 'canvas_rect'):
            return 50  # fallback
        rect = self.canvas_rect.rect()
        # Use average of width and height
        return max(rect.width(), rect.height()) * self.snap_threshold_percent

    def show_snap_lines(self, active_lines):
        """
        Show snap lines for the given set of line positions.
        active_lines: dict with keys like 'left', 'vcenter', etc. and bool values
        """
        self.hide_snap_lines()
        if not hasattr(self, 'canvas_rect'):
            return

        canvas = self.canvas_rect.rect()
        snap_positions = self.get_canvas_snap_lines()
        pen = QPen(QColor(255, 100, 100), 1, Qt.DashLine)
        pen.setCosmetic(True)

        for key, should_show in active_lines.items():
            if not should_show:
                continue
            pos = snap_positions.get(key)
            if pos is None:
                continue

            # Vertical lines (left, right, vcenter)
            if key in ('left', 'right', 'vcenter'):
                line = QGraphicsLineItem(pos, canvas.top() - 100, pos, canvas.bottom() + 100)
            # Horizontal lines (top, bottom, hcenter)
            else:
                line = QGraphicsLineItem(canvas.left() - 100, pos, canvas.right() + 100, pos)

            line.setPen(pen)
            line.setZValue(1000)
            self.scene.addItem(line)
            self.snap_lines.append(line)

    def hide_snap_lines(self):
        """Remove all visible snap lines from the scene."""
        for line in self.snap_lines:
            self.scene.removeItem(line)
        self.snap_lines.clear()

    def calculate_snap(self, clip_item, new_pos):
        """
        Calculate snapped position for a PreviewClipItem.
        Returns (snapped_pos, active_snap_lines_dict).
        """
        if not hasattr(self, 'canvas_rect') or not clip_item.pixmap:
            return new_pos, {}

        canvas_snaps = self.get_canvas_snap_lines()
        threshold = self.get_snap_threshold()
        active_lines = {}

        # Get clip bounds in scene coordinates at new_pos
        # The clip's content rect is at (0,0) in local coords
        content = clip_item.content_rect()
        scale = clip_item.scale()

        # Calculate clip edges at the proposed position
        clip_left = new_pos.x()
        clip_right = new_pos.x() + content.width() * scale
        clip_top = new_pos.y()
        clip_bottom = new_pos.y() + content.height() * scale
        clip_vcenter = new_pos.x() + (content.width() * scale) / 2
        clip_hcenter = new_pos.y() + (content.height() * scale) / 2

        snapped_x = new_pos.x()
        snapped_y = new_pos.y()

        # Check horizontal snaps (affects X position)
        best_x_snap = None
        best_x_dist = threshold

        # Check vertical snaps (affects Y position)
        best_y_snap = None
        best_y_dist = threshold

        clip_h_snaps = [clip_left, clip_right, clip_vcenter]
        clip_v_snaps = [clip_top, clip_bottom, clip_hcenter]

        for clip_snap in clip_h_snaps:
            for snap_key in ('left', 'vcenter', 'right'):
                snap_pos = canvas_snaps.get(snap_key)
                if snap_pos is None:
                    continue
                dist = abs(clip_snap - snap_pos)
                if dist < best_x_dist:
                    best_x_dist = dist
                    best_x_snap = (snap_key, snap_pos - clip_snap + new_pos.x(), snap_key)

        for clip_snap in clip_v_snaps:
            for snap_key in ('top', 'hcenter', 'bottom'):
                snap_pos = canvas_snaps.get(snap_key)
                if snap_pos is None:
                    continue
                dist = abs(clip_snap - snap_pos)
                if dist < best_y_dist:
                    best_y_dist = dist
                    best_y_snap = (snap_key, snap_pos - clip_snap + new_pos.y(), snap_key)

        if best_x_snap:
            snapped_x = best_x_snap[1]
            active_lines[best_x_snap[2]] = True

        if best_y_snap:
            snapped_y = best_y_snap[1]
            active_lines[best_y_snap[2]] = True

        return QPointF(snapped_x, snapped_y), active_lines

    def enterEvent(self, event):
        """Show studio button when mouse enters, but only if in fullscreen mode."""
        super().enterEvent(event)
        if self.studio.full_screen:
            self.studio_button.show()

    def leaveEvent(self, event):
        """Hide studio button when mouse leaves."""
        super().leaveEvent(event)
        self.studio_button.hide()
    
    def closeEvent(self, event):
        # Stop audio playback
        self.audio_player.stop()

        # Clean up all playback workers
        for thread, worker in self.playback_workers.values():
            worker.stop()
            if thread.isRunning():
                thread.quit()
                thread.wait()
        
        # Clean up seek decode thread
        if self.seek_decode_thread and self.seek_decode_thread.isRunning():
            self.seek_decode_thread.quit()
            self.seek_decode_thread.wait()
        
        # Clean up timeline thread
        if hasattr(self, 'timeline_thread') and self.timeline_thread and self.timeline_thread.isRunning():
            self.timeline_worker.stop()
            self.timeline_thread.quit()
            self.timeline_thread.wait()
            
        super().closeEvent(event)


class TimelinePlaybackWorker(QObject):
    """Worker that acts as a master clock for timeline playback."""
    time_updated = Signal(float)
    finished = Signal()

    def __init__(self, start_time=0.0, fps=30.0, parent=None):
        super().__init__(parent)
        self.current_time = start_time
        self.fps = fps
        self._running = True

    def stop(self):
        self._running = False

    def run(self):
        frame_duration = 1.0 / self.fps
        start_wall_time = time.time()
        start_timeline_time = self.current_time

        while self._running:
            now = time.time()
            elapsed = now - start_wall_time
            self.current_time = start_timeline_time + elapsed
            
            self.time_updated.emit(self.current_time)
            
            # Simple sleep to maintain approx FPS, though wall-clock diff is used for accuracy
            time.sleep(frame_duration)
        
        self.finished.emit()


class VideoDecodeWorker(QObject):
    """Worker for sequential frame decoding using MoviePy.iter_frames()."""
    frame_decoded = Signal(np.ndarray, float, str)  # (frame, time_seconds, clip_id)
    finished = Signal()
    # new signal for requesting single frame decode (to connect externally)
    decode_request = Signal(str, float, str) # (filepath, time, clip_id)


    def __init__(self, filepath=None, start_time=0.0, fps=30.0, clip_id=None, parent=None):
        super().__init__(parent)
        self.filepath = filepath
        self.start_time = start_time
        self.fps = fps
        self.clip_id = clip_id
        self._running = True

        self._current_task = None
        self.decode_request.connect(self._on_decode_request)

    @Slot(str, float, str)
    def _on_decode_request(self, filepath: str, timestamp: float, clip_id: str):
        """Internal slot for decoding a single frame."""
        task_id = (filepath, timestamp, clip_id)
        self._current_task = task_id

        try:
            if not filepath or not os.path.exists(filepath):
                print(f"Filepath not found: {filepath}")
                return

            # Check if this is still the current task before expensive operations
            if self._current_task != task_id:
                return

            with VideoFileClip(filepath) as clip:
                # Check again before get_frame (most expensive operation)
                if self._current_task != task_id:
                    return

                timestamp = max(0.0, min(timestamp, clip.duration or 0.0))
                frame = clip.get_frame(timestamp)

                # Final check before emitting
                if self._current_task == task_id:
                    self.frame_decoded.emit(frame, timestamp, clip_id)
        except Exception as e:
            print(f"[SeekDecodeWorker Error] {e}")

    def stop(self):
        self._running = False

    def run(self):
        try:
            with VideoFileClip(self.filepath) as clip:
                frame_duration = 1.0 / self.fps
                # Start iteration from the specified start time
                start_t = max(0, min(self.start_time, clip.duration - 0.001))  # Small offset to avoid edge case

                if start_t >= clip.duration:
                    print(f"[DecodeWorker] Start time {start_t} is beyond clip duration {clip.duration}")
                    return

                subclip = clip.subclipped(start_t)
                frame_gen = subclip.iter_frames(fps=self.fps, dtype="uint8", with_times=True)

                for t, frame in frame_gen:
                    if not self._running:
                        break

                    # Adjust time to be relative to the original clip
                    actual_time = t + start_t
                    self.frame_decoded.emit(frame, actual_time, self.clip_id)
                    time.sleep(frame_duration)
                    
        except Exception as e:
            print(f"[DecodeWorker Error] {e}")
        finally:
            self.finished.emit()


def get_media_duration(filepath: str) -> float:
    """
    Get duration of media file in seconds using MoviePy.

    Falls back to a default duration if the file cannot be opened or is not
    a supported audio/video type.
    """
    if not filepath or not os.path.exists(filepath):
        return 5.0

    ext = os.path.splitext(filepath)[1].lower()

    # Images don't have a duration – keep a small default like before.
    if ext in {".png", ".jpg", ".jpeg"}:
        return 5.0

    try:
        # Audio files
        if ext in {".mp3", ".wav", ".flac", ".ogg"}:
            with AudioFileClip(filepath) as clip:
                return float(clip.duration)

        # Everything else we treat as video
        with VideoFileClip(filepath) as clip:
            return float(clip.duration)

    except Exception:
        # Fallback to default duration if MoviePy fails
        return 5.0


class _AudioPlayer(QObject):
    """Multi-clip audio player using Qt's multimedia system for timeline audio playback."""

    def __init__(self, studio):
        super().__init__()
        self.timeline = studio.timeline
        self._muted = False
        self.is_playing = False
        self.clip_players = {}

    def set_muted(self, muted: bool):
        self._muted = bool(muted)
        for _, (_, audio_output, _) in self.clip_players.items():
            audio_output.setMuted(self._muted)

    def is_muted(self) -> bool:
        return self._muted

    def play(self, timeline_time: float):
        self.stop()
        for clip in self.timeline.clips.values():
            filepath = clip.filepath

            if not filepath or not os.path.exists(filepath):
                continue

            player = self._create_clip_player(clip)
            player.setSource(QUrl.fromLocalFile(filepath))

        for _, (player, _, clip) in self.clip_players.items():
            clip_start = float(clip.start_time)
            in_point = float(clip.in_point)
            out_point = float(clip.out_point)

            # Calculate the position in the actual media file
            media_position = (timeline_time - clip_start) + in_point

            # Set position and start playback
            position_ms = int(media_position * 1000)

            player.play()
            QTimer.singleShot(50, lambda: player.setPosition(position_ms))

        self.is_playing = True

    def stop(self):
        """Stop all audio playback."""
        for clip_id in list(self.clip_players.keys()):
            player, audio_output, _ = self.clip_players[clip_id]
            player.stop()
            player.setSource(QUrl())  # Clear source
            player.deleteLater()
            audio_output.deleteLater()
            del self.clip_players[clip_id]
        self.is_playing = False

    def _create_clip_player(self, clip):
        clip_id = clip.member_id
        player = QMediaPlayer(self)
        audio_output = QAudioOutput(self)
        audio_output.setMuted(self._muted)
        player.setAudioOutput(audio_output)

        # Connect error handling
        player.errorOccurred.connect(lambda error: self._on_error(clip_id, error))

        self.clip_players[clip_id] = (player, audio_output, clip)
        return player

    def _on_error(self, clip_id: str, error):
        """Handle media player errors for a specific track."""
        if error != QMediaPlayer.NoError:
            player = self.clip_players.get(clip_id, (None,))[0]
            if player:
                print(f"Audio playback error on clip {clip_id}: {player.errorString()}")


# class MediaListWidget(QListWidget):
#     """Custom QListWidget that includes filepath in drag mime data."""

#     def mimeData(self, items):
#         """Return mime data with filepath stored in UserRole."""
#         mime_data = QMimeData()
#         urls = []
#         for item in items:
#             filepath = item.data(Qt.UserRole)
#             if filepath:
#                 urls.append(QUrl.fromLocalFile(filepath))
#         if urls:
#             mime_data.setUrls(urls)
#         return mime_data


# class MediaBin(QWidget):
#     """Media bin for imported files."""

#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.layout = CVBoxLayout(self)

#         header = QLabel("Media Bin")
#         self.layout.addWidget(header)

#         self.media_list = MediaListWidget()
#         self.media_list.setDragEnabled(True)
#         self.layout.addWidget(self.media_list)

#         button_layout = CHBoxLayout()
#         self.import_button = QPushButton("Import")
#         self.import_button.clicked.connect(self.import_media)
#         button_layout.addWidget(self.import_button)

#         self.remove_button = QPushButton("Remove")
#         self.remove_button.clicked.connect(self.remove_media)
#         button_layout.addWidget(self.remove_button)

#         self.layout.addLayout(button_layout)

#         self.setAcceptDrops(True)

#         # Keep a simple list of media filepaths for serialization & quick checks
#         self.media_files = []

#     def get_config(self):
#         return {
#             self.media_list.item(i).text(): self.media_list.item(i).data(Qt.UserRole)
#             for i in range(self.media_list.count())
#         }

#     def add_media(self, filepath):
#         """Add a media file to the bin if not already present."""
#         if not filepath or not os.path.exists(filepath):
#             return
#         if filepath in self.media_files:
#             return
#         filename = os.path.basename(filepath)
#         item = QListWidgetItem(filename)
#         item.setData(Qt.UserRole, filepath)
#         self.media_list.addItem(item)
#         self.media_files.append(filepath)

#     def dragEnterEvent(self, event):
#         """Handle drag enter event."""
#         if event.mimeData().hasUrls():
#             event.acceptProposedAction()
#         else:
#             event.ignore()

#     def dropEvent(self, event):
#         """Handle drop event - import all dropped files."""
#         if event.mimeData().hasUrls():
#             for url in event.mimeData().urls():
#                 filepath = url.toLocalFile()
#                 if os.path.exists(filepath) and filepath not in self.media_files:
#                     self.add_media(filepath)
#             event.acceptProposedAction()
#         else:
#             event.ignore()

#     def import_media(self):
#         """Import media files."""
#         files, _ = QFileDialog.getOpenFileNames(
#             self,
#             "Import Media",
#             "",
#             "Media Files (*.mp4 *.avi *.mov *.mkv *.mp3 *.wav *.png *.jpg *.jpeg);;All Files (*)"
#         )

#         for filepath in files:
#             self.add_media(filepath)

#     def remove_media(self):
#         """Remove selected media."""
#         current = self.media_list.currentRow()
#         if current >= 0:
#             item = self.media_list.takeItem(current)
#             if item:
#                 filepath = item.data(Qt.UserRole)
#                 try:
#                     self.media_files.remove(filepath)
#                 except ValueError:
#                     pass
