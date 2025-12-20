from gui.widgets.config_pages import ConfigPages
from gui.widgets.config_fields import ConfigFields
from plugins.workflows.widgets.image_model_settings import ImageModelSettings
from utils.helpers import set_module_type


@set_module_type(module_type='Widgets')
class ImageSettings(ConfigPages):
    def __init__(self, parent):
        super().__init__(parent=parent)
        self.pages = {
            'Model': ImageModelSettings(parent=self),
            'Browse': self.BrowseSettings(parent=self),
            'URL': self.UrlSettings(parent=self),
        }

    def get_config(self):
        config = super().get_config()
        selected_page_key = list(self.pages.keys())[self.content.currentIndex()]
        config['mode'] = selected_page_key
        return config
    
    def load(self):
        super().load()
        selected_page_key = self.config.get('mode', 'Model')
        self.goto_page(selected_page_key)
    
    class BrowseSettings(ConfigFields):
        def __init__(self, parent):
            super().__init__(
                parent=parent,
                conf_namespace='browse'
            )
            self.schema = [
                {
                    'text': 'Browse',
                    'type': 'button',
                    'icon_path': ':/resources/icon-folder.png',
                    'default': 'Browse',
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
                    'default': '',
                },
            ]