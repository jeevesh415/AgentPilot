from PySide6.QtWidgets import QMessageBox

from gui import system
from gui.fields.model import ModelComboBox
from gui.widgets.config_db_tree import ConfigDBTree
from gui.widgets.config_fields import ConfigFields
from gui.widgets.config_tabs import ConfigTabs
from gui.util import clear_layout, find_ancestor_tree_item_id
from utils import sql
from utils.helpers import display_message_box, display_message
from utils.media import play_url
from utils.reset import reset_models


class Page_Models_Settings(ConfigDBTree):
    display_name = 'Models'
    page_type = 'settings'  # either 'settings', 'main', or 'any' ('any' means it can be pinned between main and settings)

    def __init__(self, parent):
        super().__init__(
            parent=parent,
            table_name='apis',
            query="""
                SELECT
                    name,
                    id,
                    client_key,
                    api_key
                FROM apis
                ORDER BY 
                    pinned DESC, 
                    api_key != '' DESC, 
                    name""",
            schema=[
                {
                    'text': 'Provider',
                    'key': 'name',
                    'type': str,
                    'width': 150,
                },
                {
                    'text': 'id',
                    'key': 'id',
                    'type': int,
                    'visible': False,
                },
                {
                    'text': 'Client Key',
                    'key': 'client_key',
                    'type': str,
                    'width': 100,
                },
                {
                    'text': 'API Key',
                    'type': str,
                    'encrypt': True,
                    'stretch': True,
                },
            ],
            add_item_options={'title': 'Add API', 'prompt': 'Enter a name for the API:'},
            del_item_options={'title': 'Delete API', 'prompt': 'Are you sure you want to delete this API?'},
            readonly=False,
            layout_type='vertical',
            config_widget=self.Kinds_Tab_Widget(parent=self),
            extra_tree_buttons=[
                {
                    'text': 'Sync models',
                    'icon_path': ':/resources/icon-refresh.png',
                    'target': self.sync_models,
                },
            ],
        )

    def sync_models(self):
        res = display_message_box(
            icon=QMessageBox.Question,
            text="This will reset your APIs and models to the latest known models.\nAll model parameters will be reset\nAPI keys will be preserved\nAre you sure you want to continue?",
            title="Reset APIs and models",
            buttons=QMessageBox.Yes | QMessageBox.No,
        )

        if res != QMessageBox.Yes:
            return

        reset_models()
        
        self.on_edited()
        self.load()

        display_message('Models synced successfully', 'Success')

    def on_edited(self):
        system.manager.apis.load()
        system.manager.providers.load()
        for model_combobox in self.parent.main.findChildren(ModelComboBox):
            model_combobox.load()
    
    class Kinds_Tab_Widget(ConfigTabs):
        def __init__(self, parent):
            super().__init__(parent=parent)
            self.provider = None
            self.pages = {
                'Chat': self.Tab_Kind(parent=self, kind='CHAT'),
                'Video': self.Tab_Kind(parent=self, kind='VIDEO'),
                'Image': self.Tab_Kind(parent=self, kind='IMAGE'),
                'Audio': self.Tab_Kind(parent=self, kind='AUDIO'),
                '3D': self.Tab_Kind(parent=self, kind='3D'),
            }
        
        def load_config(self, json_config=None):
            super().load_config(json_config)

            api_id = find_ancestor_tree_item_id(self)
            kinds_in_api = sql.get_results("""
                SELECT DISTINCT kind
                FROM models
				WHERE api_id = ?""", (api_id,), return_type='list'
            )

            while self.content.count() > 0:
                self.content.removeTab(0)

            for tab_name, tab_widget in self.pages.items():
                is_visible = tab_name.upper() in kinds_in_api
                if is_visible:
                    self.content.addTab(tab_widget, tab_name)

            if self.content.count() > 0:
                self.content.setCurrentIndex(0)

        class Tab_Kind(ConfigTabs):
            def __init__(self, parent, kind):
                super().__init__(parent=parent)
                self.kind = kind
                self.pages = {
                    'Models': self.Tab_Kind_Models(parent=self),
                    'Config': self.Tab_Kind_Config(parent=self),
                }
            
            class Tab_Kind_Models(ConfigDBTree):
                def __init__(self, parent):
                    super().__init__(
                        parent=parent,
                        table_name='models',
                        kind=parent.kind,
                        query="""
                            SELECT
                                name,
                                id
                            FROM models
                            WHERE api_id = :api_id
                                AND kind = :kind
                            ORDER BY pinned DESC, name COLLATE NOCASE""",
                        query_params={
                            'api_id': lambda: find_ancestor_tree_item_id(self.parent),
                        },
                        schema=[
                            {
                                'text': 'Name',
                                'key': 'name',
                                'type': str,
                                'stretch': True,
                            },
                            {
                                'text': 'id',
                                'key': 'id',
                                'type': int,
                                'visible': False,
                            },
                        ],
                        add_item_options={'title': 'Add Model', 'prompt': 'Enter a name for the model:'},
                        del_item_options={'title': 'Delete Model', 'prompt': 'Are you sure you want to delete this model?'},
                        layout_type='horizontal',
                        readonly=False,
                        config_widget=self.Kind_Model_Params(parent=self),
                        tree_header_hidden=True,
                    )

                def on_edited(self):
                    parent = self.parent
                    while parent:
                        if hasattr(parent, 'on_edited'):
                            parent.on_edited()
                            return
                        parent = getattr(parent, 'parent', None)
                
                def on_item_selected(self):
                    model_id = self.get_selected_item_id()
                    if not model_id:
                        clear_layout(self.config_widget.layout)
                        return

                    model_metadata = sql.get_scalar("""
                        SELECT metadata
                        FROM models
                        WHERE id = ?
                    """, (model_id,), load_json=True)

                    model_input_schema = model_metadata.get('input_schema', [])

                    self.config_widget.schema = model_input_schema
                    self.config_widget.build_schema()
                    super().on_item_selected()

                class Kind_Model_Params(ConfigFields):
                    def __init__(self, parent):
                        super().__init__(
                            parent=parent,
                            auto_label_width=True
                        )
                        self.schema = []

            class Tab_Kind_Config(ConfigFields):
                def __init__(self, parent):
                    super().__init__(
                        parent=parent,
                        auto_label_width=True
                    )
                    self.schema = []


    # # class Models_Tab_Widget(ConfigTabs):
    # #     def __init__(self, parent):
    # #         super().__init__(parent=parent)
    # #         self.provider = None
    # #         self.pages = {}
    # #         #     'Chat': self.Tab_Chat(parent=self),
    # #         #     'Image': self.Tab_Image(parent=self),
    # #         #     'Video': self.Tab_Video(parent=self),
    # #         #     'Voice': self.Tab_Voice(parent=self),
    # #         #     'Speech': self.Tab_Voice(parent=self),
    # #         #     'Embedding': self.Tab_Voice(parent=self),
    # #         # }

    # #     @override
    # #     def load_config(self, json_config=None):
    # #         """Called when parent tree item is selected"""
    # #         super().load_config(json_config)

    # #         api_id = find_ancestor_tree_item_id(self)
    # #         kinds_in_api = sql.get_results("""
    # #             SELECT DISTINCT kind
    # #             FROM models
	# # 			WHERE api_id = ?""", (api_id,), return_type='list')

    # #         # Rebuild tabs to force proper layout recalculation
    # #         # Remove all tabs from the widget (but keep references in self.pages)
    # #         while self.content.count() > 0:
    # #             self.content.removeTab(0)

    # #         # Re-add only visible tabs using self.pages dictionary
    # #         for tab_name, tab_widget in self.pages.items():
    # #             is_visible = tab_name.upper() in kinds_in_api
    # #             if is_visible:
    # #                 self.content.addTab(tab_widget, tab_name)
    # #                 print(f"Tab {tab_name} added (visible)")
    # #             else:
    # #                 print(f"Tab {tab_name} skipped (hidden)")

    # #         # Set current tab to the first one (all tabs in the widget are now visible)
    # #         if self.content.count() > 0:
    # #             self.content.setCurrentIndex(0)

    #     # class Tab_Chat(ConfigTabs):
    #     #     def __init__(self, parent):
    #     #         super().__init__(parent=parent)
    #     #         self.type_model_params_class = None
    #     #         self.pages = {
    #     #             'Models': self.Tab_Chat_Models(parent=self),
    #     #             'Config': self.Tab_Chat_Config(parent=self),
    #     #         }

    #     #     class Tab_Chat_Models(ConfigDBTree):
    #     #         def __init__(self, parent):
    #     #             super().__init__(
    #     #                 parent=parent,
    #     #                 table_name='models',
    #     #                 kind='CHAT',
    #     #                 query="""
    #     #                     SELECT
    #     #                         name,
    #     #                         id
    #     #                     FROM models
    #     #                     WHERE api_id = :api_id
    #     #                         AND kind = :kind
    #     #                     ORDER BY pinned DESC, name COLLATE NOCASE""",
    #     #                 query_params={
    #     #                     'api_id': lambda: find_ancestor_tree_item_id(self.parent),
    #     #                     # lambda: self.kind,
    #     #                 },
    #     #                 schema=[
    #     #                     {
    #     #                         'text': 'Name',
    #     #                         'key': 'name',
    #     #                         'type': str,
    #     #                         'stretch': True,
    #     #                     },
    #     #                     {
    #     #                         'text': 'id',
    #     #                         'key': 'id',
    #     #                         'type': int,
    #     #                         'visible': False,
    #     #                     },
    #     #                 ],
    #     #                 add_item_options={'title': 'Add Model', 'prompt': 'Enter a name for the model:'},
    #     #                 del_item_options={'title': 'Delete Model', 'prompt': 'Are you sure you want to delete this model?'},
    #     #                 layout_type='horizontal',
    #     #                 readonly=False,
    #     #                 config_widget=self.Chat_Model_Params_Tabs(parent=self),
    #     #                 tree_header_hidden=True,
    #     #             )

    #     #             # # add sync button
    #     #             # btn_sync = IconButton(
    #     #             #     parent=self.tree_buttons,
    #     #             #     icon_path=':/resources/icon-refresh.png',
    #     #             #     tooltip='Sync models',
    #     #             #     size=22,
    #     #             # )
    #     #             # self.tree_buttons.add_button(btn_sync, 'btn_sync')

    #     #         def on_edited(self):
    #     #             # # bubble upwards towards root until we find `reload_models` method
    #     #             parent = self.parent
    #     #             while parent:
    #     #                 if hasattr(parent, 'on_edited'):
    #     #                     parent.on_edited()
    #     #                     return
    #     #                 parent = getattr(parent, 'parent', None)

    #     #         class Chat_Model_Params_Tabs(ConfigFields):
    #     #             def __init__(self, parent):
    #     #                 super().__init__(parent=parent)
    #     #                 self.parent = parent
    #     #                 self.schema = []

    #     #     class Tab_Chat_Config(ConfigFields):
    #     #         def __init__(self, parent):
    #     #             super().__init__(parent=parent)
    #     #             self.label_width = 125
    #     #             self.schema = [
    #     #                 {
    #     #                     'text': 'Api Base',
    #     #                     'type': str,
    #     #                     'label_width': 150,
    #     #                     'width': 265,
    #     #                     'has_toggle': True,
    #     #                     'tooltip': 'The base URL for the API. This will be used for all models under this API',
    #     #                     'default': '',
    #     #                 },
    #     #                 {
    #     #                     'text': 'Litellm prefix',
    #     #                     'type': str,
    #     #                     'label_width': 150,
    #     #                     'width': 118,
    #     #                     'has_toggle': True,
    #     #                     'tooltip': 'The API provider prefix to be prepended to all model names under this API',
    #     #                     'row_key': 'F',
    #     #                     'default': '',
    #     #                 },
    #     #                 {
    #     #                     'text': 'Custom provider',
    #     #                     'type': str,
    #     #                     'label_width': 140,
    #     #                     'width': 118,
    #     #                     'has_toggle': True,
    #     #                     'tooltip': 'The custom provider for LiteLLM. Usually not needed.',
    #     #                     'row_key': 'F',
    #     #                     'default': '',
    #     #                 },
    #     #                 {
    #     #                     'text': 'Temperature',
    #     #                     'type': float,
    #     #                     'label_width': 150,
    #     #                     'has_toggle': True,
    #     #                     'minimum': 0.0,
    #     #                     'maximum': 1.0,
    #     #                     'step': 0.05,
    #     #                     'tooltip': 'When enabled, this will be the default temperature for all models under this API',
    #     #                     'row_key': 'A',
    #     #                     'default': 0.6,
    #     #                 },
    #     #                 {
    #     #                     'text': 'API version',
    #     #                     'type': str,
    #     #                     'label_width': 140,
    #     #                     'width': 118,
    #     #                     'has_toggle': True,
    #     #                     'row_key': 'A',
    #     #                     'tooltip': 'The api version passed to LiteLLM. Usually not needed.',
    #     #                     'default': '',
    #     #                 },
    #     #                 {
    #     #                     'text': 'Top P',
    #     #                     'type': float,
    #     #                     'label_width': 150,
    #     #                     'has_toggle': True,
    #     #                     'minimum': 0.0,
    #     #                     'maximum': 1.0,
    #     #                     'step': 0.05,
    #     #                     'tooltip': 'When enabled, this will be the default `Top P` for all models under this API',
    #     #                     'row_key': 'B',
    #     #                     'default': 1.0,
    #     #                 },
    #     #                 {
    #     #                     'text': 'Frequency penalty',
    #     #                     'type': float,
    #     #                     'has_toggle': True,
    #     #                     'label_width': 140,
    #     #                     'minimum': -2.0,
    #     #                     'maximum': 2.0,
    #     #                     'step': 0.2,
    #     #                     'row_key': 'B',
    #     #                     'default': 0.0,
    #     #                 },
    #     #                 {
    #     #                     'text': 'Max tokens',
    #     #                     'type': int,
    #     #                     'has_toggle': True,
    #     #                     'label_width': 150,
    #     #                     'minimum': 1,
    #     #                     'maximum': 999999,
    #     #                     'step': 1,
    #     #                     'row_key': 'D',
    #     #                     'tooltip': 'When enabled, this will be the default `Max tokens` for all models under this API',
    #     #                     'default': 100,
    #     #                 },
    #     #                 {
    #     #                     'text': 'Presence penalty',
    #     #                     'type': float,
    #     #                     'has_toggle': True,
    #     #                     'label_width': 140,
    #     #                     'minimum': -2.0,
    #     #                     'maximum': 2.0,
    #     #                     'step': 0.2,
    #     #                     'row_key': 'D',
    #     #                     'default': 0.0,
    #     #                 },
    #     #             ]

    #     #     # class Tab_Chat_Config(ConfigFields):
    #     #     #     def __init__(self, parent):
    #     #     #         super().__init__(parent=parent)
    #     #     #         self.label_width = 125
    #     #     #         self.schema = []

    #     # class Tab_Image(ConfigTabs):
    #     #     def __init__(self, parent):
    #     #         super().__init__(parent=parent)

    #     #         self.pages = {
    #     #             'Models': self.Tab_Image_Models(parent=self),
    #     #             'Config': self.Tab_Image_Config(parent=self),
    #     #         }

    #     #     class Tab_Image_Models(ConfigDBTree):
    #     #         def __init__(self, parent):
    #     #             super().__init__(
    #     #                 parent=parent,
    #     #                 table_name='models',
    #     #                 kind='IMAGE',
    #     #                 query="""
    #     #                     SELECT
    #     #                         name,
    #     #                         id
    #     #                     FROM models
    #     #                     WHERE api_id = :api_id
    #     #                         AND kind = :kind
    #     #                     ORDER BY pinned DESC, name COLLATE NOCASE""",
    #     #                 query_params={
    #     #                     'api_id': lambda: find_ancestor_tree_item_id(self.parent),
    #     #                     # lambda: self.kind,
    #     #                 },
    #     #                 schema=[
    #     #                     {
    #     #                         'text': 'Name',
    #     #                         'key': 'name',
    #     #                         'type': str,
    #     #                         'stretch': True,
    #     #                     },
    #     #                     {
    #     #                         'text': 'id',
    #     #                         'key': 'id',
    #     #                         'type': int,
    #     #                         'visible': False,
    #     #                     },
    #     #                 ],
    #     #                 add_item_options={'title': 'Add Model', 'prompt': 'Enter a name for the model:'},
    #     #                 del_item_options={'title': 'Delete Model', 'prompt': 'Are you sure you want to delete this model?'},
    #     #                 layout_type='horizontal',
    #     #                 readonly=False,
    #     #                 config_widget=self.Image_Model_Params_Tabs(parent=self),
    #     #                 tree_header_hidden=True,
    #     #             )

    #     #             # # add sync button
    #     #             # btn_sync = IconButton(
    #     #             #     parent=self.tree_buttons,
    #     #             #     icon_path=':/resources/icon-refresh.png',
    #     #             #     tooltip='Sync models',
    #     #             #     size=22,
    #     #             # )
    #     #             # self.tree_buttons.add_button(btn_sync, 'btn_sync')

    #     #         def on_edited(self):
    #     #             # # bubble upwards towards root until we find `reload_models` method
    #     #             parent = self.parent
    #     #             while parent:
    #     #                 if hasattr(parent, 'on_edited'):
    #     #                     parent.on_edited()
    #     #                     return
    #     #                 parent = getattr(parent, 'parent', None)

    #     #         class Image_Model_Params_Tabs(ConfigTabs):
    #     #             def __init__(self, parent):
    #     #                 super().__init__(parent=parent, hide_tab_bar=True)

    #     #                 self.pages = {
    #     #                     'Parameters': self.Image_Config_Parameters_Widget(parent=self),
    #     #                     # 'Finetune': self.Chat_Config_Finetune_Widget(parent=self),
    #     #                 }

    #     #             class Image_Config_Parameters_Widget(ConfigFields):
    #     #                 def __init__(self, parent):
    #     #                     super().__init__(parent=parent)
    #     #                     self.parent = parent
    #     #                     self.schema = []

    #     #     class Tab_Image_Config(ConfigFields):
    #     #         def __init__(self, parent):
    #     #             super().__init__(parent=parent)
    #     #             self.label_width = 125
    #     #             self.schema = []

    #     # class Tab_Video(ConfigTabs):
    #     #     def __init__(self, parent):
    #     #         super().__init__(parent=parent)

    #     #         self.pages = {
    #     #             'Models': self.Tab_Video_Models(parent=self),
    #     #             'Config': self.Tab_Video_Config(parent=self),
    #     #         }

    #     #     class Tab_Video_Models(ConfigDBTree):
    #     #         def __init__(self, parent):
    #     #             super().__init__(
    #     #                 parent=parent,
    #     #                 table_name='models',
    #     #                 kind='VIDEO',
    #     #                 query="""
    #     #                     SELECT
    #     #                         name,
    #     #                         id
    #     #                     FROM models
    #     #                     WHERE api_id = :api_id
    #     #                         AND kind = :kind
    #     #                     ORDER BY pinned DESC, name COLLATE NOCASE""",
    #     #                 query_params={
    #     #                     'api_id': lambda: find_ancestor_tree_item_id(self.parent),
    #     #                     # lambda: self.kind,
    #     #                 },
    #     #                 schema=[
    #     #                     {
    #     #                         'text': 'Name',
    #     #                         'key': 'name',
    #     #                         'type': str,
    #     #                         'stretch': True,
    #     #                     },
    #     #                     {
    #     #                         'text': 'id',
    #     #                         'key': 'id',
    #     #                         'type': int,
    #     #                         'visible': False,
    #     #                     },
    #     #                 ],
    #     #                 add_item_options={'title': 'Add Model', 'prompt': 'Enter a name for the model:'},
    #     #                 del_item_options={'title': 'Delete Model', 'prompt': 'Are you sure you want to delete this model?'},
    #     #                 layout_type='horizontal',
    #     #                 readonly=False,
    #     #                 config_widget=self.Video_Model_Params_Tabs(parent=self),
    #     #                 tree_header_hidden=True,
    #     #             )

    #     #             # # add sync button
    #     #             # btn_sync = IconButton(
    #     #             #     parent=self.tree_buttons,
    #     #             #     icon_path=':/resources/icon-refresh.png',
    #     #             #     tooltip='Sync models',
    #     #             #     size=22,
    #     #             # )
    #     #             # self.tree_buttons.add_button(btn_sync, 'btn_sync')

    #     #         def on_edited(self):
    #     #             # # bubble upwards towards root until we find `reload_models` method
    #     #             parent = self.parent
    #     #             while parent:
    #     #                 if hasattr(parent, 'on_edited'):
    #     #                     parent.on_edited()
    #     #                     return
    #     #                 parent = getattr(parent, 'parent', None)

    #     #         class Video_Model_Params_Tabs(ConfigTabs):
    #     #             def __init__(self, parent):
    #     #                 super().__init__(parent=parent, hide_tab_bar=True)

    #     #                 self.pages = {
    #     #                     'Parameters': self.Video_Config_Parameters_Widget(parent=self),
    #     #                     # 'Finetune': self.Chat_Config_Finetune_Widget(parent=self),
    #     #                 }

    #     #             class Video_Config_Parameters_Widget(ConfigFields):
    #     #                 def __init__(self, parent):
    #     #                     super().__init__(parent=parent)
    #     #                     self.parent = parent
    #     #                     self.schema = []

    #     #     class Tab_Video_Config(ConfigFields):
    #     #         def __init__(self, parent):
    #     #             super().__init__(parent=parent)
    #     #             self.label_width = 125
    #     #             self.schema = []

    #     # class Tab_Voice(ConfigTabs):
    #     #     def __init__(self, parent):
    #     #         super().__init__(parent=parent)

    #     #         self.pages = {
    #     #             'Models': self.Tab_Voice_Models(parent=self),
    #     #             'Config': self.Tab_Voice_Config(parent=self),
    #     #         }

    #     #     class Tab_Voice_Models(ConfigDBTree):
    #     #         def __init__(self, parent):
    #     #             super().__init__(
    #     #                 parent=parent,
    #     #                 table_name='models',
    #     #                 kind='VOICE',
    #     #                 query="""
    #     #                     SELECT
    #     #                         name,
    #     #                         id
    #     #                     FROM models
    #     #                     WHERE api_id = :api_id
    #     #                         AND kind = :kind
    #     #                     ORDER BY pinned DESC, name COLLATE NOCASE""",
    #     #                 query_params={
    #     #                     'api_id': lambda: find_ancestor_tree_item_id(self.parent),
    #     #                     # lambda: self.kind,
    #     #                 },
    #     #                 schema=[
    #     #                     {
    #     #                         'text': 'Name',
    #     #                         'key': 'name',
    #     #                         'type': str,
    #     #                         'stretch': True,
    #     #                     },
    #     #                     {
    #     #                         'text': 'id',
    #     #                         'key': 'id',
    #     #                         'type': int,
    #     #                         'visible': False,
    #     #                     },
    #     #                 ],
    #     #                 add_item_options={'title': 'Add Model', 'prompt': 'Enter a name for the model:'},
    #     #                 del_item_options={'title': 'Delete Model', 'prompt': 'Are you sure you want to delete this model?'},
    #     #                 layout_type='horizontal',
    #     #                 readonly=False,
    #     #                 config_widget=self.Voice_Model_Params_Tabs(parent=self),
    #     #                 tree_header_hidden=True,
    #     #             )

    #     #             # # add sync button
    #     #             # btn_sync = IconButton(
    #     #             #     parent=self.tree_buttons,
    #     #             #     icon_path=':/resources/icon-refresh.png',
    #     #             #     tooltip='Sync models',
    #     #             #     size=22,
    #     #             # )
    #     #             # self.tree_buttons.add_button(btn_sync, 'btn_sync')

    #     #             # # add preview button
    #     #             # btn_preview = IconButton(
    #     #             #     parent=self.tree_buttons,
    #     #             #     icon_path=':/resources/icon-run.png',
    #     #             #     tooltip='Preview',
    #     #             #     size=22,
    #     #             # )
    #     #             # self.tree_buttons.add_button(btn_preview, 'btn_preview')
    #     #             # self.tree_buttons.btn_preview.clicked.connect(self.preview_voice)

    #     #         def on_edited(self):
    #     #             # # bubble upwards towards root until we find `reload_models` method
    #     #             parent = self.parent
    #     #             while parent:
    #     #                 if hasattr(parent, 'on_edited'):
    #     #                     parent.on_edited()
    #     #                     return
    #     #                 parent = getattr(parent, 'parent', None)

    #     #         def on_item_selected(self):
    #     #             super().on_item_selected()
    #     #             config = self.config_widget.config
    #     #             # has_preview = 'preview_url' in config
    #     #             # self.tree_buttons.btn_preview.setVisible(has_preview)

    #     #         def preview_voice(self):
    #     #             url = self.config_widget.config.get('preview_url')
    #     #             # play the audio file from the url
    #     #             if url:
    #     #                 play_url(url)
    #     #                 pass
    #     #             else:
    #     #                 display_message('No preview URL available', icon=QMessageBox.Warning)

    #     #         class Voice_Model_Params_Tabs(ConfigTabs):
    #     #             def __init__(self, parent):
    #     #                 super().__init__(parent=parent, hide_tab_bar=True)

    #     #                 self.pages = {
    #     #                     'Parameters': self.Voice_Config_Parameters_Widget(parent=self),
    #     #                     # 'Finetune': self.Chat_Config_Finetune_Widget(parent=self),
    #     #                 }

    #     #             class Voice_Config_Parameters_Widget(ConfigFields):
    #     #                 def __init__(self, parent):
    #     #                     super().__init__(parent=parent)
    #     #                     self.parent = parent
    #     #                     self.schema = []

    #     #     class Tab_Voice_Config(ConfigFields):
    #     #         def __init__(self, parent):
    #     #             super().__init__(parent=parent)
    #     #             self.label_width = 125
    #     #             self.schema = []