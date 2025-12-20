"""LiteLLM Provider Module.

This module provides the LiteLLM provider integration for Agent Pilot, enabling
connection to over 100 different AI model providers through a unified interface.
LiteLLM serves as the primary AI model integration layer, supporting text generation,
structured outputs, and various model configurations.

Key Features:
- Support for 100+ AI model providers (OpenAI, Anthropic, Google, etc.)
- Unified API interface for different model providers
- Structured output generation with Instructor integration
- Asynchronous and synchronous completion support
- Network connectivity validation and error handling
- Model configuration and parameter management
- Integration with Agent Pilot's model management system

The LiteLLM provider enables Agent Pilot to work with virtually any AI model
provider while maintaining consistent interfaces and functionality.
"""  # unchecked

import json
import os
import asyncio
import re
from typing import List, Dict, Any, Optional

from PySide6.QtWidgets import QMessageBox
from openai import AsyncOpenAI
import instructor
import litellm
from litellm import acompletion, completion
from pydantic import create_model

from gui import system
from utils.reset import reset_table
from utils import sql
from utils.helpers import display_message, network_connected, convert_model_json_to_obj, convert_to_safe_case
from plugins.workflows.managers.providers import Provider

litellm.log_level = 'ERROR'


class LitellmProvider(Provider):
    from gui.widgets.config_fields import ConfigFields
    def __init__(self, parent):  # , api_id=None):
        super().__init__(parent=parent)
        # self.visible_tabs = ['Chat', 'Video']
        os.environ['OR_SITE_URL'] = 'https://agentpilot.ai'
        os.environ['OR_APP_NAME'] = 'AgentPilot'

        realtime_model_id = sql.get_scalar("""
            SELECT id 
            FROM models 
            WHERE json_extract(config, '$.model_name') LIKE 'gpt-4o-realtime%'
                AND kind = 'CHAT'
        """)

        if realtime_model_id:
            self.schema_overrides = {
                # 'gpt-4o-realtime-preview-2024-10-01': [
                int(realtime_model_id): [
                    {
                        'text': 'Model name',
                        'type': str,
                        'label_width': 125,
                        'width': 265,
                        'tooltip': 'The name of the model to send to the API',
                        'default': '',
                    },
                    {
                        'text': 'Voice',
                        'type': ('Alloy','Ash','Ballad','Coral','Echo','Sage','Shimmer','Verse',),
                        'label_width': 125,
                        'default': 'Alloy',
                    },
                    {
                        'text': 'Turn detection',
                        'type': bool,
                        'label_width': 125,
                        'default': True,
                    },
                    {
                        'text': 'Temperature',
                        'type': float,
                        'has_toggle': True,
                        'label_width': 145,
                        'minimum': 0.0,
                        'maximum': 1.0,
                        'step': 0.05,
                        'default': 0.6,
                    },
                ],
            }

    # def get_model(self, model_obj):  # kind, model_name):
    #     kind, model_name = model_obj.get('kind'), model_obj.get('model_name')
    #     return self.models.get((kind, model_name), {})

    def get_model_parameters(self, model_obj, incl_api_data=True):
        provider, kind, model_name = model_obj['provider'], model_obj['kind'], model_obj['model_name']
        if kind == 'CHAT':
            accepted_keys = [
                'temperature',
                'top_p',
                'presence_penalty',
                'frequency_penalty',
                'max_tokens',
            ]
            if incl_api_data:
                accepted_keys.extend([
                    'api_key',
                    'api_base',
                    'api_version',
                    'custom_provider',
                ])
        else:
            accepted_keys = []

        model_config = self.models.get((provider, kind, model_name), {})
        cleaned_model_config = {k: v for k, v in model_config.items() if k in accepted_keys}
        return cleaned_model_config

    # async def run_model_sora_2(self, model_obj, **kwargs):
    #     api_key = system.manager.apis.get('Openai').get('api_key', '')
    #     client = AsyncOpenAI(api_key=api_key)
    #     video = await client.videos.create_and_poll(
    #         model=model_obj.get('model_name', ''),
    #         prompt="A video of a cat on a motorcycle",
    #     )

    #     if video.status == "completed":
    #         print("Video successfully completed: ", video)
    #         # yield video
    #     else:
    #         print("Video creation failed. Status: ", video.status)
    #         # yield video

    async def run_model(self, model_obj, **kwargs):
        model_obj = convert_model_json_to_obj(model_obj)
        model_s_params = system.manager.models.get_model(model_obj)
        model_obj['model_params'] = {**model_obj.get('model_params', {}), **model_s_params}
        accepted_keys = [
            'temperature',
            'top_p',
            'presence_penalty',
            'frequency_penalty',
            'max_tokens',
            'api_key',
            'api_base',
            'api_version',
            'custom_provider',
        ]
        model_obj['model_params'] = {k: v for k, v in model_obj['model_params'].items() if k in accepted_keys}

        # if model_obj.get('model_name', '').startswith('sora-2'):
        #     return await self.run_model_sora_2(model_obj, **kwargs)

        # print('Model params: ', json.dumps(model_obj['model_params']))

        stream = kwargs.get('stream', True)
        messages = kwargs.get('messages', [])
        tools = kwargs.get('tools', None)

        model_name = model_obj['model_name']
        model_params = model_obj.get('model_params', {})

        # if not all(msg['content'] for msg in messages):
        #     pass

        ex = None
        for i in range(5):
            try:
                kwargs = dict(
                    model=model_name,
                    messages=messages,
                    stream=stream,
                    request_timeout=100,
                    **(model_params or {}),
                )
                if tools:
                    kwargs['tools'] = tools
                    kwargs['tool_choice'] = "auto"

                if next(iter(messages), {}).get('role') != 'user':
                    pass
                return await acompletion(**kwargs)
                
            except Exception as e:
                if not network_connected():
                    ex = ConnectionError('No network connection.')
                    break
                if 'Your organization must be verified to stream this model.' in str(e):
                    display_message(
                        icon=QMessageBox.Warning,
                        title="Warning",
                        message="You must verify your organization to stream this model. Switching to non-streaming response.",
                    )
                    stream = False
                    continue
                ex = e
                await asyncio.sleep(0.3 * i)
        raise ex

    async def get_structured_output(self, model_obj, **kwargs):
        def create_dynamic_model(model_name: str, attributes: List[Dict[str, Any]]) -> Any:
            field_definitions = {}

            type_mapping = {
                "str": str,
                "int": int,
                "float": float,
                "bool": bool
            }

            for attr in attributes:
                field_type = type_mapping.get(attr["type"], Any)
                if not attr["req"]:
                    field_type = Optional[field_type]

                attr["attribute"] = convert_to_safe_case(attr["attribute"])
                field_definitions[attr["attribute"]] = (field_type, ... if attr["req"] else None)

            return create_model(model_name, **field_definitions)

        structured_class_name = model_obj.get('model_params', {}).get('structured.class_name', 'Untitled')
        structured_data = model_obj.get('model_params', {}).get('structure.data', [])
        pydantic_model = create_dynamic_model(structured_class_name, structured_data)

        # todo de-dupe
        accepted_keys = [
            'temperature',
            'top_p',
            'presence_penalty',
            'frequency_penalty',
            'max_tokens',
            'api_key',
            'api_base',
            'api_version',
            'custom_provider',
        ]
        model_s_params = system.manager.models.get_model(model_obj)
        model_obj['model_params'] = {**model_obj.get('model_params', {}), **model_s_params}
        model_obj['model_params'] = {k: v for k, v in model_obj['model_params'].items() if k in accepted_keys}

        client = instructor.from_litellm(completion)

        model_name = model_obj['model_name']
        model_params = model_obj.get('model_params', {})
        messages = kwargs.get('messages', [])

        resp = client.chat.completions.create(
            model=model_name,
            messages=messages,
            response_model=pydantic_model,
            **(model_params or {}),
        )
        assert isinstance(resp, pydantic_model)
        return resp.json()

    # async def get_scalar_async(self, prompt, single_line=False, num_lines=0, model_obj=None):
    #     if single_line:
    #         num_lines = 1

    #     if num_lines <= 0:
    #         response = await self.run_model(model_obj=model_obj, messages=[{'role': 'user', 'content': prompt}], stream=False)
    #         output = response.choices[0]['message']['content']
    #     else:
    #         response_stream = await self.run_model(model_obj=model_obj, messages=[{'role': 'user', 'content': prompt}], stream=True)
    #         output = ''
    #         line_count = 0
    #         async for resp in response_stream:
    #             if 'delta' in resp.choices[0]:
    #                 delta = resp.choices[0].get('delta', {})
    #                 chunk = delta.get('content', '')
    #             else:
    #                 chunk = resp.choices[0].get('text', '')

    #             if chunk is None:
    #                 continue
    #             if '\n' in chunk:
    #                 chunk = chunk.split('\n')[0]
    #                 output += chunk
    #                 line_count += 1
    #                 if line_count >= num_lines:
    #                     break
    #                 output += chunk.split('\n')[1]
    #             else:
    #                 output += chunk
    #     return output

    # def get_scalar(self, prompt, single_line=False, num_lines=0, model_obj=None):
    #     result = asyncio.run(self.get_scalar_async(prompt, single_line, num_lines, model_obj))
    #     return result
    
    # # def sync_chat(self):
    # #     try:
    # #         model_cnt = self.sync_all_voices()
    # # #         )
    
    def sync_models(self):
        try:
            from litellm import model_cost
            all_models = model_cost

            mode_map = {
                'chat': 'CHAT',
                # 'video_generation': 'VIDEO',
                'audio_transcription': 'TRANSCRIPTION',
                'embedding': 'EMBEDDING',
                'image_generation': 'IMAGE',
            }
            skip_subproviders = [
                'FAL_AI'
            ]
            # distinct_modes = set()
            apis = {}  # api_name_lower: {model_kind: {model_name: {}}}
            for model_name, model_data in all_models.items():
                api_name = model_data.get('litellm_provider', '')  # .lower()
                if api_name == '':
                    continue
                if api_name.upper() in skip_subproviders:
                    continue
                mode = model_data.get('mode', 'chat')
                if mode not in mode_map:
                    continue
                model_kind = mode_map[mode]
                # if ' ' in mode:  # patch bad data in json
                #     continue
                if api_name not in apis:
                    apis[api_name] = {}
                if model_kind not in apis[api_name]:
                    apis[api_name][model_kind] = {}
                apis[api_name][model_kind][model_name] = model_data
                # distinct_modes.add(model_data.get('mode', None))

            reset_table(
                table_name='apis',
                item_configs={
                    (('name', api_name.replace('_', ' ').title()),): {'litellm_prefix': api_name}
                    for api_name, _ in apis.items()
                },
                delete_existing=False,
            )

            api_ids = sql.get_results(f'SELECT json_extract(config, "$.litellm_prefix"), id FROM apis', return_type='dict')
            api_models = {}
            for api_name, model_kinds in apis.items():
                for mode in mode_map.values():
                    mode_models = model_kinds.get(mode, {})
                    for model_name, model_metadata in mode_models.items():
                        if model_name.startswith(f'{api_name}/'):
                            model_name = model_name[len(f'{api_name}/'):]
                        
                        # Replace `-` with space only if it's NOT between two digits
                        display_name = re.sub(r'(?<!\d)-(?!\d)', ' ', model_name)
                        display_name = display_name.replace('_', ' ').replace('/', ' / ').title()
                        # Replace all letters directly after a digit with lower case character
                        display_name = re.sub(r'\d([A-Za-z])', r'\1', display_name)

                        api_models[
                            ('name', display_name),
                            ('kind', mode),
                            ('api_id', api_ids[api_name]),
                            ('metadata', json.dumps(model_metadata)),
                        ] = {
                            'model_name': model_name,
                        }

            reset_table(
                table_name='models',
                item_configs=api_models,
                delete_existing=False,
            )

        except Exception as e:
            display_message(
                icon=QMessageBox.Critical,
                title="Error syncing models",
                message=f"An error occurred while syncing models: {e}"
            )
    
    # def reset_models(self):
    #     # retval = display_message_box(
    #     #     icon=QMessageBox.Warning,
    #     #     title="Sync models",
    #     #     text="Are you sure you want to sync LiteLLM models?",
    #     #     buttons=QMessageBox.Yes | QMessageBox.No,
    #     # )
    #     # if retval != QMessageBox.Yes:
    #     #     return

    #     try:
    #         from litellm import model_cost
    #         all_models = model_cost

    #         mode_map = {
    #             'chat': 'CHAT',
    #             # 'video_generation': 'VIDEO',
    #             'audio_transcription': 'TRANSCRIPTION',
    #             'embedding': 'EMBEDDING',
    #             'image_generation': 'IMAGE',
    #         }
    #         # distinct_modes = set()
    #         apis = {}  # api_name_lower: {model_kind: {model_name: {}}}
    #         for model_name, model_data in all_models.items():
    #             api_name = model_data.get('litellm_provider', '')  # .lower()
    #             if api_name == '':
    #                 continue
    #             mode = model_data.get('mode', 'chat')
    #             if mode not in mode_map:
    #                 continue
    #             model_kind = mode_map[mode]
    #             # if ' ' in mode:  # patch bad data in json
    #             #     continue
    #             if api_name not in apis:
    #                 apis[api_name] = {}
    #             if model_kind not in apis[api_name]:
    #                 apis[api_name][model_kind] = {}
    #             apis[api_name][model_kind][model_name] = model_data
    #             # distinct_modes.add(model_data.get('mode', None))
            
    #         reset_table(
    #             table_name='apis',
    #             delete_existing=False,
    #             item_configs={
    #                 (('name', api_name.replace('_', ' ').title()),): {'litellm_prefix': api_name}
    #                 for api_name, _ in apis.items()
    #             },
    #         )

    #         api_ids = sql.get_results(f'SELECT json_extract(config, "$.litellm_prefix"), id FROM apis', return_type='dict')
    #         api_models = {}
    #         for api_name, model_kinds in apis.items():
    #             for mode in mode_map.values():
    #                 mode_models = model_kinds.get(mode, {})
    #                 for model_name, model_metadata in mode_models.items():
    #                     if model_name.startswith(f'{api_name}/'):
    #                         model_name = model_name[len(f'{api_name}/'):]
                        
    #                     # Replace `-` with space only if it's NOT between two digits
    #                     display_name = re.sub(r'(?<!\d)-(?!\d)', ' ', model_name)
    #                     display_name = display_name.replace('_', ' ').replace('/', ' / ').title()
    #                     # Replace all letters directly after a digit with lower case character
    #                     display_name = re.sub(r'\d([A-Za-z])', r'\1', display_name)

    #                     api_models[
    #                         ('name', display_name),
    #                         ('kind', mode),
    #                         ('api_id', api_ids[api_name]),
    #                         ('metadata', json.dumps(model_metadata)),
    #                     ] = {
    #                         'model_name': model_name,
    #                     }

    #         reset_table(
    #             table_name='models',
    #             delete_existing=False,
    #             item_configs=api_models,
    #         )

    #         # openai_api_id = sql.get_scalar("SELECT id FROM apis WHERE LOWER(name) = 'openai'")

    #         # # add sora 2
    #         # sora_2_metadata = {
    #         #     "max_input_tokens": 1024,  # todo check
    #         #     "max_tokens": 1024,  # todo check
    #         #     "mode": "video_generation",
    #         #     "output_cost_per_second": 0.10,
    #         #     "supported_modalities": [
    #         #         "text",
    #         #         "image",
    #         #     ],
    #         #     "supported_output_modalities": [
    #         #         "video"
    #         #     ]
    #         # }
    #         # sql.execute("INSERT INTO models (name, kind, api_id, config) VALUES ('Sora 2', 'VIDEO', ?, ?)", (openai_api_id, json.dumps({"model_name": "sora-2"})))
    #         # sql.execute("INSERT INTO models (name, kind, api_id, config) VALUES ('Sora 2 Pro', 'VIDEO', ?, ?)", (openai_api_id, json.dumps({"model_name": "sora-2-pro"})))
    #         # #     item_configs={
    #         # #         (("id", 22), ("name", "AI21")): {},
    #         # #         (("id", 17), ("name", "AWS Bedrock")): {"litellm_prefix": "bedrock"},
    #         # #         (("id", 16), ("name", "AWS Sagemaker")): {"litellm_prefix": "sagemaker"},
    #         # #         (("id", 5), ("name", "AWSPolly")): {},
    #         # #         (("id", 27), ("name", "Aleph Alpha")): {},
    #         # #         (("id", 15), ("name", "Anthropic")): {},
    #         # #         (("id", 18), ("name", "Anyscale")): {"litellm_prefix": "anyscale"},
    #         # #         (("id", 10), ("name", "Azure OpenAI")): {"litellm_prefix": "azure"},
    #         # #         (("id", 28), ("name", "Baseten")): {"litellm_prefix": "baseten"},
    #         # #         (("id", 34), ("name", "Cloudflare")): {"litellm_prefix": "cloudflare"},
    #         # #         (("id", 25), ("name", "Cohere")): {},
    #         # #         (("id", 30), ("name", "Custom API Server")): {},
    #         # #         (("id", 21), ("name", "DeepInfra")): {"litellm_prefix": "deepinfra"},
    #         # #         (("id", 39), ("name", "DeepSeek")): {"litellm_prefix": "deepseek"},
    #         # #         (("id", 3), ("name", "ElevenLabs")): {},
    #         # #         (("id", 1), ("name", "FakeYou")): {},
    #         # #         (("id", 36), ("name", "Google AI studio")): {"litellm_prefix": "google"},
    #         # #         (("id", 38), ("name", "Github")): {"litellm_prefix": "github"},
    #         # #         (("id", 33), ("name", "Groq")): {"litellm_prefix": "groq"},
    #         # #         (("id", 11), ("name", "Huggingface")): {"litellm_prefix": "huggingface"},
    #         # #         (("id", 32), ("name", "Mistral")): {"litellm_prefix": "mistral"},
    #         # #         (("id", 23), ("name", "NLP Cloud")): {},
    #         # #         (("id", 37), ("name", "Nvidia NIM")): {"litellm_prefix": "nvidia_nim"},
    #         # #         (("id", 12), ("name", "Ollama")): {"litellm_prefix": "ollama"},
    #         # #         (("id", 4), ("name", "OpenAI")): {},
    #         # #         (("id", 29), ("name", "OpenRouter")): {"litellm_prefix": "openrouter"},
    #         # #         (("id", 14), ("name", "PaLM API Google")): {"litellm_prefix": "palm"},
    #         # #         (("id", 19), ("name", "Perplexity AI")): {"litellm_prefix": "perplexity"},
    #         # #         (("id", 31), ("name", "Petals")): {"litellm_prefix": "petals"},
    #         # #         (("id", 8), ("name", "Replicate")): {"litellm_prefix": "replicate"},
    #         # #         (("id", 26), ("name", "Together AI")): {"litellm_prefix": "together_ai"},
    #         # #         (("id", 2), ("name", "Uberduck")): {},
    #         # #         (("id", 20), ("name", "VLLM")): {"litellm_prefix": "vllm"},
    #         # #         (("id", 13), ("name", "VertexAI Google")): {"litellm_prefix": "vertex_ai"},
    #         # #         (("id", 35), ("name", "Voyage")): {"litellm_prefix": "voyage"},
    #         # #         (("id", 40), ("name", "xAI")): {},
    #         # #         # (("id", 41), ("name", "Google AI Studio")): {"litellm_prefix": "gemini"},
    #         # #     }
    #         # # )
    #         # # )

    #         # display_message_box(
    #         #     icon=QMessageBox.Information,
    #         #     title="Success",
    #         #     text=f"Synced {model_cnt} voices",  # and {folder_cnt} folders."
    #         # )
    #     except Exception as e:
    #         display_message(
    #             icon=QMessageBox.Critical,
    #             title="Error syncing models",
    #             message=f"An error occurred while syncing models: {e}"
    #         )

    # class ChatConfig(ConfigFields):
    #     def __init__(self, parent):
    #         super().__init__(parent=parent)
    #         self.label_width = 125
    #         self.schema = [
    #             {
    #                 'text': 'Api Base',
    #                 'type': str,
    #                 'label_width': 150,
    #                 'width': 265,
    #                 'has_toggle': True,
    #                 'tooltip': 'The base URL for the API. This will be used for all models under this API',
    #                 'default': '',
    #             },
    #             {
    #                 'text': 'Litellm prefix',
    #                 'type': str,
    #                 'label_width': 150,
    #                 'width': 118,
    #                 'has_toggle': True,
    #                 'tooltip': 'The API provider prefix to be prepended to all model names under this API',
    #                 'row_key': 'F',
    #                 'default': '',
    #             },
    #             {
    #                 'text': 'Custom provider',
    #                 'type': str,
    #                 'label_width': 140,
    #                 'width': 118,
    #                 'has_toggle': True,
    #                 'tooltip': 'The custom provider for LiteLLM. Usually not needed.',
    #                 'row_key': 'F',
    #                 'default': '',
    #             },
    #             {
    #                 'text': 'Temperature',
    #                 'type': float,
    #                 'label_width': 150,
    #                 'has_toggle': True,
    #                 'minimum': 0.0,
    #                 'maximum': 1.0,
    #                 'step': 0.05,
    #                 'tooltip': 'When enabled, this will be the default temperature for all models under this API',
    #                 'row_key': 'A',
    #                 'default': 0.6,
    #             },
    #             {
    #                 'text': 'API version',
    #                 'type': str,
    #                 'label_width': 140,
    #                 'width': 118,
    #                 'has_toggle': True,
    #                 'row_key': 'A',
    #                 'tooltip': 'The api version passed to LiteLLM. Usually not needed.',
    #                 'default': '',
    #             },
    #             {
    #                 'text': 'Top P',
    #                 'type': float,
    #                 'label_width': 150,
    #                 'has_toggle': True,
    #                 'minimum': 0.0,
    #                 'maximum': 1.0,
    #                 'step': 0.05,
    #                 'tooltip': 'When enabled, this will be the default `Top P` for all models under this API',
    #                 'row_key': 'B',
    #                 'default': 1.0,
    #             },
    #             {
    #                 'text': 'Frequency penalty',
    #                 'type': float,
    #                 'has_toggle': True,
    #                 'label_width': 140,
    #                 'minimum': -2.0,
    #                 'maximum': 2.0,
    #                 'step': 0.2,
    #                 'row_key': 'B',
    #                 'default': 0.0,
    #             },
    #             {
    #                 'text': 'Max tokens',
    #                 'type': int,
    #                 'has_toggle': True,
    #                 'label_width': 150,
    #                 'minimum': 1,
    #                 'maximum': 999999,
    #                 'step': 1,
    #                 'row_key': 'D',
    #                 'tooltip': 'When enabled, this will be the default `Max tokens` for all models under this API',
    #                 'default': 100,
    #             },
    #             {
    #                 'text': 'Presence penalty',
    #                 'type': float,
    #                 'has_toggle': True,
    #                 'label_width': 140,
    #                 'minimum': -2.0,
    #                 'maximum': 2.0,
    #                 'step': 0.2,
    #                 'row_key': 'D',
    #                 'default': 0.0,
    #             },
    #         ]

    class ChatModelParameters(ConfigFields):
        def __init__(self, parent):
            super().__init__(parent=parent)
            self.parent = parent
            self.schema = [
                {
                    'text': 'Model name',
                    'type': str,
                    'label_width': 125,
                    'width': 265,
                    # 'stretch_x': True,
                    'tooltip': 'The name of the model to send to the API',
                    'default': '',
                },
                {
                    'text': 'Temperature',
                    'type': float,
                    'has_toggle': True,
                    'label_width': 125,
                    'minimum': 0.0,
                    'maximum': 1.0,
                    'step': 0.05,
                    'default': 0.6,
                    'row_key': 'A',
                },
                {
                    'text': 'Presence penalty',
                    'type': float,
                    'has_toggle': True,
                    'label_width': 140,
                    'minimum': -2.0,
                    'maximum': 2.0,
                    'step': 0.2,
                    'default': 0.0,
                    'row_key': 'A',
                },
                {
                    'text': 'Top P',
                    'type': float,
                    'has_toggle': True,
                    'label_width': 125,
                    'minimum': 0.0,
                    'maximum': 1.0,
                    'step': 0.05,
                    'default': 1.0,
                    'row_key': 'B',
                },
                {
                    'text': 'Frequency penalty',
                    'type': float,
                    'has_toggle': True,
                    'label_width': 140,
                    'minimum': -2.0,
                    'maximum': 2.0,
                    'step': 0.2,
                    'default': 0.0,
                    'row_key': 'B',
                },
                {
                    'text': 'Max tokens',
                    'type': int,
                    'has_toggle': True,
                    'label_width': 125,
                    'minimum': 1,
                    'maximum': 999999,
                    'step': 1,
                    'default': 100,
                },
            ]

    class V2VModelParameters(ConfigFields):
        def __init__(self, parent):
            super().__init__(parent=parent)
            self.parent = parent
            self.schema = [
                {
                    'text': 'Model name',
                    'type': str,
                    'label_width': 125,
                    'width': 265,
                    # 'stretch_x': True,
                    'tooltip': 'The name of the model to send to the API',
                    'default': '',
                },
                {
                    'text': 'Voice',
                    'type': ('Alloy',),
                    'label_width': 125,
                    'default': 'Alloy',
                    # 'row_key': 'A',
                },
                {
                    'text': 'Turn detection',
                    'type': bool,
                    'default': True,
                    'row_key': 'A',
                },
                {
                    'text': 'Temperature',
                    'type': float,
                    'has_toggle': True,
                    'label_width': 125,
                    'minimum': 0.0,
                    'maximum': 1.0,
                    'step': 0.05,
                    'default': 0.6,
                },
            ]
