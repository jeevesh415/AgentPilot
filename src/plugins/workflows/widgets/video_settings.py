from gui.widgets.config_pages import ConfigPages
from gui.widgets.config_fields import ConfigFields
from plugins.workflows.widgets.video_model_settings import VideoModelSettings
from utils.helpers import set_module_type


@set_module_type(module_type='Widgets')
class VideoSettings(ConfigPages):
    def __init__(self, parent):
        super().__init__(parent=parent)
        self.pages = {
            'Model': VideoModelSettings(parent=self),
            'Browse': self.BrowseSettings(parent=self),
            'URL': self.UrlSettings(parent=self),
        }
        self.content.currentChanged.disconnect()  # todo clean
        self.content.currentChanged.connect(self.on_current_changed)

    def get_config(self):
        config = super().get_config()
        selected_page_key = list(self.pages.keys())[self.content.currentIndex()]
        config['mode'] = selected_page_key
        return config
    
    def load(self):
        super().load()
        selected_page_key = self.config.get('mode', 'Model')
        self.goto_page(selected_page_key)

    def on_current_changed(self, _):
        selected_page_key = list(self.pages.keys())[self.content.currentIndex()]
        self.config['mode'] = selected_page_key
        super().on_current_changed(_)
    
    class BrowseSettings(ConfigFields):
        def __init__(self, parent):
            super().__init__(
                parent=parent,
                conf_namespace='browse'
            )
            self.schema = [
                {
                    'text': 'Path',
                    'key': 'path',
                    'type': 'path_picker',
                    'label_position': None,
                    'stretch_x': True,
                },
            ]
    
    class UrlSettings(ConfigFields):
        def __init__(self, parent):
            super().__init__(
                parent=parent,
                conf_namespace='from_url'
            )
            self.schema = [
                {
                    'text': 'URL',
                    'type': str,
                    'placeholder_text': 'Enter URL...',
                    'label_position': None,
                    'stretch_x': True,
                    'default': '',
                },
            ]