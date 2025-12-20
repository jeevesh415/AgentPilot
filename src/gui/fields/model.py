"""
Model selection field widget for configurable AI model choices.

This module provides a ModelComboBox field widget that extends BaseCombo to create
a sophisticated dropdown for selecting AI models from various providers. It includes
an integrated options button for model parameter configuration, supports model
filtering by kind (chat, completion, etc.), and provides a popup interface for
advanced model settings. The widget automatically organizes models by provider
and handles model configuration persistence.
"""  # unchecked

import json

from PySide6.QtGui import QPainter, QStandardItemModel, QStandardItem, Qt, QColor
from PySide6.QtWidgets import QStyleOptionComboBox, QStylePainter, QStyle

from gui import system
from gui.fields.combo import BaseCombo
from gui.util import IconButton, CHBoxLayout
from utils import sql
from utils.helpers import convert_model_json_to_obj, block_signals


class ModelComboBox(BaseCombo):
    """
    BE CAREFUL SETTING BREAKPOINTS DUE TO PYSIDE COMBOBOX BUG
    """
    def __init__(self, parent, **kwargs):
        self.parent = parent
        self.first_item = kwargs.pop('first_item', None)
        self.model_kind = kwargs.pop('model_kind', 'ALL')
        super().__init__(parent, **kwargs)

        self.options_btn = self.OptionsButton(
            parent=self,
            icon_path=':/resources/icon-settings-solid.png',
            tooltip='Options',
            size=20,
        )
        self.options_btn.setFixedSize(20, 20)
        from gui.popup import PopupModel

        self.config_widget = PopupModel(self)
        self.layout = CHBoxLayout(self)
        self.layout.addWidget(self.options_btn)
        self.options_btn.move(-20, 0)
        self.currentIndexChanged.connect(parent.update_config)

        self.load()

    def load(self):
        #
        # matched_provider_ids = sql.get_results(f"""
        #     SELECT DISTINCT a.id
        #     FROM apis a
        #     JOIN models m
        #         ON a.id = m.api_id
        #     WHERE m.kind = ? OR ? = 'ALL'
        #     ORDER BY a.pinned DESC, a.name
        # """, (self.model_kind, self.model_kind), return_type='list')  # todo clean
        with block_signals(self):
            self.clear()

            model = QStandardItemModel()
            self.setModel(model)

            # api_models = {}

            models = sql.get_results("""
                SELECT
                    m.name,
                    m.kind,
                    a.name AS api_name,
                    m.provider_plugin,
                    m.config,
                    a.api_key
                FROM models m
                LEFT JOIN apis a
                    ON m.api_id = a.id
                ORDER BY m.api_id, m.name""")
            
            last_api_name = None
            for display_name, model_kind, api_name, provider_plugin, model_config, api_key in models:
                if self.model_kind not in ('ALL', model_kind):
                    continue

                if self.model_kind == 'CHAT' and api_key == '':
                    continue

                if api_name != last_api_name:
                    header_item = QStandardItem(api_name)
                    header_item.setData('header', Qt.UserRole)
                    header_item.setEnabled(False)
                    font = header_item.font()
                    font.setBold(True)
                    header_item.setFont(font)
                    model.appendRow(header_item)
                    last_api_name = api_name

                data = json.loads(model_config)
                data.update({
                    'kind': model_kind,
                    'provider': provider_plugin,
                })
                    # 'model_name': model_name,  #  or '',  # todo
                    # 'model_params': model_config,  purposefully exclude params
                item = QStandardItem(display_name)
                item.setData(json.dumps(data), Qt.UserRole)
                model.appendRow(item)

            # # for provider_name, provider in system.manager.providers.items():
            # #     # api_id =
            # #     # if provider.api_ids not in matched_provider_ids:
            # #     #     continue
            # #     for (kind, model_name), api_id in provider.model_api_ids.items():
            # #         if not model_name:  # todo
            # #             continue
            # #         if self.model_kind not in ('ALL', kind):
            # #             continue
            # #         api_name = provider.api_ids[api_id]
            # #         model_config = provider.models.get((kind, model_name))
            # #         alias = provider.model_aliases.get((kind, model_name), model_name)
            # #         api_key = model_config.get('api_key', '')
            # #         if api_key == '':
            # #             continue
            # #         if api_name not in api_models:
            # #             api_models[api_name] = []
            # #         api_models[api_name].append((kind, model_name, provider_name, alias))

            # for api_name, models in api_models.items():
            #     if api_name.lower() == 'openai':
            #         pass
            #     header_item = QStandardItem(api_name)
            #     header_item.setData('header', Qt.UserRole)
            #     header_item.setEnabled(False)
            #     font = header_item.font()
            #     font.setBold(True)
            #     header_item.setFont(font)
            #     model.appendRow(header_item)

            #     for kind, model_name, provider_name, alias in models:
            #         data = {
            #             'kind': kind,
            #             'model_name': model_name or '',  # todo
            #             # 'model_params': model_config,  purposefully exclude params
            #             'provider': provider_name,
            #         }
            #         item = QStandardItem(alias)
            #         item.setData(json.dumps(data), Qt.UserRole)
            #         model.appendRow(item)

            # # if len(model.rowCount()) == 0:
            # #     item = QStandardItem('No models found')

    def update_config(self):
        """Implements same method as ConfigWidget, as a workaround to avoid inheriting from it"""
        if hasattr(self.parent, 'update_config'):
            self.parent.update_config()

        if hasattr(self, 'save_config'):
            self.save_config()

        self.refresh_options_button_visibility()

    def refresh_options_button_visibility(self):
        has_config = len(self.config_widget.get_config()) > 0
        has_items = self.model().rowCount() > 0
        self.options_btn.setVisible(has_config and has_items)

    def get_value(self):
        """
        DO NOT PUT A BREAKPOINT IN HERE BECAUSE IT WILL FREEZE YOUR PC (LINUX, PYCHARM & VSCODE) ISSUE WITH PYSIDE COMBOBOX
        """
        # from utils.helpers import convert_model_json_to_obj
        model_json = self.currentData()
        model_obj = convert_model_json_to_obj(model_json)
        # cnf = self.config_widget.get_config()
        # pretty_printed_cnf = json.dumps(cnf, indent=4, ensure_ascii=False)
        # print(f'Config for model {model_obj["model_name"]}:\n{pretty_printed_cnf}')
        model_obj['model_params'] = self.config_widget.get_config()  #!88!#
        return model_obj

    def set_value(self, value):
        if value == '':
            value = system.manager.config.get('system.default_chat_model', 'mistral/mistral-large-latest')
        value = convert_model_json_to_obj(value)

        value_copy = value.copy()
        model_params = value_copy.pop('model_params', {})

        self.config_widget.load_config(model_params)
        self.config_widget.load()

        value_copy = json.dumps(value_copy)
        # widget.set_key(value_copy)
        super().set_value(value_copy)
        self.refresh_options_button_visibility()
        # model_obj = convert_model_json_to_obj(key)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.options_btn.move(self.width() - 40, 0)

    # only show options button when the mouse is over the combobox
    def enterEvent(self, event):
        has_items = self.model().rowCount() > 0
        if has_items:
            self.options_btn.show()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.refresh_options_button_visibility()
        super().leaveEvent(event)

    # def mousePressEvent(self, event):
    #     if self.options_btn.geometry().contains(event.pos()):
    #         self.options_btn.show_options()
    #     else:
    #         super().mousePressEvent(event)

    def paintEvent(self, event):
        current_item = self.model().item(self.currentIndex())
        if current_item:
            # Check if the selected item's text color is red
            if current_item.foreground().color() == QColor('red'):
                # Set the text color to red when
                # painter = QPainter(self)
                option = QStyleOptionComboBox()
                self.initStyleOption(option)

                painter = QStylePainter(self)
                try:
                    painter.setPen(QColor('red'))
                    painter.drawComplexControl(QStyle.CC_ComboBox, option)

                    # Get the text rectangle
                    text_rect = self.style().subControlRect(QStyle.CC_ComboBox, option, QStyle.SC_ComboBoxEditField)
                    text_rect.adjust(2, 0, -2, 0)  # Adjust the rectangle to provide some padding

                    # Draw the text with red color
                    current_text = self.currentText()
                    painter.drawText(text_rect, Qt.AlignLeft, current_text)
                finally:
                    painter.end()
                return

        if self.model().rowCount() == 0:
            painter = QPainter()
            if not painter.begin(self):
                super().paintEvent(event)
                return
            try:
                # painter.setPen(QColor('red'))
                painter.drawText(self.rect(), Qt.AlignLeft, 'No models found')
            finally:
                painter.end()
            return

        super().paintEvent(event)

    # def paintEvent(self, event):
    #     current_item = self.model().item(self.currentIndex())
    #     if current_item:
    #         # Check if the selected item's text color is red
    #         if current_item.foreground().color() == QColor('red'):
    #             # Set the text color to red when
    #             # painter = QPainter(self)
    #             option = QStyleOptionComboBox()
    #             self.initStyleOption(option)

    #             painter = QStylePainter(self)
    #             painter.setPen(QColor('red'))
    #             painter.drawComplexControl(QStyle.CC_ComboBox, option)

    #             # Get the text rectangle
    #             text_rect = self.style().subControlRect(QStyle.CC_ComboBox, option, QStyle.SC_ComboBoxEditField)
    #             text_rect.adjust(2, 0, -2, 0)  # Adjust the rectangle to provide some padding

    #             # Draw the text with red color
    #             current_text = self.currentText()
    #             painter.drawText(text_rect, Qt.AlignLeft, current_text)
    #             return

    #     if self.model().rowCount() == 0:
    #         painter = QPainter(self)
    #         # painter.setPen(QColor('red'))
    #         painter.drawText(self.rect(), Qt.AlignLeft, 'No models found')
    #         return

    #     super().paintEvent(event)

    class OptionsButton(IconButton):
        def __init__(self, parent, *args, **kwargs):
            super().__init__(parent=parent, *args, **kwargs)
            self.clicked.connect(self.show_options)
            self.hide()
            # self.config_widget = CustomDropdown(self)

        def showEvent(self, event):
            super().showEvent(event)
            self.parent.options_btn.move(self.parent.width() - 40, 0)

        def show_options(self):
            if self.parent.config_widget.isVisible():
                self.parent.config_widget.hide()
            else:
                self.parent.config_widget.show()


