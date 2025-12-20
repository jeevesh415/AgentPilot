# from PySide6.QtGui import Qt
# from PySide6.QtWidgets import QVBoxLayout
#
# from gui.widgets import ConfigFields, ConfigJoined, ConfigJsonTree
# from plugins.workflows.members.agent import AgentSettings, Agent
# # from plugins.openinterpreter.src import OpenInterpreter
# # from interpreter.core.core import OpenInterpreter
# # from plugins.openinterpreter.src.core.core import OpenInterpreter
# # from interpreter import OpenInterpreter
# from plugins.openinterpreter.src import OpenInterpreter
# from utils.helpers import split_lang_and_code, convert_model_json_to_obj


from plugins.workflows.members import LlmMember
from utils.helpers import set_module_type
from claude_code_sdk import ClaudeCodeOptions, ClaudeSDKClient, AssistantMessage, TextBlock

from gui import system

@set_module_type(module_type='Members', settings='claude_code_settings')
class ClaudeCode(LlmMember):
    workflow_insert_mode = 'single'

    def __init__(self, **kwargs):
        super().__init__(**kwargs, model_config_key='chat.model')

    # def load(self):
    #     super().load()
    #     self.agent_object = ClaudeCode(**self.config)

    async def receive(self):
        # from gui import system  # todo
        # model_json = self.config.get(self.model_config_key, system.manager.config.get('system.default_chat_model', 'mistral/mistral-large-latest'))
        # # model_obj = convert_model_json_to_obj(model_json)
        # # structured_data = model_obj.get('model_params', {}).get('structure.data', [])

        # messages = await self.get_messages()
        # # messages = [
        # #     {
        # #         'role': 'user',
        # #         'content': 'hello'
        # #     },
        # #     {
        # #         'role': 'assistant',
        # #         'content': 'hello'
        # #     },
        # #     {
        # #         'role': 'user',
        # #         'content': [
        # #             {
        # #                 "type": "text",
        # #                 "text": "What’s in this image?"
        # #             },
        # #             {
        # #                 "type": "image_url",
        # #                 "image_url": {
        # #                   "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg",
        # #                   "format": "image/jpeg"
        # #                 }
        # #             },
        # #         ]
        # #     },
        # # ]
        # system_msg = self.system_message()

        # if model_obj['model_name'].startswith('gpt-4o-realtime'):  # temp todo
        #     # raise NotImplementedError('Realtime models are not implemented yet.')
        #     stream = self.realtime_client.stream_realtime(model=model_obj, messages=messages, system_msg=system_msg)
        # else:
        #     if system_msg != '':
        #         messages.insert(0, {'role': 'system', 'content': system_msg})
        #     if len(structured_data) > 0:
        #         stream = self.stream_structured_output(model=model_obj, messages=messages)
        #     else:
        stream = self.stream()  # model=model_obj, messages=messages)

        role_responses = {}
        async for key, chunk in stream:
            # pass
            if key not in role_responses:
                role_responses[key] = ''
            if key == 'tools':
                tool_list = chunk
                role_responses['tools'] = tool_list
            else:
                chunk = chunk or ''
                role_responses[key] += chunk
                yield key, chunk

        # if 'api_key' in model_obj['model_params']:
        #     model_obj['model_params'].pop('api_key')
        logging_obj = {
            'id': 0,
            'context_id': self.workflow.context_id,
            'member_id': self.full_member_id(),
            # 'model': model_obj,
            # 'messages': messages,
            'role_responses': role_responses,
        }

        for key, response in role_responses.items():
            # if key == 'tools':
            #     all_tools = response
            #     for tool in all_tools:
            #         tool_args_json = tool['function']['arguments']
            #         # tool_name = tool_name.replace('_', ' ').capitalize()
            #         first_matching_name = next((k for k, v in system.manager.tools.items()
            #                                   if convert_to_safe_case(k) == tool['function']['name']),
            #                                  None)  # todo add duplicate check, or
            #         first_matching_id = sql.get_scalar("SELECT uuid FROM tools WHERE name = ?",
            #                                            (first_matching_name,))
            #         msg_content = json.dumps({  #!toolcall!#
            #             'tool_uuid': first_matching_id,
            #             'tool_call_id': tool['id'], # str(uuid.uuid4()),  #
            #             'name': tool['function']['name'],
            #             'args': tool_args_json,
            #             'text': tool['function']['name'].replace('_', ' ').capitalize(),
            #         })
            #         self.workflow.save_message('tool', msg_content, self.full_member_id(), logging_obj)
            # else:
            if response != '':
                self.workflow.save_message(key, response, self.full_member_id(), logging_obj)

    async def stream(self, *args, **kwargs):
        system_msg = await self.system_message()
        max_turns = self.config.get('max_turns', None)
        messages = await self.get_messages()
        if len(messages) == 0:
            raise NotImplementedError()
        prompt = messages[-1].get('content', None)
        if prompt is None:
            raise NotImplementedError()

        options = ClaudeCodeOptions(
            system_prompt=system_msg,
            max_turns=max_turns,
            allowed_tools=["Bash"],
            # hooks={
            #     "PreToolUse": [
            #         HookMatcher(matcher="Bash", hooks=[check_bash_command]),
            #     ],
            # }
        )
        async with ClaudeSDKClient(options=options) as client:
            print(f"User: {prompt}")
            await client.query(prompt)
            async for msg in client.receive_response():
                if isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        if isinstance(block, TextBlock):
                            yield 'assistant', block.text
                            # print(f"Claude: {block.text}")

    async def system_message(self, msgs_in_system=None, response_instruction='', msgs_in_system_len=0):
        raw_sys_msg = self.config.get('chat.sys_msg', '')
        name = self.config.get('name', '')
        builtin_blocks = {
            'char_name': name,
            'full_name': name,
            'response_type': 'response',
            'verb': '',
        }
        if self.member_id == '4':
            pass

        formatted_sys_msg = await system.manager.blocks.format_string(
            raw_sys_msg,
            ref_workflow=self.workflow,
            additional_blocks=builtin_blocks,
        )

        message_str = ''
        if msgs_in_system:
            if msgs_in_system_len > 0:
                msgs_in_system = msgs_in_system[-msgs_in_system_len:]
            message_str = "\n".join(
                f"""{msg['role']}: \"{msg['content'].strip().strip('"')}\"""" for msg in msgs_in_system)
            message_str = f"\n\nCONVERSATION:\n\n{message_str}\nassistant: "
        if response_instruction != '':
            response_instruction = f"\n\n{response_instruction}\n\n"

        return formatted_sys_msg + response_instruction + message_str

