import asyncio
import json
from datetime import datetime, timezone

from PySide6.QtCore import Signal, QDate, Slot, QRunnable, QObject, QPointF
import qasync
from PySide6.QtGui import Qt, QColor, QTextCharFormat, QFont
from PySide6.QtWidgets import QCalendarWidget, QVBoxLayout, QLabel, QListWidgetItem, QListWidget

# from gui.widgets import ConfigDBTree, ConfigWidget, ConfigJoined
from plugins.workflows.widgets.workflow_settings import WorkflowSettings
from gui.util import find_main_widget
from gui.widgets.config_db_tree import ConfigDBTree
from gui.widgets.config_joined import ConfigJoined
from gui.widgets.config_widget import ConfigWidget
from utils import sql
from utils.helpers import block_signals, apply_alpha_to_hex, set_module_type
from gui import system


class CustomCalendar(QCalendarWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.setHorizontalHeaderFormat(QCalendarWidget.SingleLetterDayNames)

        self.task_occurrences = {}
        self.set_today()

        from gui.style import TEXT_COLOR
        header_format = QTextCharFormat()
        transparent = QColor('#00000000')
        header_format.setBackground(transparent)
        header_format.setFontWeight(QFont.Bold)
        self.setHeaderTextFormat(header_format)
        text_format = QTextCharFormat()
        text_format.setForeground(QColor(TEXT_COLOR))
        text_weekend_format = QTextCharFormat()
        text_weekend_format.setForeground(QColor(apply_alpha_to_hex(TEXT_COLOR, 0.6)))
        for day in (Qt.Monday, Qt.Tuesday, Qt.Wednesday, Qt.Thursday, Qt.Friday):
            self.setWeekdayTextFormat(day, text_format)
        for day in (Qt.Saturday, Qt.Sunday):
            self.setWeekdayTextFormat(day, text_weekend_format)

    def load(self):
        self.update_task_occurrences()
        pass

    def set_today(self):
        """Set the calendar view to today's date and select it"""
        today = QDate.currentDate()
        self.setSelectedDate(today)

    def update_task_occurrences(self):
        tasks_manager = system.manager.tasks
        if not tasks_manager:
            return

        task_list = tasks_manager.list_tasks_per_day()
        self.task_occurrences = task_list
        self.updateCells()

    def paintCell(self, painter, rect, date):
        """Customize the appearance of individual day cells"""
        super().paintCell(painter, rect, date)
        from gui.style import ACCENT_COLOR_1, TEXT_COLOR

        # Mark today's date with a red circle
        if date == QDate.currentDate():
            painter.save()
            painter.setPen(QColor(TEXT_COLOR))
            painter.drawEllipse(rect.adjusted(3, 0, -4, -1))
            painter.restore()

        n_date = datetime(date.year(), date.month(), date.day()).date()
        # Draw dots for task occurrences
        if n_date in self.task_occurrences:
            num_tasks = min(len(self.task_occurrences[n_date]), 4)  # Limit to 4 tasks
            painter.save()
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(ACCENT_COLOR_1))

            dot_size = 3
            spacing = 2
            column_spacing = 5

            # Calculate the starting position for the dots
            start_x = rect.right() - dot_size / 2  # 10 pixels from the right side
            start_y = rect.center().y() - (dot_size + spacing) / 2

            for i in range(num_tasks):
                row = i % 2
                col = i // 2
                x = start_x - col * column_spacing
                y = start_y + row * (dot_size + spacing)
                painter.drawEllipse(QPointF(x, y), dot_size / 2, dot_size / 2)

            painter.restore()