# class ModelComboBox(BaseComboBox):
#     """
#     BE CAREFUL SETTING BREAKPOINTS DUE TO PYSIDE COMBOBOX BUG
#     Needs to be here atm to avoid circular references
#     """
#     def __init__(self, *args, **kwargs):
#         self.parent = kwargs.pop('parent', None)
#         self.first_item = kwargs.pop('first_item', None)
#         self.model_kind = kwargs.pop('model_kind', 'ALL')
#         super().__init__(*args, **kwargs)
#
#         self.options_btn = self.OptionsButton(
#             parent=self,
#             icon_path=':/resources/icon-settings-solid.png',
#             tooltip='Options',
#             size=20,
#         )
#         from gui.popup import PopupModel
#
#         self.config_widget = PopupModel(self)
#         self.layout = CHBoxLayout(self)
#         self.layout.addWidget(self.options_btn)
#         self.options_btn.move(-20, 0)
#
#         self.load()
#
#     def load(self):
#         #
#         # matched_provider_ids = sql.get_results(f"""
#         #     SELECT DISTINCT a.id
#         #     FROM apis a
#         #     JOIN models m
#         #         ON a.id = m.api_id
#         #     WHERE m.kind = ? OR ? = 'ALL'
#         #     ORDER BY a.pinned DESC, a.name
#         # """, (self.model_kind, self.model_kind), return_type='list')  # todo clean
#         with block_signals(self):
#             self.clear()
#
#             model = QStandardItemModel()
#             self.setModel(model)
#
#             api_models = {}
#
#             from gui import system
#             for provider_name, provider in system.manager.providers.items():
#                 # api_id =
#                 # if provider.api_ids not in matched_provider_ids:
#                 #     continue
#                 for (kind, model_name), api_id in provider.model_api_ids.items():
#                     if not model_name:  # todo
#                         continue
#                     if self.model_kind not in ('ALL', kind):
#                         continue
#                     api_name = provider.api_ids[api_id]
#                     model_config = provider.models.get((kind, model_name))
#                     alias = provider.model_aliases.get((kind, model_name), model_name)
#                     api_key = model_config.get('api_key', '')
#                     if api_key == '':
#                         continue
#                     if api_name not in api_models:
#                         api_models[api_name] = []
#                     api_models[api_name].append((kind, model_name, provider_name, alias))
#
#             for api_name, models in api_models.items():
#                 if api_name.lower() == 'openai':
#                     pass
#                 header_item = QStandardItem(api_name)
#                 header_item.setData('header', Qt.UserRole)
#                 header_item.setEnabled(False)
#                 font = header_item.font()
#                 font.setBold(True)
#                 header_item.setFont(font)
#                 model.appendRow(header_item)
#
#                 for kind, model_name, provider_name, alias in models:
#                     data = {
#                         'kind': kind,
#                         'model_name': model_name or '',  # todo
#                         # 'model_params': model_config,  purposefully exclude params
#                         'provider': provider_name,
#                     }
#                     item = QStandardItem(alias)
#                     item.setData(json.dumps(data), Qt.UserRole)
#                     model.appendRow(item)
#
#     def update_config(self):
#         """Implements same method as ConfigWidget, as a workaround to avoid inheriting from it"""
#         if hasattr(self.parent, 'update_config'):
#             self.parent.update_config()
#
#         if hasattr(self, 'save_config'):
#             self.save_config()
#
#         self.refresh_options_button_visibility()
#
#     def refresh_options_button_visibility(self):
#         self.options_btn.setVisible(len(self.config_widget.get_config()) > 0)
#
#     def get_value(self):
#         """
#         DO NOT PUT A BREAKPOINT IN HERE BECAUSE IT WILL FREEZE YOUR PC (LINUX, PYCHARM & VSCODE) ISSUE WITH PYSIDE COMBOBOX
#         """
#         # from utils.helpers import convert_model_json_to_obj
#         model_key = self.currentData()
#         model_obj = convert_model_json_to_obj(model_key)
#         model_obj['model_params'] = self.config_widget.get_config()  #!88!#
#         return model_obj
#
#     def set_key(self, key):
#         # from utils.helpers import convert_model_json_to_obj
#         model_obj = convert_model_json_to_obj(key)
#         super().set_key(json.dumps(model_obj))
#
#     def resizeEvent(self, event):
#         super().resizeEvent(event)
#         self.options_btn.move(self.width() - 40, 0)
#
#     # only show options button when the mouse is over the combobox
#     def enterEvent(self, event):
#         self.options_btn.show()
#         super().enterEvent(event)
#
#     def leaveEvent(self, event):
#         self.refresh_options_button_visibility()
#         super().leaveEvent(event)
#
#     def mouseMoveEvent(self, event):
#         self.options_btn.show()
#         super().mouseMoveEvent(event)
#
#     def mousePressEvent(self, event):
#         if self.options_btn.geometry().contains(event.pos()):
#             self.options_btn.show_options()
#         else:
#             super().mousePressEvent(event)
#
#     def paintEvent(self, event):
#         current_item = self.model().item(self.currentIndex())
#         if current_item:
#             # Check if the selected item's text color is red
#             if current_item.foreground().color() == QColor('red'):
#                 # Set the text color to red when
#                 # painter = QPainter(self)
#                 option = QStyleOptionComboBox()
#                 self.initStyleOption(option)
#
#                 painter = QStylePainter(self)
#                 painter.setPen(QColor('red'))
#                 painter.drawComplexControl(QStyle.CC_ComboBox, option)
#
#                 # Get the text rectangle
#                 text_rect = self.style().subControlRect(QStyle.CC_ComboBox, option, QStyle.SC_ComboBoxEditField)
#                 text_rect.adjust(2, 0, -2, 0)  # Adjust the rectangle to provide some padding
#
#                 # Draw the text with red color
#                 current_text = self.currentText()
#                 painter.drawText(text_rect, Qt.AlignLeft, current_text)
#                 return
#
#         super().paintEvent(event)
#
#     class OptionsButton(IconButton):
#         def __init__(self, parent, *args, **kwargs):
#             super().__init__(parent=parent, *args, **kwargs)
#             self.clicked.connect(self.show_options)
#             self.hide()
#             # self.config_widget = CustomDropdown(self)
#
#         def showEvent(self, event):
#             super().showEvent(event)
#             self.parent.options_btn.move(self.parent.width() - 40, 0)
#
#         def show_options(self):
#             if self.parent.config_widget.isVisible():
#                 self.parent.config_widget.hide()
#             else:
#                 self.parent.config_widget.show()
