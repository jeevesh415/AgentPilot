"""Inhouse Provider Module.
"""  # unchecked

import json
import os
import asyncio
import re
from typing import List, Dict, Any, Optional

from PySide6.QtWidgets import QMessageBox
from openai import AsyncOpenAI
# import instructor
import litellm
from litellm import acompletion, completion
from pydantic import create_model

from gui import system
from utils.reset import reset_table
from utils import sql
from utils.helpers import display_message_box, network_connected, convert_model_json_to_obj, convert_to_safe_case
from plugins.workflows.managers.providers import Provider

litellm.log_level = 'ERROR'


class InhouseProvider(Provider):
    from gui.widgets.config_fields import ConfigFields
    def __init__(self, parent):
        super().__init__(parent=parent)

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
        kind, model_name = model_obj.get('kind'), model_obj.get('model_name')
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

        model_config = self.models.get((kind, model_name), {})
        cleaned_model_config = {k: v for k, v in model_config.items() if k in accepted_keys}
        return cleaned_model_config

    async def run_model_sora_2(self, model_obj, **kwargs):
        api_key = system.manager.apis.get('Openai').get('api_key', '')
        client = AsyncOpenAI(api_key=api_key)
        video = await client.videos.create_and_poll(
            model=model_obj.get('model_name', ''),
            prompt="A video of a cat on a motorcycle",
        )

        if video.status == "completed":
            print("Video successfully completed: ", video)
            # yield video
        else:
            print("Video creation failed. Status: ", video.status)
            # yield video
    
    async def get_gemini_model_stream(self, model_obj, **kwargs):
        model_obj = convert_model_json_to_obj(model_obj)
        model_name = model_obj.get('model_name', None)
        if not model_name:
            raise ValueError("Model name is required")

        text = kwargs['text']

        import time
        from google import genai
        from google.genai import types

        api_key = model_obj['model_params']['api_key']
        client = genai.Client(api_key=api_key)

        operation = client.models.generate_videos(
            model=model_name,
            prompt=text,
        )

        print("Waiting for video generation to complete...")
        await asyncio.sleep(30)
        # Poll the operation status until the video is ready.
        while not operation.done:
            print("Waiting for video generation to complete...")
            await asyncio.sleep(3)
            operation = client.operations.get(operation)

        # Download the generated video.
        generated_video = operation.response.generated_videos[0]
        client.files.download(file=generated_video.video)
        video_bytes = generated_video.video.video_bytes
        print("Generated video completed")

        # Return a generator that yields the entire video bytes as a single chunk
        def stream_video_bytes():
            yield video_bytes
        return stream_video_bytes()

    async def run_model(self, model_obj, **kwargs):
        model_obj = convert_model_json_to_obj(model_obj)
        model_s_params = system.manager.models.get_model(model_obj)
        model_obj['model_params'] = {**model_obj.get('model_params', {}), **model_s_params}
        accepted_keys = [
            # 'temperature',
            # 'top_p',
            # 'presence_penalty',
            # 'frequency_penalty',
            # 'max_tokens',
            'api_key',
            'api_base',
            'api_version',
            'custom_provider',
        ]
        model_obj['model_params'] = {k: v for k, v in model_obj['model_params'].items() if k in accepted_keys}
        # # model_params = model_obj.get('model_params', {})
        # text = kwargs.get('text', '')
        # filepath = kwargs.get('filepath', None)
        oai_models = ['sora-2', 'sora-2-pro']
        gemini_models = ['veo-3.0-fast-generate-preview', 'veo-3.0-generate-preview']
        
        model_name = model_obj['model_name']
        if model_name in oai_models:
            pass

        elif model_name in gemini_models:
            return await self.get_gemini_model_stream(model_obj, **kwargs)

        # # if not all(msg['content'] for msg in messages):
        # #     pass

        # ex = None
        # for i in range(5):
        #     try:
        #         kwargs = dict(
        #             model=model_name,
        #             messages=messages,
        #             stream=stream,
        #             request_timeout=100,
        #             **(model_params or {}),
        #         )
        #         if tools:
        #             kwargs['tools'] = tools
        #             kwargs['tool_choice'] = "auto"

        #         if next(iter(messages), {}).get('role') != 'user':
        #             pass

        #         # return await acompletion(**kwargs)
        #     except Exception as e:
        #         if not network_connected():
        #             ex = ConnectionError('No network connection.')
        #             break
        #         ex = e
        #         await asyncio.sleep(0.3 * i)
        # raise ex

    # def reset_models(self):
    #     openai_api_id = sql.get_scalar("SELECT id FROM apis WHERE LOWER(name) = 'openai'")
    #     gemini_api_id = sql.get_scalar("SELECT id FROM apis WHERE LOWER(name) = 'gemini'")

    #     # # add sora 2
    #     # sora_2_metadata = {
    #     #     "max_input_tokens": 1024,  # todo check
    #     #     "max_tokens": 1024,  # todo check
    #     #     "mode": "video_generation",
    #     #     "output_cost_per_second": 0.10,
    #     #     "supported_modalities": [
    #     #         "text",
    #     #         "image",
    #     #     ],
    #     #     "supported_output_modalities": [
    #     #         "video"
    #     #     ]
    #     # }
    #     sql.execute("INSERT INTO models (name, kind, api_id, config, provider_plugin) VALUES ('Sora 2', 'VIDEO', ?, ?, 'inhouse')", (openai_api_id, json.dumps({"model_name": "sora-2"})))
    #     sql.execute("INSERT INTO models (name, kind, api_id, config, provider_plugin) VALUES ('Sora 2 Pro', 'VIDEO', ?, ?, 'inhouse')", (openai_api_id, json.dumps({"model_name": "sora-2-pro"})))

    #     sql.execute("INSERT INTO models (name, kind, api_id, config, provider_plugin) VALUES ('Veo 3 Fast', 'VIDEO', ?, ?, 'inhouse')", (gemini_api_id, json.dumps({"model_name": "veo-3.0-fast-generate-preview"})))
    #     sql.execute("INSERT INTO models (name, kind, api_id, config, provider_plugin) VALUES ('Veo 3', 'VIDEO', ?, ?, 'inhouse')", (gemini_api_id, json.dumps({"model_name": "veo-3.0-generate-preview"})))

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
