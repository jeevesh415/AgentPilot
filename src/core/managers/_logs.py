
from utils.helpers import BaseManager


class LogsManager(BaseManager):
    def __init__(self, system):
        super().__init__(
            system,
            table_name='logs',
            folder_key='logs',
            load_columns=['name', 'config'],
        )
