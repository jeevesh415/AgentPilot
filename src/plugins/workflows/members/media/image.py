
from plugins.workflows.members import Member
from utils.helpers import set_module_type


@set_module_type(module_type='Members', settings='image_settings')
class Image(Member):
    default_role = 'image'
    default_avatar = ':/resources/icon-image.png'
    default_name = 'Image'
    workflow_insert_mode = 'single'
    OUTPUT = 'IMAGE'

    @property
    def INPUTS(self):
        return {
            'CONFIG': {
                'text': str,
            },
        }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def receive(self):
        """The entry response method for the member."""
        yield self.default_role, 'TODO'
