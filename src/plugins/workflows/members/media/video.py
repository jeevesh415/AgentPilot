

import json
from plugins.workflows.members import Member
from gui import system
from utils import sql
from utils.helpers import convert_model_json_to_obj, set_module_type


@set_module_type(module_type='Members', settings='video_settings')
class Video(Member):
    default_role = 'video'
    default_avatar = ':/resources/icon-video.png'
    default_name = 'Video'
    workflow_insert_mode = 'single'
    OUTPUT = 'VIDEO'

    @property
    def INPUTS(self):
        return {
            'CONFIG': {
                'text': str,
            },
        }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def get_content(self, run_sub_blocks=True):  # todo dupe code 777
        # We have to redefine this here because we inherit from LlmMember
        content = self.config.get('text', '')

        if run_sub_blocks:
            content = await system.manager.blocks.format_string(content, ref_workflow=self.workflow)

        return content

    async def receive(self):
        """The entry response method for the member."""
        # import wave
        model_json = self.config.get('model', None)  # system.manager.config.get('system.default_voice_model', 'mistral/mistral-large-latest'))
        if not model_json:
            raise ValueError("Model is required")
        model_obj = convert_model_json_to_obj(model_json)
        text = await self.get_content()
        filepath = self.text_to_filepath(text)

        # Buffer all chunks into a single audio stream
        video_buffer = b""

        if self.config.get('use_cache', False):
            # model id is in `log`['model']['model_name']
            last_generated_path = sql.get_scalar("""
                SELECT json_extract(msg, '$.filepath')
                FROM contexts_messages
                WHERE role = 'video' AND 
                    json_extract(log, '$.text') = ? AND 
                    json_extract(log, '$.model.model_name') = ?
                ORDER BY id DESC
                LIMIT 1""",
                (text, model_obj.get('model_name'))
            )
            if last_generated_path:
                try:
                    with open(last_generated_path, 'rb') as f:
                        video_buffer = f.read()
                    filepath = last_generated_path

                except Exception:
                    pass

        if not video_buffer:
            stream = await system.manager.models.run_model(
                model_obj=model_obj,
                text=text,
                filepath=filepath,
            )
            for chunk in stream:
                video_buffer += chunk
            pass
        #     # Save the video to a MP4 file
        with open(filepath, 'wb') as f:
            f.write(video_buffer)
            
        if 'api_key' in model_obj['model_params']:
            model_obj['model_params'].pop('api_key')
        logging_obj = {
            'id': 0,
            'context_id': self.workflow.context_id,
            'member_id': self.full_member_id(),
            'model': model_obj,
            'text': text,
        }

        # if self.config.get('play_audio', True):
        #     blocking = self.config.get('wait_until_finished', False)
        #     wait_percent = self.config.get('wait_percent', 0.0)
        #     play_file(filepath, blocking=blocking, wait_percent=wait_percent)

        msg_json = {
            'filepath': filepath,
        }
        msg_content = json.dumps(msg_json)
        self.workflow.save_message(self.default_role, msg_content, self.full_member_id(), logging_obj)

        yield 'SYS', 'SKIP'

    # async def receive(self):
    #     """The entry response method for the member."""
    #     yield self.default_role, 'TODO'
