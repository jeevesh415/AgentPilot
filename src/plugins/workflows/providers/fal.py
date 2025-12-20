
import json
import asyncio
import re
import time
from typing import Any

from PySide6.QtWidgets import QMessageBox
import requests

from gui import system
from utils.reset import reset_table
from utils import sql
from utils.helpers import display_message, network_connected, convert_model_json_to_obj
from plugins.workflows.managers.providers import Provider


class FalProvider(Provider):
    from gui.widgets.config_fields import ConfigFields
    def __init__(self, parent):
        super().__init__(parent=parent)
        
    def get_model_parameters(self, model_obj, incl_api_data=True):
        raise NotImplementedError("Not implemented")
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

    async def run_model(self, model_obj, **kwargs):
        raise NotImplementedError("Not implemented")
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

    def sync_models(self):

        def resolve_schema(schema):
            # Helper function to resolve complex JSON schemas into a single type definition
            """
            Returns a tuple: (resolved_schema_dict, is_nullable)
            Recurses through anyOf/oneOf/allOf to find the 'dominant' type for the UI.
            """
            is_nullable = False
            
            # 1. Handle anyOf / oneOf (Choice structures)
            # Logic: Check if 'null' is an option. Then pick the first non-null schema.
            if 'anyOf' in schema or 'oneOf' in schema:
                choices = schema.get('anyOf') or schema.get('oneOf')
                valid_options = []
                
                for choice in choices:
                    if choice.get('type') == 'null':
                        is_nullable = True
                    else:
                        valid_options.append(choice)
                
                if valid_options:
                    # Heuristic: We pick the first valid option to determine the UI element.
                    # (e.g. if it's String OR Int, we render a String field)
                    chosen_schema, inner_nullable = resolve_schema(valid_options[0])
                    # Propagate nullability
                    return chosen_schema, (is_nullable or inner_nullable)
                
                # If only null is available (weird, but possible)
                return {'type': 'null'}, True

            # 2. Handle allOf (Combination structures)
            # Logic: Merge properties from all schemas.
            elif 'allOf' in schema:
                merged_schema = {}
                for sub_schema in schema['allOf']:
                    resolved_sub, _ = resolve_schema(sub_schema)
                    merged_schema.update(resolved_sub)
                return merged_schema, False

            # 3. Handle Standard Types
            return schema, False

        reset_table(
            table_name='apis',
            item_configs={
                (('name', 'Fal AI'),): {}
            },
            delete_existing=False,
        )
        api_id = sql.get_scalar("SELECT id FROM apis WHERE LOWER(name) = 'fal ai'")
        sql.execute("UPDATE apis SET api_key = '$FAL_API_KEY' WHERE id = ?", (api_id,))

        mode_maps = {
            'image': 'IMAGE',
            'video': 'VIDEO',
            'speech': 'AUDIO',
            'audio': 'AUDIO',
            '3d': '3D',
        }
        
        all_models = {}
        try:
            next_cursor = None
            while True:
                time.sleep(5)
                response = requests.get(
                    'https://api.fal.ai/v1/models',
                    params={
                        "expand":"openapi-3.0",
                        "cursor": next_cursor,
                    }
                )
                is_error = response.status_code != 200
                if is_error:
                    raise Exception(f"Error syncing models: {response.text}")

                response = response.json()
                for model in response.get('models', []):
                    model_name = model['endpoint_id']
                    metadata = model.get('metadata', {})
                    category = metadata.get('category', None)
                    cat_end = category.split('-')[-1].lower() if '-' in category else None
                    mode = mode_maps.get(cat_end, None)
                    if not mode:
                        print(f"Skipping model {model_name} because it has no valid mode")
                        continue
                    if 'openapi' not in model:
                        print(f"Skipping model {model_name} because it has no openapi schema")
                        continue
                    if 'components' not in model['openapi']:
                        print(f"Skipping model {model_name} because it's openapi schema has no components")
                        continue
                    
                    openapi_schema = model['openapi']['components']['schemas']
                    
                    input_schema, output_schema = [], []
                    for schema_name, schema_data in openapi_schema.items():
                        if schema_name.endswith('Input'):  # todo how else to identify input/output schemas?
                            properties = schema_data.get('properties', {})
                            property_order = schema_data.get('x-fal-order-properties', [])
                            ordered_properties = {
                                **{k: properties[k] for k in property_order if k in properties},
                                **properties
                            }
                            type_map = {
                                'string': 'text',
                                'boolean': 'boolean',
                                'integer': 'integer',
                                'number': 'float',
                            }
                            
                            for property_name, raw_property_data in ordered_properties.items():
                                # Resolve the schema (handles anyOf, allOf, oneOf)
                                property_data, allow_none = resolve_schema(raw_property_data)
                                
                                # Fallback for default handling if it was hidden inside the complex structure
                                default_val = raw_property_data.get('default', property_data.get('default', None))

                                fal_property_type = property_data.get('type')

                                # Handle missing types (defaults to string if unknown)
                                if not fal_property_type:
                                    # Sometimes schemas are empty {}, effectively "any". Treat as text.
                                    fal_property_type = 'string'

                                type_map = {
                                    'string': 'text',
                                    'boolean': 'boolean',
                                    'integer': 'integer',
                                    'number': 'float',
                                    'array': 'text', # Map arrays to text so user can input JSON "[1,2]"
                                    'object': 'text', # Map objects to text so user can input JSON "{...}"
                                }

                                if fal_property_type not in type_map:
                                    print(f"Warning: Unknown type '{fal_property_type}' for {property_name}. Defaulting to text.")
                                    property_type = 'text'
                                else:
                                    property_type = type_map[fal_property_type]

                                # Handle Enum
                                enum = property_data.get('enum', None)
                                if enum:
                                    # Convert enum to tuple for your GUI system
                                    property_type = tuple(enum)

                                new_property = {
                                    'key': property_name,
                                    'text': raw_property_data.get('title', property_name), # Use original title
                                    'type': property_type,
                                    'default': default_val,
                                    'optional': allow_none, # Store this if your GUI needs to know it's optional
                                }
                                
                                # Copy tooltip from original or resolved
                                desc = raw_property_data.get('description') or property_data.get('description')
                                if desc:
                                    new_property['tooltip'] = desc

                                # UI Formatting logic
                                if property_type == 'text':
                                    is_prompt = 'prompt' in property_name.lower() or 'prompt' in (desc or '').lower()
                                    if is_prompt:
                                        new_property['num_lines'] = 2
                                        new_property['stretch_x'] = True
                                        new_property['stretch_y'] = True
                                        new_property['label_position'] = 'top'

                                elif property_type == 'integer' or property_type == 'float':
                                    default_maximum = 2147483647 if property_type == 'integer' else 3.402823466e+38
                                    new_property['minimum'] = property_data.get('minimum', 0)
                                    new_property['maximum'] = property_data.get('maximum', default_maximum)

                                input_schema.append(new_property)

                        elif schema_name.endswith('Output'):
                            output_schema = schema_data

                    if not (input_schema and output_schema):
                        print(f"Skipping model {model_name} because it has no input/output schemas")
                        continue

                    metadata['input_schema'] = input_schema
                    metadata['output_schema'] = output_schema

                    all_models[
                        ('name', metadata.get('display_name', model_name)),
                        ('kind', mode),
                        ('api_id', api_id),
                        ('metadata', json.dumps(metadata)),
                    ] = {
                        'model_name': model_name,
                    }

                if not response.get('has_more', False):
                    break
                next_cursor = response.get('next_cursor', None)

        except Exception as e:
            display_message(
                icon=QMessageBox.Critical,
                title="Error syncing models",
                message=f"An error occurred while syncing models: {e}"
            )
            return

        reset_table(
            table_name='models',
            item_configs=all_models,
            delete_existing=False,
        )