#
#     def load(self):
#         super().load()
#         param_dict = {
#             'offline': self.config.get('plugin.offline', False),
#             'max_output': self.config.get('code.max_output', 2800),
#             'safe_mode': self.config.get('plugin.safe_mode', 'off'),
#             'loop': self.config.get('loop.loop', False),
#             'loop_message': self.config.get('loop.loop_message', """Proceed. You CAN run code on my machine. If you want to run code, start your message with "```"! If the entire task I asked for is done, say exactly 'The task is done.' If you need some specific information (like username or password) say EXACTLY 'Please provide more information.' If it's impossible, say 'The task is impossible.' (If I haven't provided a task, say exactly 'Let me know what you'd like to do next.') Otherwise keep going."""),
#             'disable_telemetry': self.config.get('plugin.disable_telemetry', False),
#             'os': self.config.get('plugin.os', True),
#             # 'system_message': self.system_message(),
#             'custom_instructions': self.config.get('chat.custom_instructions', ''),
#             'user_message_template': self.config.get('chat.user_message_template', '{content}'),
#             'code_output_template': self.config.get('code.code_output_template', "Code output: {content}\n\nWhat does this output mean / what's next (if anything, or are we done)?"),
#             'empty_code_output_template': self.config.get('code.empty_code_output_template', "The code above was executed on my machine. It produced no text output. what's next (if anything, or are we done?)"),
#             'code_output_sender': self.config.get('code.code_output_sender', 'user'),
#             'import_skills': False,
#         }
#         self.agent_object = OpenInterpreter(**param_dict)
#         # print('## Loaded OpenInterpreter obj')
#
#         # model_name = self.config.get('chat.model', 'gpt-4-turbo')
#
#         model_json = self.config.get('chat.model')
#         model_obj = convert_model_json_to_obj(model_json)
#         model_name = model_obj['model_name']
#
#         model_params = self.main.system.providers.get_model_parameters(model_obj)
#         # print('## Fetched model params')
#         self.agent_object.llm.model = model_name
#         self.agent_object.llm.temperature = model_params.get('temperature', 0)
#         self.agent_object.llm.max_tokens = model_params.get('max_tokens', None)
#         self.agent_object.llm.api_key = model_params.get('api_key', None)
#         self.agent_object.llm.api_base = model_params.get('api_base', None)
#
#     async def stream(self, *args, **kwargs):
#         self.agent_object.system_message = self.system_message()  # put this here to only compute blocks when needed
#         native_messages = self.workflow.message_history.get_llm_messages(calling_member_id=self.member_id)
#         messages = self.convert_messages(native_messages)
#         try:
#             code_lang = None
#             for chunk in self.agent_object.chat(message=messages, display=False, stream=True):
#                 if chunk.get('start', False) or chunk.get('end', False):
#                     continue
#
#                 if chunk['type'] == 'message':
#                     yield 'assistant', chunk.get('content', '')
#
#                 elif chunk['type'] == 'code':
#                     if code_lang is None:
#                         code_lang = chunk['format']
#                         yield 'code', f'```{code_lang}\n'
#
#                     code = chunk['content']
#                     yield 'code', code
#                 elif chunk['type'] == 'confirmation':
#                     yield 'code', '\n```'
#                     break
#                 else:
#                     print('Unknown chunk type:', chunk['type'])
#
#         except StopIteration as e:
#             raise NotImplementedError('StopIteration')
#
#     def convert_messages(self, messages):
#         new_messages = []
#         for message in messages:
#             if message['role'] == 'code':
#                 lang, code = split_lang_and_code(message['content'])
#                 message['type'] = 'code'
#                 message['role'] = 'assistant'
#                 message['format'] = lang
#                 message['content'] = code
#
#             elif message['role'] == 'output':
#                 message['type'] = 'console'
#                 message['role'] = 'computer'
#                 message['format'] = 'output'
#             else:
#                 message['type'] = 'message'
#             new_messages.append(message)
#
#         return new_messages
#
#
# class OpenInterpreterSettings(AgentSettings):
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         # self.pages.pop('Files')
#         self.pages.pop('Tools')
#         self.pages['Chat'].pages['Messages'].schema = [
#             {
#                 'text': 'Model',
#                 'type': 'ModelComboBox',
#                 'model_kind': 'CHAT',
#                 'default': 'gpt-3.5-turbo',
#                 'row_key': 0,
#             },
#             {
#                 'text': 'Display markdown',
#                 'type': bool,
#                 'default': True,
#                 'row_key': 0,
#             },
#             {
#                 'text': 'System message',
#                 'key': 'sys_msg',
#                 'type': str,
#                 'num_lines': 2,
#                 'default': '',
#                 'stretch_x': True,
#                 'stretch_y': True,
#                 'label_position': 'top',
#             },
#             {
#                 'text': 'Max messages',
#                 'type': int,
#                 'minimum': 1,
#                 'maximum': 99,
#                 'default': 10,
#                 'width': 60,
#                 'has_toggle': True,
#                 'row_key': 1,
#             },
#             {
#                 'text': 'Max turns',
#                 'type': int,
#                 'minimum': 1,
#                 'maximum': 99,
#                 'default': 7,
#                 'width': 60,
#                 'has_toggle': True,
#                 'row_key': 1,
#             },
#             {
#                 'text': 'Custom instructions',
#                 'type': str,
#                 'num_lines': 2,
#                 'default': '',
#                 'stretch_x': True,
#                 'label_position': 'top',
#                 'row_key': 2,
#             },
#             {
#                 'text': 'User message template',
#                 'type': str,
#                 'num_lines': 2,
#                 'default': '{content}',
#                 'stretch_x': True,
#                 'label_position': 'top',
#                 'row_key': 2,
#             },
#         ]
#         info_widget = self.pages['Info']
#         info_widget.widgets.append(self.Plugin_Fields(parent=info_widget))
#
#         self.pages['Loop'] = self.Loop_Settings(parent=self.pages['Chat'])
#         self.pages['Code'] = self.Code_Settings(parent=self.pages['Chat'])
#
#     class Plugin_Fields(ConfigFields):
#         def __init__(self, parent):
#             super().__init__(parent=parent)
#             self.parent = parent
#             self.conf_namespace = 'plugin'
#             self.label_width = 150
#             self.schema = [
#                 {
#                     'text': 'Offline',
#                     'type': bool,
#                     'default': False,
#                     'map_to': 'offline',
#                 },
#                 {
#                     'text': 'Safe mode',
#                     'type': ('off', 'ask', 'auto',),
#                     'default': False,
#                     'map_to': 'safe_mode',
#                     'width': 75,
#                 },
#                 {
#                     'text': 'Disable telemetry',
#                     'type': bool,
#                     'default': False,
#                     'map_to': 'disable_telemetry',
#                 },
#                 {
#                     'text': 'OS',
#                     'type': bool,
#                     'default': True,
#                     'map_to': 'os',
#                 },
#             ]
#
#     class Loop_Settings(ConfigJoined):
#         def __init__(self, parent):
#             super().__init__(parent=parent, layout_type='vertical')
#             self.widgets = [
#                 self.Loop_Fields(parent=self),
#                 # self.Info_Plugin(parent=self),
#             ]
#
#         class Loop_Fields(ConfigFields):
#             def __init__(self, parent):
#                 super().__init__(parent=parent)
#                 self.parent = parent
#                 self.conf_namespace = 'loop'
#                 self.field_alignment = Qt.AlignHCenter
#                 self.schema = [
#                     {
#                         'text': 'Loop',
#                         'type': bool,
#                         # 'label_width': 150,
#                         'default': False,
#                     },
#                     {
#                         'text': 'Loop message',
#                         'type': str,
#                         # 'label_width': 150,
#                         'stretch_x': True,
#                         'num_lines': 5,
#                         'label_position': 'top',
#                         'default': """Proceed. You CAN run code on my machine. If you want to run code, start your message with "```"! If the entire task I asked for is done, say exactly 'The task is done.' If you need some specific information (like username or password) say EXACTLY 'Please provide more information.' If it's impossible, say 'The task is impossible.' (If I haven't provided a task, say exactly 'Let me know what you'd like to do next.') Otherwise keep going.""",
#                     }
#                 ]
#
#         class Loop_Breakers(ConfigJsonTree):
#             def __init__(self, parent):
#                 super().__init__(parent=parent,
#                                  add_item_options={'title': 'NA', 'prompt': 'NA'},
#                                  del_item_options={'title': 'NA', 'prompt': 'NA'})
#                 self.parent = parent
#                 self.conf_namespace = 'loop.breakers'
#                 self.schema = [
#                     {
#                         'text': 'Loop breakers',
#                         'type': str,
#                         'width': 120,
#                         'default': 'Variable name',
#                     },
#                     {
#                         'text': 'Value',
#                         'type': str,
#                         'stretch': True,
#                         'default': '',
#                     },
#                 ]
#
#     class Code_Settings(ConfigFields):
#         def __init__(self, parent):
#             super().__init__(parent=parent)
#             self.parent = parent
#             self.conf_namespace = 'code'
#             self.schema = [
#                 {
#                     'text': 'Code output template',
#                     'type': str,
#                     'num_lines': 4,
#                     'label_position': 'top',
#                     'stretch_x': True,
#                     'default': "Code output: {content}\n\nWhat does this output mean / what's next (if anything, or are we done)?",
#                 },
#                 {
#                     'text': 'Empty code output template',
#                     'type': str,
#                     'num_lines': 4,
#                     'label_position': 'top',
#                     'stretch_x': True,
#                     'default': "The code above was executed on my machine. It produced no text output. what's next (if anything, or are we done?)"
#                 },
#                 {
#                     'text': 'Code output sender',
#                     'type': str,
#                     'label_position': 'top',
#                     'default': 'user',
#                 },
#                 {
#                     'text': 'Max output',
#                     'type': int,
#                     'minimum': 1,
#                     'maximum': 69420,
#                     'step': 100,
#                     'default': 2800,
#                 }
#             ]
#
# # class OpenInterpreterSettings(AgentSettings):
# #     def __init__(self, *args, **kwargs):
# #         super().__init__(*args, **kwargs)
# #         # self.pages.pop('Files')
# #         page_widget = self.widgets[1]
# #         page_widget.pages.pop('Tools')
# #         page_widget.pages['Chat'].pages['Messages'].schema = [
# #             {
# #                 'text': 'Model',
# #                 'type': 'ModelComboBox',
# #                 'default': 'gpt-3.5-turbo',
# #                 'row_key': 0,
# #             },
# #             {
# #                 'text': 'Display markdown',
# #                 'type': bool,
# #                 'default': True,
# #                 'row_key': 0,
# #             },
# #             {
# #                 'text': 'System message',
# #                 'key': 'sys_msg',
# #                 'type': str,
# #                 'num_lines': 2,
# #                 'default': '',
# #                 'stretch_x': True,
# #                 'stretch_y': True,
# #                 'label_position': 'top',
# #             },
# #             {
# #                 'text': 'Max messages',
# #                 'type': int,
# #                 'minimum': 1,
# #                 'maximum': 99,
# #                 'default': 10,
# #                 'width': 60,
# #                 'has_toggle': True,
# #                 'row_key': 1,
# #             },
# #             {
# #                 'text': 'Max turns',
# #                 'type': int,
# #                 'minimum': 1,
# #                 'maximum': 99,
# #                 'default': 7,
# #                 'width': 60,
# #                 'has_toggle': True,
# #                 'row_key': 1,
# #             },
# #             {
# #                 'text': 'Custom instructions',
# #                 'type': str,
# #                 'num_lines': 2,
# #                 'default': '',
# #                 'stretch_x': True,
# #                 'label_position': 'top',
# #                 'row_key': 2,
# #             },
# #             {
# #                 'text': 'User message template',
# #                 'type': str,
# #                 'num_lines': 2,
# #                 'default': '{content}',
# #                 'stretch_x': True,
# #                 'label_position': 'top',
# #                 'row_key': 2,
# #             },
# #         ]
# #         info_widget = page_widget.pages['Info']
# #         info_widget.widgets.append(self.Plugin_Fields(parent=info_widget))
# #
# #         page_widget.pages['Loop'] = self.Loop_Settings(parent=page_widget.pages['Chat'])
# #         page_widget.pages['Code'] = self.Code_Settings(parent=page_widget.pages['Chat'])
# #
# #     class Plugin_Fields(ConfigFields):
# #         def __init__(self, parent):
# #             super().__init__(parent=parent)
# #             self.parent = parent
# #             self.conf_namespace = 'plugin'
# #             self.label_width = 150
# #             self.schema = [
# #                 {
# #                     'text': 'Offline',
# #                     'type': bool,
# #                     'default': False,
# #                     'map_to': 'offline',
# #                 },
# #                 {
# #                     'text': 'Safe mode',
# #                     'type': ('off', 'ask', 'auto',),
# #                     'default': False,
# #                     'map_to': 'safe_mode',
# #                     'width': 75,
# #                 },
# #                 {
# #                     'text': 'Disable telemetry',
# #                     'type': bool,
# #                     'default': False,
# #                     'map_to': 'disable_telemetry',
# #                 },
# #                 {
# #                     'text': 'OS',
# #                     'type': bool,
# #                     'default': True,
# #                     'map_to': 'os',
# #                 },
# #             ]
# #
# #     class Loop_Settings(ConfigJoined):
# #         def __init__(self, parent):
# #             super().__init__(parent=parent, layout_type=QVBoxLayout)
# #             self.widgets = [
# #                 self.Loop_Fields(parent=self),
# #                 # self.Info_Plugin(parent=self),
# #             ]
# #
# #         class Loop_Fields(ConfigFields):
# #             def __init__(self, parent):
# #                 super().__init__(parent=parent)
# #                 self.parent = parent
# #                 self.conf_namespace = 'loop'
# #                 self.field_alignment = Qt.AlignHCenter
# #                 self.schema = [
# #                     {
# #                         'text': 'Loop',
# #                         'type': bool,
# #                         # 'label_width': 150,
# #                         'default': False,
# #                     },
# #                     {
# #                         'text': 'Loop message',
# #                         'type': str,
# #                         # 'label_width': 150,
# #                         'stretch_x': True,
# #                         'num_lines': 5,
# #                         'label_position': 'top',
# #                         'default': """Proceed. You CAN run code on my machine. If you want to run code, start your message with "```"! If the entire task I asked for is done, say exactly 'The task is done.' If you need some specific information (like username or password) say EXACTLY 'Please provide more information.' If it's impossible, say 'The task is impossible.' (If I haven't provided a task, say exactly 'Let me know what you'd like to do next.') Otherwise keep going.""",
# #                     }
# #                 ]
# #
# #         class Loop_Breakers(ConfigJsonTree):
# #             def __init__(self, parent):
# #                 super().__init__(parent=parent,
# #                                  add_item_options={'title': 'NA', 'prompt': 'NA'},
# #                                  del_item_options={'title': 'NA', 'prompt': 'NA'})
# #                 self.parent = parent
# #                 self.conf_namespace = 'loop.breakers'
# #                 self.schema = [
# #                     {
# #                         'text': 'Loop breakers',
# #                         'type': str,
# #                         'width': 120,
# #                         'default': 'Variable name',
# #                     },
# #                     {
# #                         'text': 'Value',
# #                         'type': str,
# #                         'stretch': True,
# #                         'default': '',
# #                     },
# #                 ]
# #
# #     class Code_Settings(ConfigFields):
# #         def __init__(self, parent):
# #             super().__init__(parent=parent)
# #             self.parent = parent
# #             self.conf_namespace = 'code'
# #             self.schema = [
# #                 {
# #                     'text': 'Code output template',
# #                     'type': str,
# #                     'num_lines': 4,
# #                     'label_position': 'top',
# #                     'stretch_x': True,
# #                     'default': "Code output: {content}\n\nWhat does this output mean / what's next (if anything, or are we done)?",
# #                 },
# #                 {
# #                     'text': 'Empty code output template',
# #                     'type': str,
# #                     'num_lines': 4,
# #                     'label_position': 'top',
# #                     'stretch_x': True,
# #                     'default': "The code above was executed on my machine. It produced no text output. what's next (if anything, or are we done?)"
# #                 },
# #                 {
# #                     'text': 'Code output sender',
# #                     'type': str,
# #                     'label_position': 'top',
# #                     'default': 'user',
# #                 },
# #                 {
# #                     'text': 'Max output',
# #                     'type': int,
# #                     'minimum': 1,
# #                     'maximum': 69420,
# #                     'step': 100,
# #                     'default': 2800,
# #                 }
# #             ]
