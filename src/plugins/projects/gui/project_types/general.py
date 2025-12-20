
from gui.util import find_ancestor_tree_item_id
from gui.widgets.config_db_tree import ConfigDBTree
from gui.widgets.config_fields import ConfigFields
from gui.widgets.config_joined import ConfigJoined
from gui.widgets.config_tabs import ConfigTabs
from gui.widgets.file_tree import FileTree
from plugins.workflows.widgets.chat_widget import ChattableWorkflowWidget


class GeneralProject(ConfigJoined):
    def __init__(self, parent):
        super().__init__(
            parent=parent,
            resizable=True,
            widgets=[
                self.Project_Config(parent=self),
                self.Project_Tasks_Tree(parent=self),
            ]
        )

    class Project_Config(ConfigJoined):
        def __init__(self, parent):
            super().__init__(
                parent=parent,
                widgets=[
                    self.Project_Fields(parent=self),
                    self.Project_Config_Tabs(parent=self),
                ]
            )
    
        class Project_Fields(ConfigFields):
            def __init__(self, parent):
                super().__init__(
                    parent=parent,
                    schema=[
                        {
                            'text': 'Path',
                            'key': 'working_dir',
                            'type': 'path_picker',
                            'row_key': 0,
                        },
                        {
                            'key': '_TYPE',
                            'text': 'Project type',
                            'type': 'project_type_menu',
                            'label_position': None,
                            # 'visibility_predicate': self.member_type_visibility_predicate,
                            'default': '',
                            'row_key': 0,
                        },
                    ]
                )
                self.setFixedHeight(35)
            
            def load_config(self, json_config=None):
                super().load_config(json_config)
                pass
        
        class Project_Config_Tabs(ConfigTabs):
            def __init__(self, parent):
                super().__init__(
                    parent=parent,
                    pages={
                        'Files': self.Project_Config_Files(parent=self),
                        # 'Tasks': self.Project_Config_Files(parent=self),
                        'Concepts': self.Project_Concepts_Tree(parent=self),
                    }
                )
                self.propagate_config=False
            
            class Project_Concepts_Tree(ConfigDBTree):
                def __init__(self, parent):
                    super().__init__(
                        parent=parent,
                        table_name='project_concepts',
                        query_params={
                            'project_id': lambda: find_ancestor_tree_item_id(self.parent),
                        },
                        query="""
                            SELECT
                                name,
                                id,
                                config,
                                folder_id
                            FROM project_concepts
                            WHERE project_id = :project_id
                            ORDER BY name COLLATE NOCASE""",
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
                        ],
                        layout_type='horizontal',
                        config_widget=self.Project_Concepts_Config_Widget(parent=self),
                        # folder_config_widget=self.Folder_Config_Widget(parent=self),
                        tree_header_hidden=True,
                        readonly=True,
                        searchable=True,
                        # filterable=True,
                    )

                # show 
                class Project_Concepts_Config_Widget(ConfigJoined):
                    def __init__(self, parent):
                        super().__init__(
                            parent=parent,
                            widgets=[
                                # self.Project_Concepts_Config_Fields(parent=self),
                            ]
                        )

            class Project_Config_Files(FileTree):
                def __init__(self, parent):
                    super().__init__(
                        parent=parent, 
                        files_in_tree=True,
                        root_directory='/home/jb/CursorProjects/AgentPilot',
                        show_bookmarks=False,
                    )

                def load_config(self, json_config=None):
                    config = self.parent.parent.get_config()
                    path = config.get('working_dir', '')
                    self.set_root_directory(path)

    class Project_Tasks_Tree(ConfigDBTree):
        def __init__(self, parent):
            super().__init__(
                parent=parent,
                table_name='contexts',
                layout_type='horizontal',
                query="""
                    SELECT
                        name,
                        id,
                        folder_id
                    FROM contexts
                    WHERE kind = 'PROJECT'
                """,
                kind='PROJECT',
                folder_key=lambda: f'project:{find_ancestor_tree_item_id(parent)}:task',
                schema=[
                    {
                        'text': 'Tasks',
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
                config_widget=self.Project_Chat_Widget(parent=self),
            )
            
        class Project_Chat_Widget(ChattableWorkflowWidget):
            def __init__(self, parent):
                super().__init__(
                    parent=parent,
                    kind='PROJECT',
                    workflow_editable=False,
                )