@set_module_type('Pages')
class Page_Tasks_Settings(ConfigJoined):
    display_name = 'Tasks'
    icon_path = ":/resources/icon-tasks.png"
    page_type = 'main'  # either 'settings', 'main', or 'any' ('any' means it can be pinned between main and settings)

    def __init__(self, parent):
        super().__init__(parent=parent, layout_type='vertical', propagate_config=False)
        self.widgets = [
            self.Page_Tasks_Calendar(parent=self),
            self.Page_Scheduled_Tasks(parent=self),
        ]

        self.calendar = self.widgets[0].widgets[0]
        # self.icon_path = ":/resources/icon-tasks.png"
        # self.try_add_breadcrumb_widget(root_title='Tasks')

    class Page_Tasks_Calendar(ConfigJoined):
        def __init__(self, parent):
            super().__init__(
                parent=parent,
                layout_type='horizontal',
                propagate_config=False,
            )

            self.widgets = [
                self.Page_Tasks_Calendar_Widget(parent=self),
                self.Page_Tasks_Calendar_Fields(parent=self),
            ]
            self.setFixedHeight(175)
            self.widgets[0].selectionChanged.connect(self.widgets[1].load)

        class Page_Tasks_Calendar_Widget(CustomCalendar):
            def __init__(self, parent):
                super().__init__(parent)
                self.setMaximumWidth(350)

        class Page_Tasks_Calendar_Fields(ConfigWidget):
            def __init__(self, parent):
                super().__init__(parent)
                self.layout = QVBoxLayout(self)

                self.label = QLabel('')
                self.label.setStyleSheet('font-size: 10pt; font-weight: bold;')
                self.layout.addWidget(self.label)

                self.task_list = QListWidget(self)
                self.task_list.itemClicked.connect(self.on_task_clicked)
                self.layout.addWidget(self.task_list)
                self.layout.addStretch(1)

            def load(self):
                self.load_date()

            def load_date(self):
                calendar_date = self.parent.widgets[0].selectedDate()
                calendar_date = datetime(calendar_date.year(), calendar_date.month(), calendar_date.day()).date()

                formatted_date = calendar_date.strftime('%d %B %Y, %A')
                self.label.setText(formatted_date)

                task_ids_on_date = self.parent.widgets[0].task_occurrences.get(calendar_date, [])
                tasks_data = sql.get_results(f"""
                    SELECT
                        id,
                        name,
                        config
                    FROM tasks
                    WHERE uuid IN ({','.join('?' * len(task_ids_on_date))})
                """, task_ids_on_date)

                # Clear the previous list of tasks
                self.task_list.clear()

                # add a list of tasks for the selected date
                for task_id, task_name, task_config in tasks_data:
                    task_config = json.loads(task_config)
                    task_time = task_config.get('time_expression', '')
                    task_time = f' ({task_time})' if task_time else ''

                    # Create a list item with the task name and time
                    item_text = f'{task_name}{task_time}'
                    item = QListWidgetItem(item_text)
                    item.setData(Qt.UserRole, task_id)

                    self.task_list.addItem(item)

            def on_task_clicked(self, item):
                task_id = item.data(Qt.UserRole)
                self.parent.parent.widgets[1].tree.select_items_by_id(task_id)

    class Page_Scheduled_Tasks(ConfigDBTree):
        def __init__(self, parent):
            super().__init__(
                parent=parent,
                table_name='tasks',
                query="""
                    SELECT
                        name,
                        id,
                        COALESCE(json_extract(config, '$.time_expression'), ''),
                        COALESCE(json_extract(config, '$.rrule'), ''),
                        -- COALESCE(json_extract(config, '$.enabled'), 1),
                        folder_id
                    FROM tasks
                    WHERE kind = 'SCHEDULED'
                    ORDER BY pinned DESC, ordr, name COLLATE NOCASE""",
                schema=[
                    {
                        'text': 'Tasks',
                        'key': 'name',
                        'type': str,
                        # 'width': 150,
                        'stretch': True,
                    },
                    {
                        'text': 'id',
                        'key': 'id',
                        'type': int,
                        'visible': False,
                    },
                    {
                        'text': 'When',
                        'key': 'time_expression',
                        'type': str,
                        'is_config_field': True,
                        'stretch': True,
                    },
                    {
                        'text': 'RRule',
                        'key': 'rrule',
                        'type': str,
                        'is_config_field': True,
                        'visible': False,
                        'stretch': True,
                    },
                    # {
                    #     'text': '',
                    #     'key': 'enabled',
                    #     'type': bool,
                    #     'is_config_field': True,
                    # },
                ],
                add_item_options={'title': 'Add Task', 'prompt': 'Enter a name for the task:'},
                del_item_options={'title': 'Delete Task', 'prompt': 'Are you sure you want to delete this task?'},
                folder_key='tasks_scheduled',
                kind='SCHEDULED',
                readonly=False,
                layout_type='vertical',
                config_widget=self.Task_Config_Widget(self),
                default_item_icon=':/resources/icon-tasks-small.png',
            )
            self.splitter.setSizes([400, 1000])

        def on_edited(self):
            system.manager.load_manager('tasks')
            self.parent.widgets[0].load()

        def on_item_selected(self):
            current_parent = self.config_widget.parent
            if isinstance(current_parent, ConfigDBTree) and current_parent != self:
                with block_signals(current_parent.tree):
                    current_parent.tree.clearSelection()
            self.config_widget.parent = self
            super().on_item_selected()

        @qasync.asyncSlot()
        async def on_cell_edited(self, item):
            col_indx = self.tree.currentColumn()
            if col_indx != 2:
                super().on_cell_edited(item)
                return

            item_id = self.get_selected_item_id()
            if item_id is None:
                return
            time_expression = item.text(col_indx)

            if time_expression.strip() == '':
                self.handle_result('', '', item_id)
                return

            try:
                result = await system.manager.blocks.compute_block_async('expression-to-time', {'expression': time_expression})
                clean_time_expression = await system.manager.blocks.compute_block_async('time-to-expression', {'time': result.strip()})
                self.handle_result(result, clean_time_expression, item_id)
            except Exception as e:
                print(f"Error processing time expression: {e}")

        class AsyncWorker(QRunnable):
            class Signals(QObject):
                result = Signal(str, str, int)
                error = Signal(tuple)
                finished = Signal()

            def __init__(self, time_expression, item_id):
                super().__init__()
                self.time_expression = time_expression
                self.item_id = item_id
                self.signals = self.Signals()

            def run(self):
                if self.time_expression.strip() == '':
                    self.signals.result.emit('', '', self.item_id)
                    return

                try:
                    asyncio.run(self.run_blocks())
                except Exception as e:
                    self.signals.error.emit((type(e), str(e), e.__traceback__))

            async def run_blocks(self):
                result = await system.manager.blocks.compute_block_async('Expression to Time', {'expression': self.time_expression})
                clean_time_expression = await system.manager.blocks.compute_block_async('Time to Expression', {'time': result.strip()})
                self.signals.result.emit(result, clean_time_expression, self.item_id)

        @Slot(str, str, int)
        def handle_result(self, result, time_expression, item_id):
            result = result.strip()
            if 'DTSTART' not in result and result != '':
                now = datetime.now(timezone.utc)
                result = f"DTSTART:{now.strftime('%Y%m%dT%H%M%SZ')}\n{result}"

            sql.execute(f"""
                UPDATE tasks
                SET config = json_set(config, '$.rrule', ?)
                WHERE id = ?
            """ , (result.strip(), item_id))
            sql.execute(f"""
                UPDATE tasks
                SET config = json_set(config, '$.time_expression', ?)
                WHERE id = ?
            """ , (time_expression.strip(), item_id))

            system.manager.load_manager('tasks')
            self.parent.load()

        class Task_Config_Widget(WorkflowSettings):
            def __init__(self, parent):
                super().__init__(parent=parent, compact_mode=True)

            def load_config(self, json_config=None):
                if json_config is None:
                    parent_config = getattr(self.parent, 'config', {})

                    if self.conf_namespace is None and not isinstance(self, ConfigDBTree):
                        json_config = parent_config
                    else:
                        json_config = {k: v for k, v in parent_config.items() if k.startswith(f'{self.conf_namespace}.')}
                super().load_config(json_config)

            def update_config(self):
                self.save_config()

            def save_config(self):
                self.parent.update_config()