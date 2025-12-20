"""Video Studio Page Module.

This module provides a comprehensive video editing interface for Agent Pilot,
enabling users to create, edit, and export video projects similar to Kdenlive.

Key Features:
- Multi-track timeline editing with drag-and-drop
- Real-time video preview with playback controls
- Media bin for organizing imported media files
- Effects and transitions library
- Clip manipulation (trim, split, cut, delete, move)
- Project save/load functionality
- Video export capabilities
- Multiple video/audio tracks support
- Zoom controls for precise editing
- Playhead scrubbing and position control

The page provides a full-featured non-linear video editing experience while
maintaining consistency with the Agent Pilot interface.
"""

from gui.studios.video_studio import VideoStudio
from gui.widgets.config_db_tree import ConfigDBTree
from utils.helpers import set_module_type


# @set_module_type('Pages')
# class Page_Videos(ConfigDBTree):
#     display_name = 'Videos'
#     icon_path = ":/resources/icon-video.png"
#     page_type = 'any'

#     def __init__(self, parent):
#         super().__init__(
#             parent=parent,
#             manager='blocks',
#             query="""
#                 SELECT
#                     name,
#                     id,
#                     uuid,
#                     folder_id,
#                     parent_id
#                 FROM blocks
#                 ORDER BY pinned DESC, ordr, name COLLATE NOCASE""",
#             schema=[
#                 {
#                     'text': 'Name',
#                     'key': 'name',
#                     'type': str,
#                     'stretch': True,
#                 },
#                 {
#                     'text': 'id',
#                     'key': 'id',
#                     'type': int,
#                     'visible': False,
#                 },
#                 {
#                     'text': 'uuid',
#                     'key': 'uuid',
#                     'type': str,
#                     'visible': False,
#                 },
#             ],
#             readonly=False,
#             layout_type='horizontal',
#             tree_header_hidden=True,
#             default_item_icon=':/resources/icon-block.png',
#             config_widget=self.Block_Config_Widget(parent=self),
#             folder_config_widget=self.Folder_Config_Widget(parent=self),
#             folder_key='blocks',
#             support_item_nesting=True,
#             searchable=True,
#             has_chat=True,
#         )
#         self.splitter.setSizes([400, 1000])


@set_module_type('Pages')
class Page_Videos(VideoStudio):
    display_name = 'Videos'
    icon_path = ":/resources/icon-video.png"
    page_type = 'any'

    def __init__(self, parent):
        super().__init__(parent=parent, full_screen=False)
