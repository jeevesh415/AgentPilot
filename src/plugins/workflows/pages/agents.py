from gui.widgets.config_db_tree import ConfigDBTree
from plugins.workflows.widgets.chat_widget import ChattableWorkflowWidget


class Page_Entities(ConfigDBTree):
    display_name = 'Agents'
    icon_path = ":/resources/icon-agent.png"
    page_type = 'main'  # either 'settings', 'main', or 'any' ('any' means it can be pinned between main and settings)

    def __init__(self, parent):
        super().__init__(
            parent=parent,
            manager='agents',  # todo name
            query="""
                SELECT
                    name,
                    id,
                    config,
                    uuid,
                    folder_id
                FROM entities
                WHERE kind = :kind
                ORDER BY pinned DESC, ordr, name COLLATE NOCASE""",
            schema=[
                {
                    'text': 'Name',
                    'key': 'name',
                    'type': str,
                    'stretch': True,
                    'image_key': 'config',
                },
                {
                    'text': 'id',
                    'key': 'id',
                    'type': int,
                    'visible': False,
                },
                {
                    'text': 'config',
                    'type': str,
                    'visible': False,
                },
                {
                    'text': 'uuid',
                    'key': 'uuid',
                    'type': str,
                    'visible': False,
                },
            ],
            layout_type='horizontal',
            config_widget=self.Entity_Config_Widget(parent=self),
            folder_config_widget=self.Folder_Config_Widget(parent=self),
            tree_header_hidden=True,
            readonly=True,
            searchable=True,
            filterable=True,
            has_chat=True,
            kind='AGENT',
            kind_list=['AGENT', 'CONTACT'],
            folder_key={'AGENT': 'agents', 'CONTACT': 'contacts'},
        )
        self.splitter.setSizes([400, 1000])

    class Entity_Config_Widget(ChattableWorkflowWidget):
        def __init__(self, parent):
            super().__init__(
                parent=parent,
                kind='AGENT',
            )
