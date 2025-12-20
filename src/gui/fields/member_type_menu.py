"""
Member type menu field widget for member type selection.

This module provides a MemberTypeMenu field widget that extends IconButton to create
a button that opens a dropdown menu for member type selection. It provides a simple
interface for selecting different member types through a contextual menu.
"""

from functools import partial
from PySide6.QtWidgets import QMenu
from PySide6.QtGui import QAction, QFont

from gui import system
from gui.util import IconButton
from plugins.workflows.widgets.workflow_settings import WorkflowSettings
from utils.helpers import block_signals


class MemberTypeMenu(IconButton):  # todo dedupe
    def __init__(self, parent, **kwargs):
        super().__init__(
            parent=parent,
            icon_path=':/resources/icon-refresh.png',
            size=24,
        )
        self.is_member_header = getattr(parent, 'is_member_header', True)
        self.current_value = None
        
        self.menu = QMenu(self)
        
        self.clicked.connect(self.show_menu)

    def select_item(self, value):
        """Handle menu item selection"""
        self.current_value = value
        self.update_config()

    def get_value(self):
        """Get the currently selected value"""
        return self.current_value

    def set_value(self, value):
        self.current_value = value

    def set_member_type(self, value):
        current_name = self.parent.config.get('name', 'Agent')
        if self.current_value.replace('_', ' ').title() == current_name:
            with block_signals(self.parent):
                self.parent.name_wgt.set_value(value.replace('_', ' ').title())

        self.current_value = value
        # rebuild the member
        if self.parent.parent.parent.__class__.__name__ == 'MemberProxy':
            workflow_settings = self.parent.parent.parent.parent.workflow_settings
        else:
            is_workflow_header = not self.is_member_header
            if is_workflow_header:
                # _TYPE inserted here
                workflow_settings = self.parent.parent.parent
                if not workflow_settings.can_simplify_view():
                    return

                member_id_to_update = next((k for k, m in workflow_settings.members_in_view.items() if not m.member_config.get('_TYPE', 'agent') == 'user'), None)
                if not member_id_to_update:
                    return
                workflow_settings.members_in_view[member_id_to_update].member_config['_TYPE'] = value
            else:
                # _TYPE updated automatically
                workflow_settings = self.parent.parent.parent.parent

        self.update_config()
        workflow_settings.load()

    def add_contxt_menu_header(self, menu, title):  # todo dedupe
        section = QAction(title, self)
        section.setEnabled(False)
        font = QFont()
        font.setPointSize(8)
        section.setFont(font)
        menu.addAction(section)

    def update_config(self):
        """Implements same method as ConfigWidget, as a workaround to avoid inheriting from it"""
        if hasattr(self.parent, 'update_config'):
            self.parent.update_config()

        if hasattr(self, 'save_config'):
            self.save_config()

    def show_menu(self):
        """Show the dropdown menu"""
        # clear the menu
        self.menu.clear()

        # populate the menu
        member_modules = system.manager.modules.get_modules_in_folder(
            module_type='Members',
            fetch_keys=('name', 'kind_folder', 'class',)
        )

        value_kind = next((kind_folder for name, kind_folder, module_class in member_modules if name == self.current_value), None)

        type_dict = {}
        for module_name, kind_folder, module_class in member_modules:
            if kind_folder not in type_dict:
                type_dict[kind_folder] = []
            type_dict[kind_folder].append((module_name, module_class))

        for module_kind, kind_modules in type_dict.items():
            if not module_kind:
                continue
            if value_kind:
                if value_kind != module_kind:
                    continue
            else:
                self.add_contxt_menu_header(self.menu, module_kind.capitalize())

            for module_name, module_class in kind_modules:
                if value_kind and module_name == self.current_value:
                    continue
                default_name = getattr(module_class, 'default_name', module_name.capitalize())
                workflow_insert_mode = getattr(module_class, 'workflow_insert_mode', None)
                # if workflow_insert_mode == 'single':
                self.menu.addAction(module_name.capitalize(), partial(
                    self.set_member_type,
                    module_name
                ))
                # elif workflow_insert_mode == 'list':
                #     self.menu.addAction(module_name.capitalize(), partial(self.choose_member, 'AGENT'))
                # else:
                #     continue

        # set_kind = next((kind_folder for name, kind_folder in module_type_modules if name == value), None)

        # for module_name, module_class, baked, kind_folder in module_type_modules:

        button_rect = self.rect()
        menu_pos = self.mapToGlobal(button_rect.bottomLeft())
        self.menu.exec(menu_pos)