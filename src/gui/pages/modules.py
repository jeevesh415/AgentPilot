"""
Modules Page Module.

This module provides the modules management page for the Agent Pilot GUI interface.
The page enables users to manage, install, and configure the various module types
that extend Agent Pilot's functionality, including custom pages, widgets, providers,
and other extensible components.

Key Features:
- Module installation and uninstallation
- Module type management (managers, pages, widgets, etc.)
- Runtime module loading and configuration
- Module dependency tracking
- Custom module development support
- Module status monitoring and updates
- Integration with the dynamic module system

The page provides comprehensive module lifecycle management, enabling users to
extend Agent Pilot's capabilities through custom and third-party modules.
"""

from PySide6.QtGui import Qt
from PySide6.QtWidgets import QLabel, QWidget, QSizePolicy, QMessageBox

from gui import system
from gui.widgets.config_widget import ConfigWidget
from gui.widgets.config_db_tree import ConfigDBTree
from gui.widgets.config_fields import ConfigFields
from gui.widgets.config_joined import ConfigJoined
from gui.util import IconButton, find_main_widget, CHBoxLayout, CVBoxLayout
from utils import sql
from utils.helpers import display_message, set_module_type


@set_module_type(module_type='Pages')
class Page_Module_Settings(ConfigDBTree):
    display_name = 'Modules'
    icon_path = ":/resources/icon-jigsaw.png"
    page_type = 'main'  # either 'settings', 'main', or 'any' ('any' means it can be pinned between main and settings)

    def __init__(self, parent):
        super().__init__(
            parent=parent,
            table_name='modules',
            manager='modules',
            query="""
                SELECT
                    name,
                    id,
                    baked,
                    -- COALESCE(json_extract(config, '$.enabled'), 1),
                    folder_id
                FROM modules
                ORDER BY pinned DESC, ordr, name COLLATE NOCASE""",
            schema=[
                {
                    'text': 'Modules',
                    'key': 'name',
                    'type': str,
                    'stretch': True,
                },
                {
                    'key': 'id',
                    'type': int,
                    'visible': False,
                },
                {
                    'key': 'baked',
                    'type': int,
                    'visible': False,
                },
            ],
            # extra_data=lambda: self.extra_data(),
            add_item_options={'title': 'Add module', 'prompt': 'Enter a name for the module:'},
            del_item_options={'title': 'Delete module', 'prompt': 'Are you sure you want to delete this module?'},
            folder_key='modules',
            readonly=False,
            layout_type='horizontal',
            tree_header_hidden=True,
            config_widget=Module_Config_Widget(parent=self),
            folder_config_widget=self.Folder_Config_Widget(parent=self),
            searchable=True,
            default_item_icon=':/resources/icon-jigsaw-solid.png',
        )
        self.splitter.setSizes([400, 1000])
    
    def get_module_file_path(self, item_id, module_name=None):  # folder_name, module_name, module_config):
        is_baked = sql.get_scalar('SELECT baked FROM modules WHERE id = ?', (item_id,)) == 1
        if not is_baked:
            return None

        # Get module data from database
        module_config = sql.get_scalar('SELECT config FROM modules WHERE id = ?', (item_id,), load_json=True)
        folder_id = sql.get_scalar('SELECT folder_id FROM modules WHERE id = ?', (item_id,))
        if module_name is None:
            module_name = sql.get_scalar('SELECT name FROM modules WHERE id = ?', (item_id,))
        
        if not module_config or not module_name:
            print(f"Module data not found for id {item_id}")
            return
            
        # Get folder name (module type) from folder_id
        folder_name = None
        if folder_id:
            folder_name = sql.get_scalar('SELECT name FROM folders WHERE id = ?', (folder_id,))

        if not folder_name:
            print(f"Folder not found for module {module_name}")
            return
            
        # Get source code from config
        source_code = module_config.get('data', '')
        if not source_code:
            print(f"No source code found in module {module_name}")
            return

        type_controller = self.manager.type_controllers.get(folder_name.lower())
        base_path = getattr(type_controller, 'load_to_path', None)
        if not base_path:
            display_message(
                message=f"Unknown module type: {folder_name}",
                icon=QMessageBox.Warning,
            )
            return
        
        # Join the description and source code
        description = module_config.get('description', '')
        if description != '':
            source_code = f'"""\n{description}\n"""\n\n{source_code}'
            
        # Construct file path
        from pathlib import Path
        
        base_path = f"src/{base_path.replace('.', '/')}"
        file_path = Path(base_path) / f"{module_name.lower()}.py"

        return file_path
    
    def unbake_item(self):
        item_id = self.get_selected_item_id()
        if not item_id:
            return
        sql.execute('UPDATE modules SET baked = 0 WHERE id = ?', (item_id,))
        self.load()

    def bake_item(self, force=False):
        item_id = self.get_selected_item_id()
        if not item_id:
            return

        # # Get module data from database
        module_name = sql.get_scalar('SELECT name FROM modules WHERE id = ?', (item_id,))
        module_config = sql.get_scalar('SELECT config FROM modules WHERE id = ?', (item_id,), load_json=True)
        
        source_code = module_config.get('data', '')
        file_path = self.get_module_file_path(item_id)
        
        # Check if file exists and ask for confirmation if not forcing
        if file_path.exists():
            if not force:
                retval = QMessageBox.question(
                    self,
                    "File Exists",
                    f"The file {file_path} already exists. Do you want to overwrite it?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if retval != QMessageBox.Yes:
                    return
        
        try:
            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write source code to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(source_code)
            
            # Update the module to mark it as baked
            sql.execute('UPDATE modules SET baked = 1 WHERE id = ?', (item_id,))
            
            if not force:
                display_message(
                    message=f"Successfully baked module {module_name} to {file_path}",
                    icon=QMessageBox.Information,
                )
            
        except Exception as e:
            display_message(
                message=f"Error baking module {module_name}: {e}",
                icon=QMessageBox.Critical,
            )
    
    def on_item_selected(self):
        super().on_item_selected()

        item_id = self.get_selected_item_id()
        if not item_id:
            return
        
        folder_id = sql.get_scalar('SELECT folder_id FROM modules WHERE id = ?', (item_id,))
        if not folder_id:
            return
        folder_name = sql.get_scalar('SELECT name FROM folders WHERE id = ?', (folder_id,))
        if not folder_name:
            return
        controller = self.manager.type_controllers.get(folder_name.lower())
        if not controller:
            return
        
    # def extra_data(self):
    #     from gui import system
    #     extra_data = []
    #     module_types = {name: controller for name, controller in system.manager.modules.type_controllers.items() if name is not None}
    #     for module_type in module_types:
    #         type_folder_id = get_module_type_folder_id(module_type)
    #         module_type_modules = system.manager.modules.get_modules_in_folder(
    #             module_type=module_type,
    #             fetch_keys=('name', 'class',)
    #         )
    #         for module_name, module_class in module_type_modules:
    #             # if module_class is None:
    #             #     print(f"Module class for {module_name} in {module_type} is None, skipping.")
    #             #     continue
    #             extra_data.append((module_name, module_name, 1, type_folder_id))

    #     return extra_data

    # # def extra_data(self):
    # #     from gui import system
    # #     extra_data = []
    # #     module_types = {name: controller for name, controller in system.manager.modules.type_controllers.items() if name is not None}
    # #     for module_type in module_types:
    # #         type_folder_id = get_module_type_folder_id(module_type)
    # #         module_type_modules = system.manager.modules.get_modules_in_folder(
    # #             module_type=module_type,
    # #             fetch_keys=('name', 'class',)
    # #         )
    # #         for module_name, module_class in module_type_modules:
    # #             # if module_class is None:
    # #             #     print(f"Module class for {module_name} in {module_type} is None, skipping.")
    # #             #     continue
    # #             extra_data.append((module_name, module_name, 1, type_folder_id))

    # #     return extra_data
    # #             add_module(
    # #                 module_class=module_class,
    # #                 module_name=module_name,
    # #                 folder_name=module_type,
    # #             )
    # #     from gui import system
    # #     import inspect

    # #     # Get the module name and folder (type) from the DB
    # #     module_name = sql.get_scalar('SELECT name FROM modules WHERE id = ?', (item_id,))
    # #     folder_id = sql.get_scalar('SELECT folder_id FROM modules WHERE id = ?', (item_id,))
    # #     if not module_name or not folder_id:
    # #         return None
    # #     folder_name = sql.get_scalar('SELECT name FROM folders WHERE id = ?', (folder_id,))
    # #     if not folder_name:
    # #         return None

    # #     # Try to get the class from source
    # #     module_class = system.manager.modules.get_module_class(folder_name, module_name)
    # #     if not module_class:
    # #         return None

    # #     try:
    # #         module_file_path = inspect.getfile(module_class)
    # #         with open(module_file_path, 'r', encoding='utf-8') as file:
    # #             module_source = file.read()
    # #         return {
    # #             'data': module_source,
    # #             'file_path': module_file_path,
    # #             'module_class': module_class.__name__,
    # #             'module_type': folder_name,
    # #         }
    # #     except Exception as e:
    # #         print(f"Error getting inferred data for module {module_name}: {e}")
    # #         return None

class Module_Config_Widget(ConfigJoined):
    def __init__(self, parent):
        super().__init__(parent=parent)
        self.widgets = [
            self.Module_Config_Fields(parent=self),
        ]

    class Module_Config_Fields(ConfigFields):
        def __init__(self, parent):
            super().__init__(parent=parent)
            # self.IS_DEV_MODE = True
            self.main = find_main_widget(self)
            self.status = 'unloaded'  # 'loaded', 'unloaded', 'modified', 'error', 'externally modified'
            self.schema = [
                {
                    'text': 'Avatar',
                    'key': 'icon_path',
                    'type': 'image',
                    'diameter': 30,
                    'circular': False,
                    'border': False,
                    'default': ':/resources/icon-jigsaw-solid.png',
                    'label_position': None,
                    'row_key': 0,
                },
                {
                    'text': 'Name',
                    'type': str,
                    'default': 'Unnamed module',
                    'stretch_x': True,
                    'text_size': 14,
                    # 'text_alignment': Qt.AlignCenter,
                    'label_position': None,
                    'transparent': True,
                    'row_key': 0,
                },
                {
                    'text': '',
                    'key': 'toggle_description',
                    'type': 'button_toggle',
                    # 'checkable': True,
                    'default': False,
                    'icon_path': ':/resources/icon-description.png',
                    'tooltip': 'Toggle description',
                    'label_position': None,
                    'row_key': 0,
                },
                {
                    'text': 'Description',
                    'type': str,
                    'default': '',
                    'num_lines': 10,
                    'stretch_x': True,
                    'stretch_y': True,
                    'transparent': True,
                    'visibility_predicate': lambda fields: fields.config.get('toggle_description', False),
                    'placeholder_text': 'Description',
                    'gen_block_folder_name': 'todo',
                    'wrap_text': True,
                    'monospaced': True,
                    'label_position': None,
                },
                {
                    'text': 'Load on startup',
                    'type': bool,
                    'default': True,
                    'row_key': 1,
                },
                {
                    'text': 'Load && run',
                    'key': 'load_button',
                    'type': 'button',
                    'tooltip': 'Re-import the module and execute it',
                    'target': self.reimport,
                    'label_position': None,
                    'row_key': 1,
                },
                {
                    'text': 'Unload',
                    'key': 'unload_button',
                    'type': 'button',
                    'tooltip': 'Unload the module',
                    'target': self.unload,
                    'label_position': None,
                    'row_key': 1,
                },
                {
                    'text': 'Data',
                    'type': str,
                    'default': '',
                    'num_lines': 2,
                    'stretch_x': True,
                    'stretch_y': True,
                    'highlighter': 'python',
                    'fold_mode': 'python',
                    'monospaced': True,
                    'gen_block_folder_name': 'page_module',
                    'label_position': None,
                },
            ]

        def after_init(self):
            self.lbl_status = QLabel(self)
            self.lbl_status.setProperty("class", 'dynamic_color')
            self.lbl_status.setMaximumWidth(250)
            self.lbl_status.move(40, 30)
        
        def update_config(self):
            module_id = self.get_item_id()
            module_metadata = sql.get_scalar('SELECT metadata FROM modules WHERE id = ?', (module_id,), load_json=True)
            module_hash = module_metadata.get('hash')

            super().update_config()
        
        def get_item_id(self):
            return self.parent.parent.get_selected_item_id()
        
        def load(self):
            super().load()

            module_id = self.get_item_id()
            # module_metadata = system.manager.modules.get_cell(module_id, 'metadata')
            module_metadata = sql.get_scalar('SELECT metadata FROM modules WHERE id = ?', (module_id,), load_json=True)
            if not module_metadata:
                self.set_status('Unloaded')
                return

            module_hash = module_metadata.get('hash')
            is_baked = sql.get_scalar('SELECT baked FROM modules WHERE id = ?', (module_id,)) == 1
            is_loaded = False  # module_id in system.manager.modules.loaded_module_hashes
            if is_baked:
                baked_hash = sql.get_scalar('SELECT uuid FROM modules WHERE id = ?', (module_id,))

                self.set_status('Baked')
                
            elif is_loaded:
                loaded_hash = system.manager.modules.loaded_module_hashes[module_id]
                is_modified = module_hash != loaded_hash
                if is_modified:
                    self.set_status('Modified')
                else:
                    self.set_status('Loaded')
            else:
                self.set_status('Unloaded')

        def set_status(self, status, text=None):
            if text is None:
                text = status
            status_color_classes = {
                'Loaded': '#6aab73',
                'Unloaded': '#B94343',
                'Baked': '#438BB9',
                'Modified': '#438BB9',
                'Error': '#B94343',
                'Externally Modified': '#B94343',
            }
            can_reimport = status in ['Modified', 'Unloaded']
            self.load_button.setVisible(can_reimport)
            self.unload_button.setVisible(status == 'Loaded')
            self.lbl_status.setText(text)
            self.lbl_status.setStyleSheet(f"color: {status_color_classes[status]};")

        def reimport(self):
            module_id = self.get_item_id()
            if not module_id:
                return

            module = system.manager.modules.load_module(module_id)
            if isinstance(module, Exception):
                self.set_status('Error', f"Error: {str(module)}")
            else:
                self.set_status('Loaded')
                if system.manager.modules.get_cell(module_id, 'type') == 'pages':
                    main = find_main_widget(self)
                    main.main_pages.build_schema()
                    # main.page_settings.build_schema()

        def unload(self):
            module_id = self.get_item_id()
            if not module_id:
                return

            system.manager.modules.unload_module(module_id)
            self.set_status('Unloaded')
            if system.manager.modules.get_cell(module_id, 'type') == 'pages':
                main = find_main_widget(self)
                main.main_pages.build_schema()
                # main.page_settings.build_schema()


class PageEditor(ConfigWidget):
    def __init__(self, main, module_id):
        super().__init__(parent=main)

        self.main = main
        self.module_id = module_id
        self.layout = CVBoxLayout(self)  # contains a titlebar (title, close button) and a module config widget
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setFixedWidth(500)

        # create title bar with title and close button
        self.titlebar = QWidget(parent=self)
        self.titlebar_layout = CHBoxLayout(self.titlebar)
        self.titlebar_layout.setContentsMargins(4, 4, 4, 4)
        self.lbl_title = QLabel(parent=self.titlebar)
        self.lbl_title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        font = self.lbl_title.font()
        font.setBold(True)
        self.lbl_title.setFont(font)
        self.titlebar_layout.addWidget(self.lbl_title)
        self.btn_close = IconButton(parent=self.titlebar, icon_path=':/resources/close.png', size=22)
        self.btn_close.clicked.connect(self.close)
        self.titlebar_layout.addWidget(self.btn_close)

        self.layout.addWidget(self.titlebar)

        self.config_widget = self.PageEditorWidget(parent=self, module_id=module_id)
        self.config_widget.build_schema()
        self.layout.addWidget(self.config_widget)

        self.setFixedHeight(self.main.height())

        module_manager = system.manager.modules
        page_name = module_manager.module_names.get(module_id, None)
        if not page_name:
            return
        self.lbl_title.setText(f'Editing module > {page_name}')

    def close(self):
        self.hide()

    def showEvent(self, event):
        # SHOW THE POPUP TO THE LEFT HAND SIDE OF THE MAIN WINDOW, MINUS 350
        top_left = self.main.rect().topLeft()
        top_left_global = self.main.mapToGlobal(top_left)
        top_left_global.setX(top_left_global.x() - self.width())
        self.move(top_left_global)
        super().showEvent(event)

    def load(self):
        self.config_widget.load()

    class PageEditorWidget(Module_Config_Widget):
        def __init__(self, parent, module_id):
            super().__init__(parent=parent)
            self.module_id = module_id
            self.data_source = {
                'table_name': 'modules',
                'item_id': module_id,
            }
            self.code_ast = None

        # def load(self):
        #     item_id = self.module_id
        #     table_name = self.data_target['table_name']
        #     json_config = json.loads(sql.get_scalar(f"""
        #         SELECT
        #             `config`
        #         FROM `{table_name}`
        #         WHERE id = ?
        #     """, (item_id,)))
        #     if ((table_name == 'entities' or table_name == 'blocks' or table_name == 'tools')
        #             and json_config.get('_TYPE', 'agent') != 'workflow'):
        #         json_config = merge_config_into_workflow_config(json_config)
        #     self.load_config(json_config)
        #     super().load()
        #
        # def update_config(self):
        #     config = self.get_config()
        #
        #     save_table_config(
        #         ref_widget=self,
        #         table_name='modules',
        #         item_id=self.module_id,
        #         value=json.dumps(config),
        #     )
        #
        #     main = find_main_widget(self)
        #     main.system.modules.load(import_modules=False)
        #     self.widgets[0].load()