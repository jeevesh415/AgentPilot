# import asyncio
# import json
# import threading
# import uuid

# from PySide6.QtCore import QObject, Signal, Slot, QRunnable
# from itertools import islice
# from datetime import datetime, timezone

# from PySide6.QtWidgets import QMessageBox
# from dateutil.rrule import rrulestr

# from utils import sql
# from utils.helpers import BaseManager, receive_workflow, display_message
# from utils.sql import define_table

# define_table('tasks')

# class TaskManager(BaseManager):
#     def __init__(self, system):
#         super().__init__(
#             system,
#             table_name='tasks',
#             folder_key='tasks',
#             load_columns=['name', 'config'],
#             default_fields={
#                 'config': {'_TYPE': 'text_block'}
#             },
#             add_item_options={'title': 'Add Task', 'prompt': 'Enter a name for the task:'},
#             del_item_options={'title': 'Delete Task', 'prompt': 'Are you sure you want to delete this task?'},
#             config_is_workflow=True,
#         )

# # # class TaskManager:  # (QObject):
# # #     # taskFinished = Signal(str, str)
# # #     # taskError = Signal(str)

# #     def __init__(self, system):
# #         # super().__init__(parent=None)
# #         self.system = system
#         self.task_names = {}
#         self.task_configs = {}
#         self.scheduled_tasks = {}
#         # self.taskFinished.connect(self.on_task_finished)
#         # self.taskError.connect(self.on_task_error)

#         self.thread_lock = threading.Lock()

#     def load(self):
#         self.task_names = sql.get_results("""
#             SELECT
#                 uuid,
#                 name
#             FROM tasks""", return_type='dict')

#         self.task_configs = sql.get_results("""
#             SELECT
#                 uuid,
#                 config
#             FROM tasks""", return_type='dict')
#         self.task_configs = {k: json.loads(v) for k, v in self.task_configs.items()}

#         self.schedule_upcoming_tasks()

#     def schedule_upcoming_tasks(self):
#         print('schedule_upcoming_tasks')
#         with self.thread_lock:
#             now = datetime.now(timezone.utc)
#             for task_id, config in self.task_configs.items():
#                 rrule_str = config.get('rrule', None)
#                 if not rrule_str or rrule_str == '':
#                     continue

#                 try:
#                     rule = rrulestr(rrule_str)
#                 except Exception as e:
#                     print(f"Error parsing rrule for task {task_id}: {e}")
#                     continue

#                 next_occurrence = next(rule.xafter(now, inc=False, count=1), None)
#                 if not next_occurrence:
#                     continue

#                 if task_id in self.scheduled_tasks:
#                     if self.scheduled_tasks[task_id]['occurrence'] == next_occurrence \
#                             and self.scheduled_tasks[task_id]['config'] == config:
#                         continue
#                     task_dict = self.scheduled_tasks.pop(task_id)
#                     runnable = task_dict.get('runnable', None)
#                     if runnable:
#                         runnable.cancel()

#                 delay = max((next_occurrence - now).total_seconds(), 0)
#                 self.scheduled_tasks[task_id] = {
#                     'occurrence': next_occurrence, 'runnable': None, 'config': None}  # , 'run_uuid': None
#                 runnable = self.schedule_task(task_id, delay)  # Convert to milliseconds for QTimer
#                 # run_uuid = runnable.run_uuid
#                 # self.scheduled_tasks[task_id]['run_uuid'] = run_uuid
#                 self.scheduled_tasks[task_id]['runnable'] = runnable
#                 self.scheduled_tasks[task_id]['config'] = config.copy()

#                 print(f'All tasks scheduled: {list(self.scheduled_tasks.keys())}')
#                 print(f'All tasks in qthreadpool: {self.system._main_gui.task_threadpool.activeThreadCount()}')

#     def schedule_task(self, task_uuid, delay):
#         threadpool = self.system._main_gui.task_threadpool
#         task_runnable = self.TaskRunnable(self, task_uuid, delay)
#         threadpool.start(task_runnable)
#         # print(f'Scheduled task {uuid} to run in {delay} seconds')
#         return task_runnable

#     class TaskRunnable(QRunnable):
#         def __init__(self, parent, task_uuid, delay):
#             super().__init__()
#             self.task_manager = parent
#             self.uuid = task_uuid
#             self.delay = delay
#             self.cancelled = False
#             # create a new uuid4 for the run
#             self.run_uuid = uuid.uuid4()

#         def run(self):
#             asyncio.run(self.run_task_with_delay())

#         def cancel(self):
#             self.cancelled = True

#         async def run_task_with_delay(self):
#             try:
#                 for _ in range(int(self.delay * 20)):
#                     if self.cancelled:
#                         return
#                     await asyncio.sleep(0.05)
#                 res = self.task_manager.run_task(self.uuid)
#                 self.task_manager.taskFinished.emit(self.uuid, res)

#             except Exception as e:
#                 self.task_manager.taskError.emit(str(e))

#     @Slot(str, str)
#     def on_task_finished(self, task_uuid, result):
#         print(f'Task {task_uuid} completed with result: {result}')
#         self.schedule_upcoming_tasks()

#     def on_task_error(self, error):
#         print(f'Task error: {error}')
#         display_message(self.system._main_gui,
#             message=f'Task error: {error}',
#             icon=QMessageBox.Warning,
#         )

#     async def receive_task(self, task_uuid, params=None):
#         wf_config = self.task_configs[task_uuid]
#         task_name = self.task_names.get(task_uuid, 'Untitled task')
#         async for key, chunk in receive_workflow(wf_config, kind='TASK', params=params, chat_title=task_name, main=self.system._main_gui):
#             yield key, chunk

#     async def run_task_async(self, task_uuid, params=None):
#         response = ''
#         async for key, chunk in self.receive_task(task_uuid, params=params):
#             response += chunk
#         return response

#     def run_task(self, task_uuid, params=None):
#         return asyncio.run(self.run_task_async(task_uuid, params))

#     def list_tasks_per_day(self):
#         date_occurrences = {}
#         now = datetime.now(timezone.utc)

#         for task_id, config in self.task_configs.items():
#             rrule_str = config.get('rrule', None)
#             if not rrule_str or rrule_str == '':
#                 continue

#             try:
#                 rule = rrulestr(rrule_str)
#             except Exception as e:
#                 print(f"Error parsing rrule for task {task_id}: {e}")
#                 continue

#             try:
#                 max_occurrences = 10000
#                 half_count = max_occurrences // 2

#                 before = list(islice(rule.between(rule._dtstart, now, inc=True) or [], half_count))
#                 after = list(rule.xafter(dt=now, inc=False, count=half_count + max_occurrences % 2))

#                 before.reverse()
#                 occurrences = before + after
#                 for occ in occurrences:
#                     date = occ.date()
#                     if date not in date_occurrences:
#                         date_occurrences[date] = set()
#                     date_occurrences[date].add(task_id)

#             except Exception as e:
#                 print(f"Error generating occurrences for task {task_id}: {e}")
#                 continue

#         return dict(sorted(date_occurrences.items()))