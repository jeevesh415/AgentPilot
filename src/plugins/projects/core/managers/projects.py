
from utils.helpers import BaseManager


class ProjectManager(BaseManager):
    def __init__(self, system):
        super().__init__(
            system,
            table_name='projects',
            folder_key='projects',
            load_columns=['name', 'config'],
            add_item_options={'title': 'New Project', 'prompt': 'Enter a name for the project:'},
            del_item_options={'title': 'Delete Project',
                              'prompt': 'Are you sure you want to delete this project?'},
        )

    