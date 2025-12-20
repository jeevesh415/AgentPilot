import inspect
import json
import os
import shutil
import sys

from PySide6.QtWidgets import QMessageBox

from gui import system
from utils import sql
from utils.helpers import display_message_box, get_id_from_folder_path, hash_config


def reset_application(force=False, preserve_audio_msgs=False, bootstrap=True):  # todo temp preserve_audio_msgs
    if not force:
        retval = display_message_box(
            icon=QMessageBox.Warning,
            text="Are you sure you want to reset the database and config? This will permanently delete everything.",
            title="Reset Database",
            buttons=QMessageBox.Ok | QMessageBox.Cancel,
        )
        if retval != QMessageBox.Ok:
            return

    db_path = sql.get_db_path()
    if force:
        db_name = os.path.basename(db_path)
        if db_name == 'data.db':  # protection
            raise Exception("Cannot force reset the main database.")

    # # Wait for any running threads to complete before resetting
    # from PySide6.QtCore import QThreadPool
    # threadpool = QThreadPool.globalInstance()
    # if threadpool:
    #     threadpool.waitForDone(5000)  # Wait up to 5 seconds for threads to finish

    backup_filepath = db_path + '.backup'
    counter = 1
    while os.path.isfile(backup_filepath):
        backup_filepath = db_path + f'.backup{counter}'
        counter += 1

    shutil.copyfile(db_path, backup_filepath)

    reset_table(table_name='pypi_packages')

    # ############################# FOLDERS ############################### #
    reset_folders()

    reset_models(preserve_keys=False)

    reset_table(table_name='addons')
    reset_table(table_name='blocks')
    reset_table(table_name='entities')
    reset_table(table_name='tools')
    reset_table(table_name='modules')
    reset_table(table_name='vectordbs')
    reset_table(
        table_name='environments',
        item_configs={
            "Local": {
                "env_vars.data": [],
                "sandbox_type": "",
                "venv": "default"
            },
        }
    )



    # ############################# ROLES ############################### #

    reset_table(
        table_name='roles',
        item_configs={
            "user": {
                "bubble_bg_color": "#ff222332",
                "bubble_text_color": "#ffd1d1d1",
                "bubble_image_size": 25,
                "module": "user_bubble",
            },
            "assistant": {
                "bubble_bg_color": "#ff171822",
                "bubble_text_color": "#ffb2bbcf",
                "bubble_image_size": 25,
                "module": "assistant_bubble",
            },
            "system": {
                "bubble_bg_color": "#00ffffff",
                "bubble_text_color": "#ff949494",
                "bubble_image_size": 25,
            },
            "audio": {
                "bubble_bg_color": "#00ffffff",
                "bubble_text_color": "#ff949494",
                "bubble_image_size": 25,
                "module": "audio_bubble",
            },
            "code": {
                "bubble_bg_color": "#00ffffff",
                "bubble_text_color": "#ff949494",
                "bubble_image_size": 25,
                "module": "code_bubble",
            },
            "tool": {
                "bubble_bg_color": "#00ffffff",
                "bubble_text_color": "#ffb2bbcf",
                "bubble_image_size": 25,
                "module": "tool_bubble",
            },
            "output": {
                "bubble_bg_color": "#00ffffff",
                "bubble_text_color": "#ff818365",
                "bubble_image_size": 25,
            },
            "result": {
                "bubble_bg_color": "#00ffffff",
                "bubble_text_color": "#ff818365",
                "bubble_image_size": 25,
                "module": "result_bubble",
            },
            "image": {
                "bubble_bg_color": "#00000000",
                "bubble_text_color": "#ff949494",
                "bubble_image_size": 25,
                "module": "image_bubble",
            },
            "instruction": {
                "bubble_bg_color": "#00ffffff",
                "bubble_text_color": "#ff818365",
                "bubble_image_size": 25,
            },
        }
    )

    # ############################# THEMES ############################### #

    reset_table(
        table_name='themes',
        item_configs={
            "Dark": {
                "assistant": {
                    "bubble_bg_color": "#ff212122",
                    "bubble_text_color": "#ffb2bbcf"
                },
                "code": {
                    "bubble_bg_color": "#003b3b3b",
                    "bubble_text_color": "#ff949494"
                },
                "display": {
                    "primary_color": "#ff1b1a1b",
                    "secondary_color": "#ff292629",
                    "text_color": "#ffcacdd5"
                },
                "user": {
                    "bubble_bg_color": "#ff2e2e2e",
                    "bubble_text_color": "#ffd1d1d1"
                },
            },
            "Light": {
                "assistant": {
                    "bubble_bg_color": "#ffd0d0d0",
                    "bubble_text_color": "#ff4d546d"
                },
                "code": {
                    "bubble_bg_color": "#003b3b3b",
                    "bubble_text_color": "#ff949494"
                },
                "display": {
                    "primary_color": "#ffe2e2e2",
                    "secondary_color": "#ffd6d6d6",
                    "text_color": "#ff413d48"
                },
                "user": {
                    "bubble_bg_color": "#ffcbcbd1",
                    "bubble_text_color": "#ff413d48"
                },
            },
            "Dark Blue": {
                "assistant": {
                    "bubble_bg_color": "#ff171822",
                    "bubble_text_color": "#ffb2bbcf"
                },
                "code": {
                    "bubble_bg_color": "#003b3b3b",
                    "bubble_text_color": "#ff949494"
                },
                "display": {
                    "primary_color": "#ff11121b",
                    "secondary_color": "#ff222332",
                    "text_color": "#ffb0bbd5"
                },
                "user": {
                    "bubble_bg_color": "#ff222332",
                    "bubble_text_color": "#ffd1d1d1"
                },
            },
        }
    )

    # ############################# APP CONFIG ############################### #

    app_settings = {
        # "display.bubble_avatar_position": "Top",
        "display.bubble_spacing": 7,
        "display.primary_color": "#ff11121b",
        "display.secondary_color": "#ff222332",
        "display.show_bubble_avatar": "In Group",
        "display.show_bubble_name": "In Group",
        "display.show_waiting_bar": "In Group",
        "display.text_color": "#ffb0bbd5",
        "display.text_font": "",
        "display.text_size": 15,
        "display.window_margin": 6,
        # "display.pinned_pages": ['Blocks', 'Tools'],
        "system.always_on_top": True,
        # "system.auto_complete": True,
        "system.default_chat_model": "claude-3-5-sonnet-20240620",
        "system.auto_title": True,
        "system.auto_title_model": "claude-3-5-sonnet-20240620",
        "system.auto_title_prompt": "Write only a brief and concise title for a chat that begins with the following message:\n\n```{user_msg}```",
        "system.dev_mode": False,
        "system.language": "English",
        "system.telemetry": True,
        "system.voice_input_method": "None"
    }

    sql.execute("UPDATE settings SET value = '' WHERE `field` = 'my_uuid'")
    # tos_val = 1 if accept_tos else 0
    # sql.execute("UPDATE settings SET value = ? WHERE `field` = 'accepted_tos'", (str(tos_val),))
    sql.execute("UPDATE settings SET value = '0' WHERE `field` = 'accepted_tos'")
    sql.execute("UPDATE settings SET value = ? WHERE `field` = 'app_config'", (json.dumps(app_settings),))
    sql.execute("UPDATE settings SET value = json(?) WHERE `field` = 'pinned_pages'", (json.dumps(['blocks', 'tools']),))
    sql.execute("UPDATE settings SET value = json(?) WHERE `field` = 'enhancement_blocks'",
                (json.dumps({
                    'main_input': ['2637891c-69ba-4f41-bc54-c4c26f32bc66']
                }),))

    audio_msgs = None
    if preserve_audio_msgs:
        audio_msgs = sql.get_results("""
            SELECT msg, log
            FROM contexts_messages 
            WHERE role = 'audio'
        """, return_type='rows')

    sql.execute('DELETE FROM contexts_messages')
    reset_table(table_name='contexts')
    sql.execute('DELETE FROM logs')
    sql.execute('DELETE FROM folders WHERE locked != 1')
    sql.execute('DELETE FROM pypi_packages')
    if audio_msgs:
        values_list = []
        placeholders = []
        for msg, log in audio_msgs:
            values_list.extend(('', 0, msg, log, 'audio'))
            placeholders.append("(?, ?, ?, ?, ?)")

        if placeholders:
            query = f"""
                INSERT INTO contexts_messages (member_id, context_id, msg, log, role)
                VALUES {', '.join(placeholders)}
            """
            sql.execute(query, values_list)

    keep_tables = [
        'addons',
        'apis',
        'blocks',
        'contexts',
        'contexts_messages',
        'entities',
        'environments',
        'folders',
        'logs',
        'models',
        'modules',
        'pypi_packages',
        'roles',
        'settings',
        'themes',
        'tools',
        'tasks',
        'vectordbs',
    ]
    all_tables = sql.get_results("SELECT name FROM sqlite_master WHERE type='table'", return_type='list')
    for table in all_tables:
        if table == 'sqlite_sequence':
            continue
        if table not in keep_tables:
            sql.execute(f"DROP TABLE {table}")

    if bootstrap:
        bootstrap()

    sql.execute('VACUUM')

    if not force:
        display_message_box(
            icon=QMessageBox.Information,
            title="Reset complete",
            text="The app has been reset. Please restart the app to apply the changes."
        )
        sys.exit(0)


def bootstrap():
    bootstrap_entities()
    # bootstrap_modules()
    # pass


def bootstrap_entities():
    from pathlib import Path
    
    # Get the baked directory path
    baked_dir = Path(__file__).parent / 'baked'
    
    if not baked_dir.exists():
        print(f"Baked directory not found: {baked_dir}")
        return
    
    # Iterate through each folder (table name) in the baked directory
    for table_folder in baked_dir.iterdir():
        if not table_folder.is_dir():
            continue
            
        table_name = table_folder.name
        
        mgr = getattr(system.manager, table_name, None)
        if not mgr:
            print(f"Manager for {table_name} not found")
            continue

        from utils.filesystem import get_all_baked_items
        baked_items = get_all_baked_items(table_name)
        
        for _, item_config in baked_items.items():
            kwargs = {
                'name': item_config['name'],
                'uuid': item_config['uuid'],
                'config': item_config['config'],
                'baked': 1,
            }
            folder_path = item_config.get('folder_path', None)
            folder_id = get_id_from_folder_path(folder_path)
            if folder_id:
                kwargs['folder_id'] = folder_id
            mgr.add(**kwargs)


def split_module_source_description(module_source):
    """Split module source into description and data, description is the triple `"` block at the top of the file"""

    description = ""
    if module_source.strip().startswith('"""'):
        description = module_source.split('"""')[1].strip()
        # to get the data, we need to find the location of the second `"""`
        second_quote_index = module_source.find('"""', module_source.find('"""') + 1)
        data = module_source[second_quote_index + 3:]
        first_newline_index = data.find('\n')
        if first_newline_index == -1:
            data = ""
        else:
            data = data[first_newline_index:].strip('\n')
    else:
        data = module_source
    return description, data


def bootstrap_modules():
    def add_module(module_class, module_name, module_type, bake_mode='FILE', extra_imports=''):
        # module_file = module_class.__module__
        module_file_path = inspect.getfile(module_class)

        with open(module_file_path, 'r', encoding='utf-8') as file:
            module_source = file.read()

        if extra_imports:
            module_source = f'{extra_imports}\n{module_source}'

        description, module_source = split_module_source_description(module_source)
        config = {
            "name": module_name,
            "description": description,
            "data": module_source,
            "load_on_startup": True,
        }
        system.manager.modules.add(
            name=module_name,
            config=config,
            module_type=module_type,
            baked=1,
            locked=1,
            skip_load=True,
        )

    sql.execute("DELETE FROM modules WHERE baked = 1")

    module_types = {name: controller for name, controller in system.manager.modules.type_controllers.items()
                    if name is not None}
    for module_type in module_types:
        module_type_modules = system.manager.modules.get_modules_in_folder(
            module_type=module_type,
            fetch_keys=('name', 'class', 'baked', 'kind_folder',)
        )
        for module_name, module_class, baked, kind_folder in module_type_modules:
            if baked == 0:
                continue
            if module_class is None:
                print(f"Module class for {module_name} in {module_type} is None, skipping.")
                continue
            if module_name == 'config':
                pass
            # module = module_class.__module__
            add_module(
                module_class=module_class,
                module_name=module_name,
                module_type=module_type,
            )


def reset_table(table_name, item_configs=None, folder_type=None, folder_items=None, delete_existing=True):
    if delete_existing:
        sql.execute(f'DELETE FROM {table_name}')

    item_configs = item_configs or {}
    folder_items = folder_items or {}
    folders_ids = {}
    if folder_type:
        if delete_existing:
            sql.execute(f'DELETE FROM folders WHERE type = "{folder_type}" AND locked != 1')  # todo locked

        for folder, blocks in folder_items.items():
            folder_id = sql.get_scalar(f'SELECT id FROM folders WHERE `name` = "{folder}" AND `type` = "{folder_type}" LIMIT 1')
            if not folder_id:
                sql.execute(f'INSERT INTO folders (name, type) VALUES (?, "{folder_type}")', (folder,))
                folder_id = sql.get_scalar(f'SELECT MAX(id) FROM folders')
            print(folder_id)
            folders_ids[folder] = folder_id

    for key, conf in item_configs.items():
        # name = key.get('name') if isinstance(key, tuple) else key
        name = key
        field_vals = {}
        if isinstance(key, tuple):
            # key is a tuple(n) of tuples(2), a key value pair, find the value for 'name'
            name = next((kvp[1] for kvp in key if kvp[0] == 'name'), None)
            field_vals = {kvp[0]: kvp[1] for kvp in key}
        # field_vals = key if isinstance(key, tuple) else {}

        item_folder = next((folder_name for folder_name, item_list in folder_items.items() if name in item_list),
                            None)
        folder_id = folders_ids.get(item_folder, None)

        field_vals['name'] = name
        field_vals['config'] = json.dumps(conf)
        if folder_id:
            field_vals['folder_id'] = folder_id

        ex_cnt = sql.get_scalar(f'SELECT COUNT(*) FROM {table_name} WHERE `name` = ?', (name,))
        if ex_cnt > 0:
            sql.execute(f'UPDATE `{table_name}` SET config = ?, folder_id = ? WHERE `name` = ?', (field_vals['config'], field_vals.get('folder_id'), name))
        else:
            sql.execute(
                f"INSERT INTO `{table_name}` ({', '.join(field_vals.keys())}) VALUES ({', '.join(['?'] * len(field_vals))})",
                tuple(field_vals.values()))


def ensure_system_folders():
    sys_folders = {
        'blocks': {
            'Enhancement': ':/resources/icon-wand.png',
            'Time expressions': ':/resources/icon-clock.png',
        },
        'modules': {
            'Controllers': ':/resources/icon-settings-solid.png',
            'Managers': ':/resources/icon-settings-solid.png',
            'Connectors': ':/resources/icon-settings-solid.png',
            'Pages': ':/resources/icon-pages.png',
            'Widgets': ':/resources/icon-widgets.png',
            'Fields': ':/resources/icon-pencil.png',
            'Members': ':/resources/icon-agent-group.png',
            'Bubbles': ':/resources/icon-paste.png',
            'Behaviors': ':/resources/icon-settings-solid.png',
            'Providers': ':/resources/icon-archive3.png',
            'Toolkits': ':/resources/icon-tool-small.png',
            'Daemons': ':/resources/icon-settings-solid.png',
            'Primitives': ':/resources/icon-settings-solid.png',
            'Highlighters': ':/resources/icon-settings-solid.png',
            'Environments': ':/resources/icon-settings-solid.png',
        },
    }

    for folder_type, folders in sys_folders.items():
        ex_type_folders = sql.get_results("""
            SELECT 
                name
            FROM folders
            WHERE locked = 1 AND type = ?
        """, (folder_type,), return_type='list')

        ordr = 0
        for folder_name, icon_path in folders.items():
            ordr += 1
            config = json.dumps({
                'icon_path': icon_path,
                'name': folder_name,
            })

            exists = folder_name in ex_type_folders
            if not exists:
                sql.execute("""
                    INSERT INTO folders (`name`, `type`, `config`, `ordr`, `locked`, `expanded`, `parent_id`) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)""", (folder_name, folder_type, config, ordr, 1, 0, None)
                )
                parent_id = sql.get_scalar("SELECT MAX(id) FROM folders")
            else:
                parent_id = sql.get_scalar("SELECT id FROM folders WHERE `name` = ? AND `type` = ? AND `locked` = 1 LIMIT 1",
                                        (folder_name, folder_type))
                sql.execute("""
                    UPDATE folders
                    SET config = ?, 
                        ordr = ?
                    WHERE id = ?""", (config, ordr, parent_id))


def reset_folders():
    reset_table(
        table_name='folders',
        item_configs={},
    )
    ensure_system_folders()


def reset_models(preserve_keys=True):  # , ask_dialog=True):
    if preserve_keys:
        api_key_vals = sql.get_results("SELECT LOWER(name), api_key FROM apis WHERE api_key != ''", return_type='dict')
    
    if not preserve_keys or len(api_key_vals) == 0:
        api_key_vals = {
            'anthropic': '$ANTHROPIC_API_KEY',
            'mistral': '$MISTRAL_API_KEY',
            'perplexity': '$PERPLEXITY_API_KEY',
            'openai': '$OPENAI_API_KEY',
            'elevenlabs': '$ELEVENLABS_API_KEY',
            'gemini': '$GEMINI_API_KEY',
            'xai': '$XAI_API_KEY',
            'fal ai': '$FAL_API_KEY',
        }
    
    reset_table(
        table_name='apis',
        item_configs={},
    )
    reset_table(
        table_name='models',
        item_configs={},
    )

    for name, provider in system.manager.providers.items():
        if hasattr(provider, 'reset_models'):
            raise NotImplementedError("Delete this")
        if not hasattr(provider, 'sync_models'):
            continue
        # if name == 'inhouse':
        #     continue
        # provider.reset_models()
        provider.sync_models()
    
    # system.manager.providers['inhouse'].reset_models()
    
    # sql.execute("UPDATE apis SET provider_plugin = 'openai' WHERE LOWER(name) = 'openai'")
    for name, key in api_key_vals.items():
        sql.execute("UPDATE apis SET api_key = ? WHERE LOWER(name) = ?", (key, name))

    return
    reset_table(
        table_name='apis',
        item_configs={
            (("id", 22), ("name", "AI21")): {},
            (("id", 17), ("name", "AWS Bedrock")): {"litellm_prefix": "bedrock"},
            (("id", 16), ("name", "AWS Sagemaker")): {"litellm_prefix": "sagemaker"},
            (("id", 5), ("name", "AWSPolly")): {},
            (("id", 27), ("name", "Aleph Alpha")): {},
            (("id", 15), ("name", "Anthropic")): {},
            (("id", 18), ("name", "Anyscale")): {"litellm_prefix": "anyscale"},
            (("id", 10), ("name", "Azure OpenAI")): {"litellm_prefix": "azure"},
            (("id", 28), ("name", "Baseten")): {"litellm_prefix": "baseten"},
            (("id", 34), ("name", "Cloudflare")): {"litellm_prefix": "cloudflare"},
            (("id", 25), ("name", "Cohere")): {},
            (("id", 30), ("name", "Custom API Server")): {},
            (("id", 21), ("name", "DeepInfra")): {"litellm_prefix": "deepinfra"},
            (("id", 39), ("name", "DeepSeek")): {"litellm_prefix": "deepseek"},
            (("id", 3), ("name", "ElevenLabs")): {},
            (("id", 1), ("name", "FakeYou")): {},
            (("id", 36), ("name", "Google AI studio")): {"litellm_prefix": "google"},
            (("id", 38), ("name", "Github")): {"litellm_prefix": "github"},
            (("id", 33), ("name", "Groq")): {"litellm_prefix": "groq"},
            (("id", 11), ("name", "Huggingface")): {"litellm_prefix": "huggingface"},
            (("id", 32), ("name", "Mistral")): {"litellm_prefix": "mistral"},
            (("id", 23), ("name", "NLP Cloud")): {},
            (("id", 37), ("name", "Nvidia NIM")): {"litellm_prefix": "nvidia_nim"},
            (("id", 12), ("name", "Ollama")): {"litellm_prefix": "ollama"},
            (("id", 4), ("name", "OpenAI")): {},
            (("id", 29), ("name", "OpenRouter")): {"litellm_prefix": "openrouter"},
            (("id", 14), ("name", "PaLM API Google")): {"litellm_prefix": "palm"},
            (("id", 19), ("name", "Perplexity AI")): {"litellm_prefix": "perplexity"},
            (("id", 31), ("name", "Petals")): {"litellm_prefix": "petals"},
            (("id", 8), ("name", "Replicate")): {"litellm_prefix": "replicate"},
            (("id", 26), ("name", "Together AI")): {"litellm_prefix": "together_ai"},
            (("id", 2), ("name", "Uberduck")): {},
            (("id", 20), ("name", "VLLM")): {"litellm_prefix": "vllm"},
            (("id", 13), ("name", "VertexAI Google")): {"litellm_prefix": "vertex_ai"},
            (("id", 35), ("name", "Voyage")): {"litellm_prefix": "voyage"},
            (("id", 40), ("name", "xAI")): {},
            # (("id", 41), ("name", "Google AI Studio")): {"litellm_prefix": "gemini"},
        }
    )
    sql.execute("UPDATE apis SET provider_plugin = 'litellm'")
    api_providers = {  # all except litellm
        3: 'elevenlabs',
    }
    for api_id, provider in api_providers.items():
        sql.execute("UPDATE apis SET provider_plugin = ? WHERE id = ?", (provider, api_id))

    # sql.execute("UPDATE apis SET provider_plugin = 'openai' WHERE LOWER(name) = 'openai'")
    for name, key in api_key_vals.items():
        sql.execute("UPDATE apis SET api_key = ? WHERE LOWER(name) = ?", (key, name))

    reset_table(
        table_name='models',
        item_configs={
            # AI21
            (("name", "j2-light"), ("kind", "CHAT"), ("api_id", 22)): {
                "model_name": "j2-light"},
            (("name", "j2-mid"), ("kind", "CHAT"), ("api_id", 22)): {
                "model_name": "j2-mid"},
            (("name", "j2-ultra"), ("kind", "CHAT"), ("api_id", 22)): {
                "model_name": "j2-ultra"},

            # AWS Bedrock
            (("name", "anthropic.claude-v2"), ("kind", "CHAT"), ("api_id", 17)): {
                "model_name": "anthropic.claude-v2"},
            (("name", "anthropic.claude-instant-v1"), ("kind", "CHAT"), ("api_id", 17)): {
                "model_name": "anthropic.claude-instant-v1"},
            (("name", "anthropic.claude-v1"), ("kind", "CHAT"), ("api_id", 17)): {
                "model_name": "anthropic.claude-v1"},
            (("name", "amazon.titan-text-lite-v1"), ("kind", "CHAT"), ("api_id", 17)): {
                "model_name": "amazon.titan-text-lite-v1"},
            (("name", "amazon.titan-text-express-v1"), ("kind", "CHAT"), ("api_id", 17)): {
                "model_name": "amazon.titan-text-express-v1"},
            (("name", "cohere.command-text-v14"), ("kind", "CHAT"), ("api_id", 17)): {
                "model_name": "cohere.command-text-v14"},
            (("name", "ai21.j2-mid-v1"), ("kind", "CHAT"), ("api_id", 17)): {
                "model_name": "ai21.j2-mid-v1"},
            (("name", "ai21.j2-ultra-v1"), ("kind", "CHAT"), ("api_id", 17)): {
                "model_name": "ai21.j2-ultra-v1"},
            (("name", "meta.llama2-13b-chat-v1"), ("kind", "CHAT"), ("api_id", 17)): {
                "model_name": "meta.llama2-13b-chat-v1"},
            (("name", "anthropic.claude-3-sonnet-20240229-v1:0"), ("kind", "CHAT"), ("api_id", 17)): {
                "model_name": "anthropic.claude-3-sonnet-20240229-v1:0"},
            (("name", "anthropic.claude-v2:1"), ("kind", "CHAT"), ("api_id", 17)): {
                "model_name": "anthropic.claude-v2:1"},
            (("name", "meta.llama2-70b-chat-v1"), ("kind", "CHAT"), ("api_id", 17)): {
                "model_name": "meta.llama2-70b-chat-v1"},
            (("name", "mistral.mistral-7b-instruct-v0:2"), ("kind", "CHAT"), ("api_id", 17)): {
                "model_name": "mistral.mistral-7b-instruct-v0:2"},
            (("name", "mistral.mixtral-8x7b-instruct-v0:1"), ("kind", "CHAT"), ("api_id", 17)): {
                "model_name": "mistral.mixtral-8x7b-instruct-v0:1"},

            # AWS Sagemaker
            (("name", "jumpstart-dft-meta-textgeneration-llama-2-7b"), ("kind", "CHAT"), ("api_id", 16)): {
                "model_name": "jumpstart-dft-meta-textgeneration-llama-2-7b"},
            (("name", "your-endpoint"), ("kind", "CHAT"), ("api_id", 16)): {
                "model_name": "your-endpoint"},
            (("name", "jumpstart-dft-meta-textgeneration-llama-2-7b-f"), ("kind", "CHAT"), ("api_id", 16)): {
                "model_name": "jumpstart-dft-meta-textgeneration-llama-2-7b-f"},
            (("name", "jumpstart-dft-meta-textgeneration-llama-2-13b"), ("kind", "CHAT"), ("api_id", 16)): {
                "model_name": "jumpstart-dft-meta-textgeneration-llama-2-13b"},
            (("name", "jumpstart-dft-meta-textgeneration-llama-2-13b-f"), ("kind", "CHAT"), ("api_id", 16)): {
                "model_name": "jumpstart-dft-meta-textgeneration-llama-2-13b-f"},
            (("name", "jumpstart-dft-meta-textgeneration-llama-2-70b"), ("kind", "CHAT"), ("api_id", 16)): {
                "model_name": "jumpstart-dft-meta-textgeneration-llama-2-70b"},
            (("name", "jumpstart-dft-meta-textgeneration-llama-2-70b-b-f"), ("kind", "CHAT"), ("api_id", 16)): {
                "model_name": "jumpstart-dft-meta-textgeneration-llama-2-70b-b-f"},

            # Aleph Alpha
            (("name", "luminous-base"), ("kind", "CHAT"), ("api_id", 27)): {
                "model_name": "luminous-base"},
            (("name", "luminous-base-control"), ("kind", "CHAT"), ("api_id", 27)): {
                "model_name": "luminous-base-control"},
            (("name", "luminous-extended"), ("kind", "CHAT"), ("api_id", 27)): {
                "model_name": "luminous-extended"},
            (("name", "luminous-extended-control"), ("kind", "CHAT"), ("api_id", 27)): {
                "model_name": "luminous-extended-control"},
            (("name", "luminous-supreme"), ("kind", "CHAT"), ("api_id", 27)): {
                "model_name": "luminous-supreme"},
            (("name", "luminous-supreme-control"), ("kind", "CHAT"), ("api_id", 27)): {
                "model_name": "luminous-supreme-control"},

            # Anthropic
            (("name", "claude-3-7-sonnet-latest"), ("kind", "CHAT"), ("api_id", 15)): {
                "model_name": "claude-3-7-sonnet-latest"},
            (("name", "claude-3-5-sonnet"), ("kind", "CHAT"), ("api_id", 15)): {
                "model_name": "claude-3-5-sonnet-20240620"},
            (("name", "claude-3-sonnet"), ("kind", "CHAT"), ("api_id", 15)): {
                "model_name": "claude-3-sonnet-20240229"},
            (("name", "claude-3-haiku"), ("kind", "CHAT"), ("api_id", 15)): {
                "model_name": "claude-3-haiku-20240307"},
            (("name", "claude-3-opus"), ("kind", "CHAT"), ("api_id", 15)): {
                "model_name": "claude-3-opus-latest"},
            (("name", "claude-2.1"), ("kind", "CHAT"), ("api_id", 15)): {
                "model_name": "claude-2.1"},
            (("name", "claude-2"), ("kind", "CHAT"), ("api_id", 15)): {
                "model_name": "claude-2"},
            (("name", "claude-instant-1.2"), ("kind", "CHAT"), ("api_id", 15)): {
                "model_name": "claude-instant-1.2"},
            (("name", "claude-instant-1"), ("kind", "CHAT"), ("api_id", 15)): {
                "model_name": "claude-instant-1"},

            # Anyscale
            (("name", "meta-llama/Llama-2-7b-chat-hf"), ("kind", "CHAT"), ("api_id", 18)): {
                "model_name": "meta-llama/Llama-2-7b-chat-hf"},
            (("name", "meta-llama/Llama-2-13b-chat-hf"), ("kind", "CHAT"), ("api_id", 18)): {
                "model_name": "meta-llama/Llama-2-13b-chat-hf"},
            (("name", "meta-llama/Llama-2-70b-chat-hf"), ("kind", "CHAT"), ("api_id", 18)): {
                "model_name": "meta-llama/Llama-2-70b-chat-hf"},
            (("name", "mistralai/Mistral-7B-Instruct-v0.1"), ("kind", "CHAT"), ("api_id", 18)): {
                "model_name": "mistralai/Mistral-7B-Instruct-v0.1"},
            (("name", "codellama/CodeLlama-34b-Instruct-hf"), ("kind", "CHAT"), ("api_id", 18)): {
                "model_name": "codellama/CodeLlama-34b-Instruct-hf"},

            # Azure OpenAI
            (("name", "azure/gpt-4"), ("kind", "CHAT"), ("api_id", 10)): {
                "model_name": "gpt-4"},
            (("name", "azure/gpt-4-0314"), ("kind", "CHAT"), ("api_id", 10)): {
                "model_name": "gpt-4-0314"},
            (("name", "azure/gpt-4-0613"), ("kind", "CHAT"), ("api_id", 10)): {
                "model_name": "gpt-4-0613"},
            (("name", "azure/gpt-4-32k"), ("kind", "CHAT"), ("api_id", 10)): {
                "model_name": "gpt-4-32k"},
            (("name", "azure/gpt-4-32k-0314"), ("kind", "CHAT"), ("api_id", 10)): {
                "model_name": "gpt-4-32k-0314"},
            (("name", "azure/gpt-4-32k-0613"), ("kind", "CHAT"), ("api_id", 10)): {
                "model_name": "gpt-4-32k-0613"},
            (("name", "azure/gpt-3.5-turbo"), ("kind", "CHAT"), ("api_id", 10)): {
                "model_name": "gpt-3.5-turbo"},
            (("name", "azure/gpt-3.5-turbo-0301"), ("kind", "CHAT"), ("api_id", 10)): {
                "model_name": "gpt-3.5-turbo-0301"},
            (("name", "azure/gpt-3.5-turbo-0613"), ("kind", "CHAT"), ("api_id", 10)): {
                "model_name": "gpt-3.5-turbo-0613"},
            (("name", "azure/gpt-3.5-turbo-16k"), ("kind", "CHAT"), ("api_id", 10)): {
                "model_name": "gpt-3.5-turbo-16k"},
            (("name", "azure/gpt-3.5-turbo-16k-0613"), ("kind", "CHAT"), ("api_id", 10)): {
                "model_name": "gpt-3.5-turbo-16k-0613"},

            # Baseten
            (("name", "Falcon 7B"), ("kind", "CHAT"), ("api_id", 28)): {
                "model_name": "qvv0xeq"},
            (("name", "Wizard LM"), ("kind", "CHAT"), ("api_id", 28)): {
                "model_name": "q841o8w"},
            (("name", "MPT 7B Base"), ("kind", "CHAT"), ("api_id", 28)): {
                "model_name": "31dxrj3"},

            # Cloudflare
            (("name", "mistral/mistral-tiny"), ("kind", "CHAT"), ("api_id", 34)): {
                "model_name": "mistral/mistral-tiny"},
            (("name", "mistral/mistral-small"), ("kind", "CHAT"), ("api_id", 34)): {
                "model_name": "mistral/mistral-small"},
            (("name", "mistral/mistral-medium"), ("kind", "CHAT"), ("api_id", 34)): {
                "model_name": "mistral/mistral-medium"},
            (("name", "codellama/codellama-medium"), ("kind", "CHAT"), ("api_id", 34)): {
                "model_name": "codellama/codellama-medium"},

            # Cohere
            (("name", "command"), ("kind", "CHAT"), ("api_id", 25)): {
                "model_name": "command"},
            (("name", "command-light"), ("kind", "CHAT"), ("api_id", 25)): {
                "model_name": "command-light"},
            (("name", "command-medium"), ("kind", "CHAT"), ("api_id", 25)): {
                "model_name": "command-medium"},
            (("name", "command-medium-beta"), ("kind", "CHAT"), ("api_id", 25)): {
                "model_name": "command-medium-beta"},
            (("name", "command-xlarge-beta"), ("kind", "CHAT"), ("api_id", 25)): {
                "model_name": "command-xlarge-beta"},
            (("name", "command-nightly"), ("kind", "CHAT"), ("api_id", 25)): {
                "model_name": "command-nightly"},

            # DeepInfra
            (("name", "meta-llama/Llama-2-70b-chat-hf"), ("kind", "CHAT"), ("api_id", 21)): {
                "model_name": "meta-llama/Llama-2-70b-chat-hf"},
            (("name", "meta-llama/Llama-2-7b-chat-hf"), ("kind", "CHAT"), ("api_id", 21)): {
                "model_name": "meta-llama/Llama-2-7b-chat-hf"},
            (("name", "meta-llama/Llama-2-13b-chat-hf"), ("kind", "CHAT"), ("api_id", 21)): {
                "model_name": "meta-llama/Llama-2-13b-chat-hf"},
            (("name", "codellama/CodeLlama-34b-Instruct-hf"), ("kind", "CHAT"), ("api_id", 21)): {
                "model_name": "codellama/CodeLlama-34b-Instruct-hf"},
            (("name", "mistralai/Mistral-7B-Instruct-v0.1"), ("kind", "CHAT"), ("api_id", 21)): {
                "model_name": "mistralai/Mistral-7B-Instruct-v0.1"},
            (("name", "jondurbin/airoboros-l2-70b-gpt4-1.4.1"), ("kind", "CHAT"), ("api_id", 21)): {
                "model_name": "jondurbin/airoboros-l2-70b-gpt4-1.4.1"},

            # DeepSeek
            (("name", "Deepseek V3"), ("kind", "CHAT"), ("api_id", 39)): {
                "model_name": "deepseek-chat"},
            (("name", "Deepseek R1"), ("kind", "CHAT"), ("api_id", 39)): {
                "model_name": "deepseek-reasoner"},

            # Google AI studio
            (("name", "Gemini 2.5 Flash"), ("kind", "CHAT"), ("api_id", 36)): {
                "model_name": "gemini-2.5-flash"},
            (("name", "Gemini 2.5 Pro"), ("kind", "CHAT"), ("api_id", 36)): {
                "model_name": "gemini-2.5-pro"},
            (("name", "gemini-pro"), ("kind", "CHAT"), ("api_id", 36)): {
                "model_name": "gemini-pro"},
            (("name", "gemini-1.5-pro-latest"), ("kind", "CHAT"), ("api_id", 36)): {
                "model_name": "gemini-1.5-pro-latest"},
            (("name", "gemini-2.0-flash"), ("kind", "CHAT"), ("api_id", 36)): {
                "model_name": "gemini-2.0-flash"},
            (("name", "gemini-2.0-flash-exp"), ("kind", "CHAT"), ("api_id", 36)): {
                "model_name": "gemini-2.0-flash-exp"},
            (("name", "gemini-2.0-flash-lite-preview-02-05"), ("kind", "CHAT"), ("api_id", 36)): {
                "model_name": "gemini-2.0-flash-lite-preview-02-05"},

            # Github
            (("name", "llama-3.1-8b-instant"), ("kind", "CHAT"), ("api_id", 38)): {
                "model_name": "llama-3.1-8b-instant"},
            (("name", "llama-3.1-70b-versatile"), ("kind", "CHAT"), ("api_id", 38)): {
                "model_name": "llama-3.1-70b-versatile"},
            (("name", "llama3-8b-8192"), ("kind", "CHAT"), ("api_id", 38)): {
                "model_name": "llama3-8b-8192"},
            (("name", "llama3-70b-8192"), ("kind", "CHAT"), ("api_id", 38)): {
                "model_name": "llama3-70b-8192"},
            (("name", "llama2-70b-4096"), ("kind", "CHAT"), ("api_id", 38)): {
                "model_name": "llama2-70b-4096"},
            (("name", "mixtral-8x7b-32768"), ("kind", "CHAT"), ("api_id", 38)): {
                "model_name": "mixtral-8x7b-32768"},
            (("name", "gemma-7b-it"), ("kind", "CHAT"), ("api_id", 38)): {
                "model_name": "gemma-7b-it"},

            # Groq
            (("name", "llama-3.1-8b-instant"), ("kind", "CHAT"), ("api_id", 33)): {
                "model_name": "llama-3.1-8b-instant"},
            (("name", "llama-3.1-70b-versatile"), ("kind", "CHAT"), ("api_id", 33)): {
                "model_name": "llama-3.1-70b-versatile"},
            (("name", "llama3-8b-8192"), ("kind", "CHAT"), ("api_id", 33)): {
                "model_name": "llama3-8b-8192"},
            (("name", "llama3-70b-8192"), ("kind", "CHAT"), ("api_id", 33)): {
                "model_name": "llama3-70b-8192"},
            (("name", "llama3-groq-8b-8192-tool-use-preview"), ("kind", "CHAT"), ("api_id", 33)): {
                "model_name": "llama3-groq-8b-8192-tool-use-preview"},
            (("name", "llama3-groq-70b-8192-tool-use-preview"), ("kind", "CHAT"), ("api_id", 33)): {
                "model_name": "llama3-groq-70b-8192-tool-use-preview"},
            (("name", "llama2-70b-4096"), ("kind", "CHAT"), ("api_id", 33)): {
                "model_name": "llama2-70b-4096"},
            (("name", "mixtral-8x7b-32768"), ("kind", "CHAT"), ("api_id", 33)): {
                "model_name": "mixtral-8x7b-32768"},
            (("name", "gemma2-9b-it"), ("kind", "CHAT"), ("api_id", 33)): {
                "model_name": "gemma2-9b-it"},
            (("name", "gemma-7b-it"), ("kind", "CHAT"), ("api_id", 33)): {
                "model_name": "gemma-7b-it"},
            (("name", "llava-v1.5-7b-4096-preview"), ("kind", "CHAT"), ("api_id", 33)): {
                "model_name": "llava-v1.5-7b-4096-preview"},
            (("name", "llama-guard-3-8b"), ("kind", "CHAT"), ("api_id", 33)): {
                "model_name": "llama-guard-3-8b"},

            # Huggingface
            (("name", "mistralai/Mistral-7B-Instruct-v0.1"), ("kind", "CHAT"), ("api_id", 11)): {
                "model_name": "mistralai/Mistral-7B-Instruct-v0.1"},
            (("name", "meta-llama/Llama-2-7b-chat"), ("kind", "CHAT"), ("api_id", 11)): {
                "model_name": "meta-llama/Llama-2-7b-chat"},
            (("name", "tiiuae/falcon-7b-instruct"), ("kind", "CHAT"), ("api_id", 11)): {
                "model_name": "tiiuae/falcon-7b-instruct"},
            (("name", "mosaicml/mpt-7b-chat"), ("kind", "CHAT"), ("api_id", 11)): {
                "model_name": "mosaicml/mpt-7b-chat"},
            (("name", "codellama/CodeLlama-34b-Instruct-hf"), ("kind", "CHAT"), ("api_id", 11)): {
                "model_name": "codellama/CodeLlama-34b-Instruct-hf"},
            (("name", "WizardLM/WizardCoder-Python-34B-V1.0"), ("kind", "CHAT"), ("api_id", 11)): {
                "model_name": "WizardLM/WizardCoder-Python-34B-V1.0"},
            (("name", "Phind/Phind-CodeLlama-34B-v2"), ("kind", "CHAT"), ("api_id", 11)): {
                "model_name": "Phind/Phind-CodeLlama-34B-v2"},

            # Mistral
            (("name", "Mistral Small"), ("kind", "CHAT"), ("api_id", 32)): {
                "model_name": "mistral-small-latest"},
            (("name", "Mistral Medium"), ("kind", "CHAT"), ("api_id", 32)): {
                "model_name": "mistral-medium-latest"},
            (("name", "Mistral Large 2"), ("kind", "CHAT"), ("api_id", 32)): {
                "model_name": "mistral-large-2407"},
            (("name", "Mistral Large Latest"), ("kind", "CHAT"), ("api_id", 32)): {
                "model_name": "mistral-large-latest"},
            (("name", "Mistral 7B"), ("kind", "CHAT"), ("api_id", 32)): {
                "model_name": "open-mistral-7b"},
            (("name", "Mixtral 8x7B"), ("kind", "CHAT"), ("api_id", 32)): {
                "model_name": "open-mixtral-8x7b"},
            (("name", "Mixtral 8x22B"), ("kind", "CHAT"), ("api_id", 32)): {
                "model_name": "open-mixtral-8x22b"},
            (("name", "Codestral"), ("kind", "CHAT"), ("api_id", 32)): {
                "model_name": "codestral-latest"},
            (("name", "Mistral NeMo"), ("kind", "CHAT"), ("api_id", 32)): {
                "model_name": "open-mistral-nemo"},
            (("name", "Mistral NeMo 2407"), ("kind", "CHAT"), ("api_id", 32)): {
                "model_name": "open-mistral-nemo-2407"},
            (("name", "Codestral Mamba"), ("kind", "CHAT"), ("api_id", 32)): {
                "model_name": "open-codestral-mamba"},
            (("name", "Codestral Mamba Latest"), ("kind", "CHAT"), ("api_id", 32)): {
                "model_name": "codestral-mamba-latest"},


            # NLP Cloud
            (("name", "dolphin"), ("kind", "CHAT"), ("api_id", 23)): {
                "model_name": "dolphin"},
            (("name", "chatdolphin"), ("kind", "CHAT"), ("api_id", 23)): {
                "model_name": "chatdolphin"},

            # Nvidia NIM
            (("name", "nvidia/nemotron-4-340b-reward"), ("kind", "CHAT"), ("api_id", 37)): {
                "model_name": "nvidia/nemotron-4-340b-reward"},
            (("name", "01-ai/yi-large"), ("kind", "CHAT"), ("api_id", 37)): {
                "model_name": "01-ai/yi-large"},
            (("name", "aisingapore/sea-lion-7b-instruct"), ("kind", "CHAT"), ("api_id", 37)): {
                "model_name": "aisingapore/sea-lion-7b-instruct"},
            (("name", "databricks/dbrx-instruct"), ("kind", "CHAT"), ("api_id", 37)): {
                "model_name": "databricks/dbrx-instruct"},
            (("name", "google/gemma-7b"), ("kind", "CHAT"), ("api_id", 37)): {
                "model_name": "google/gemma-7b"},
            (("name", "google/gemma-2b"), ("kind", "CHAT"), ("api_id", 37)): {
                "model_name": "google/gemma-2b"},
            (("name", "google/codegemma-1.1-7b"), ("kind", "CHAT"), ("api_id", 37)): {
                "model_name": "google/codegemma-1.1-7b"},
            (("name", "google/codegemma-7b"), ("kind", "CHAT"), ("api_id", 37)): {
                "model_name": "google/codegemma-7b"},
            (("name", "google/recurrentgemma-2b"), ("kind", "CHAT"), ("api_id", 37)): {
                "model_name": "google/recurrentgemma-2b"},
            (("name", "ibm/granite-34b-code-instruct"), ("kind", "CHAT"), ("api_id", 37)): {
                "model_name": "ibm/granite-34b-code-instruct"},
            (("name", "ibm/granite-8b-code-instruct"), ("kind", "CHAT"), ("api_id", 37)): {
                "model_name": "ibm/granite-8b-code-instruct"},
            (("name", "mediatek/breeze-7b-instruct"), ("kind", "CHAT"), ("api_id", 37)): {
                "model_name": "mediatek/breeze-7b-instruct"},
            (("name", "meta/codellama-70b"), ("kind", "CHAT"), ("api_id", 37)): {
                "model_name": "meta/codellama-70b"},
            (("name", "meta/llama2-70b"), ("kind", "CHAT"), ("api_id", 37)): {
                "model_name": "meta/llama2-70b"},
            (("name", "meta/llama3-8b"), ("kind", "CHAT"), ("api_id", 37)): {
                "model_name": "meta/llama3-8b"},
            (("name", "meta/llama3-70b"), ("kind", "CHAT"), ("api_id", 37)): {
                "model_name": "meta/llama3-70b"},
            (("name", "microsoft/phi-3-medium-4k-instruct"), ("kind", "CHAT"), ("api_id", 37)): {
                "model_name": "microsoft/phi-3-medium-4k-instruct"},
            (("name", "microsoft/phi-3-mini-128k-instruct"), ("kind", "CHAT"), ("api_id", 37)): {
                "model_name": "microsoft/phi-3-mini-128k-instruct"},
            (("name", "microsoft/phi-3-mini-4k-instruct"), ("kind", "CHAT"), ("api_id", 37)): {
                "model_name": "microsoft/phi-3-mini-4k-instruct"},
            (("name", "microsoft/phi-3-small-128k-instruct"), ("kind", "CHAT"), ("api_id", 37)): {
                "model_name": "microsoft/phi-3-small-128k-instruct"},
            (("name", "microsoft/phi-3-small-8k-instruct"), ("kind", "CHAT"), ("api_id", 37)): {
                "model_name": "microsoft/phi-3-small-8k-instruct"},
            (("name", "mistralai/codestral-22b-instruct-v0.1"), ("kind", "CHAT"), ("api_id", 37)): {
                "model_name": "mistralai/codestral-22b-instruct-v0.1"},
            (("name", "mistralai/mistral-7b-instruct"), ("kind", "CHAT"), ("api_id", 37)): {
                "model_name": "mistralai/mistral-7b-instruct"},
            (("name", "mistralai/mistral-7b-instruct-v0.3"), ("kind", "CHAT"), ("api_id", 37)): {
                "model_name": "mistralai/mistral-7b-instruct-v0.3"},
            (("name", "mistralai/mixtral-8x7b-instruct"), ("kind", "CHAT"), ("api_id", 37)): {
                "model_name": "mistralai/mixtral-8x7b-instruct"},
            (("name", "mistralai/mixtral-8x22b-instruct"), ("kind", "CHAT"), ("api_id", 37)): {
                "model_name": "mistralai/mixtral-8x22b-instruct"},
            (("name", "mistralai/mistral-large"), ("kind", "CHAT"), ("api_id", 37)): {
                "model_name": "mistralai/mistral-large"},
            (("name", "nvidia/nemotron-4-340b-instruct"), ("kind", "CHAT"), ("api_id", 37)): {
                "model_name": "nvidia/nemotron-4-340b-instruct"},
            (("name", "seallms/seallm-7b-v2.5"), ("kind", "CHAT"), ("api_id", 37)): {
                "model_name": "seallms/seallm-7b-v2.5"},
            (("name", "snowflake/arctic"), ("kind", "CHAT"), ("api_id", 37)): {
                "model_name": "snowflake/arctic"},
            (("name", "upstage/solar-10.7b-instruct"), ("kind", "CHAT"), ("api_id", 37)): {
                "model_name": "upstage/solar-10.7b-instruct"},

            # Ollama
            (("name", "Mistral"), ("kind", "CHAT"), ("api_id", 12)): {
                "model_name": "mistral"},
            (("name", "Llama2 7B"), ("kind", "CHAT"), ("api_id", 12)): {
                "model_name": "llama2"},
            (("name", "Llama2 13B"), ("kind", "CHAT"), ("api_id", 12)): {
                "model_name": "llama2:13b"},
            (("name", "Llama2 70B"), ("kind", "CHAT"), ("api_id", 12)): {
                "model_name": "llama2:70b"},
            (("name", "Llama2 Uncensored"), ("kind", "CHAT"), ("api_id", 12)): {
                "model_name": "llama2-uncensored"},
            (("name", "Code Llama"), ("kind", "CHAT"), ("api_id", 12)): {
                "model_name": "codellama"},
            (("name", "Llama2 Uncensored"), ("kind", "CHAT"), ("api_id", 12)): {
                "model_name": "llama2-uncensored"},
            (("name", "Orca Mini"), ("kind", "CHAT"), ("api_id", 12)): {
                "model_name": "orca-mini"},
            (("name", "Vicuna"), ("kind", "CHAT"), ("api_id", 12)): {
                "model_name": "vicuna"},
            (("name", "Nous-Hermes"), ("kind", "CHAT"), ("api_id", 12)): {
                "model_name": "nous-hermes"},
            (("name", "Nous-Hermes 13B"), ("kind", "CHAT"), ("api_id", 12)): {
                "model_name": "nous-hermes:13b"},
            (("name", "Wizard Vicuna Uncensored"), ("kind", "CHAT"), ("api_id", 12)): {
                "model_name": "wizard-vicuna"},

            # OpenAI
            (("name", "GPT 5"), ("kind", "CHAT"), ("api_id", 4)): {
                "model_name": "gpt-5"},
            (("name", "GPT 5 mini"), ("kind", "CHAT"), ("api_id", 4)): {
                "model_name": "gpt-5-mini"},
            (("name", "GPT 5 nano"), ("kind", "CHAT"), ("api_id", 4)): {
                "model_name": "gpt-5-nano"},
            (("name", "GPT 5 Chat"), ("kind", "CHAT"), ("api_id", 4)): {
                "model_name": "gpt-5-chat-latest"},
            (("name", "GPT 4o"), ("kind", "CHAT"), ("api_id", 4)): {
                "model_name": "gpt-4o"},
            (("name", "GPT 4o mini"), ("kind", "CHAT"), ("api_id", 4)): {
                "model_name": "gpt-4o-mini"},
            (("name", "GPT 4o Realtime"), ("kind", "CHAT"), ("api_id", 4)): {
                "model_name": "gpt-4o-realtime-preview-2024-10-01", "v2v": True},
            (("name", "O3 mini"), ("kind", "CHAT"), ("api_id", 4)): {
                "model_name": "o3-mini"},
            (("name", "O1"), ("kind", "CHAT"), ("api_id", 4)): {
                "model_name": "o1"},
            (("name", "O1 mini"), ("kind", "CHAT"), ("api_id", 4)): {
                "model_name": "o1-mini"},
            (("name", "GPT 3.5 Turbo"), ("kind", "CHAT"), ("api_id", 4)): {
                "model_name": "gpt-3.5-turbo"},
            (("name", "GPT 3.5 Turbo 16k"), ("kind", "CHAT"), ("api_id", 4)): {
                "model_name": "gpt-3.5-turbo-16k"},
            (("name", "GPT 3.5 Turbo (F)"), ("kind", "CHAT"), ("api_id", 4)): {
                "model_name": "gpt-3.5-turbo-1106"},
            (("name", "GPT 3.5 Turbo 16k (F)"), ("kind", "CHAT"), ("api_id", 4)): {
                "model_name": "gpt-3.5-turbo-16k-0613"},
            (("name", "GPT 4"), ("kind", "CHAT"), ("api_id", 4)): {
                "model_name": "gpt-4"},
            (("name", "GPT 4 32k"), ("kind", "CHAT"), ("api_id", 4)): {
                "model_name": "gpt-4-32k"},
            (("name", "GPT 4 (F)"), ("kind", "CHAT"), ("api_id", 4)): {
                "model_name": "gpt-4-0613"},
            (("name", "GPT 4 32k (F)"), ("kind", "CHAT"), ("api_id", 4)): {
                "model_name": "gpt-4-32k-0613"},
            (("name", "GPT 4 Turbo"), ("kind", "CHAT"), ("api_id", 4)): {
                "model_name": "gpt-4-1106-preview"},
            (("name", "GPT 4 Vision"), ("kind", "CHAT"), ("api_id", 4)): {
                "model_name": "gpt-4-vision-preview"},
            (("name", "GPT 4.5"), ("kind", "CHAT"), ("api_id", 4)): {
                "model_name": "gpt-4.5-preview"},

            # OpenRouter
            (("name", "openai/gpt-3.5-turbo"), ("kind", "CHAT"), ("api_id", 29)): {
                "model_name": "openai/gpt-3.5-turbo"},
            (("name", "openai/gpt-3.5-turbo-16k"), ("kind", "CHAT"), ("api_id", 29)): {
                "model_name": "openai/gpt-3.5-turbo-16k"},
            (("name", "openai/gpt-4"), ("kind", "CHAT"), ("api_id", 29)): {
                "model_name": "openai/gpt-4"},
            (("name", "openai/gpt-4-32k"), ("kind", "CHAT"), ("api_id", 29)): {
                "model_name": "openai/gpt-4-32k"},
            (("name", "anthropic/claude-2"), ("kind", "CHAT"), ("api_id", 29)): {
                "model_name": "anthropic/claude-2"},
            (("name", "anthropic/claude-instant-v1"), ("kind", "CHAT"), ("api_id", 29)): {
                "model_name": "anthropic/claude-instant-v1"},
            (("name", "google/palm-2-chat-bison"), ("kind", "CHAT"), ("api_id", 29)): {
                "model_name": "google/palm-2-chat-bison"},
            (("name", "google/palm-2-codechat-bison"), ("kind", "CHAT"), ("api_id", 29)): {
                "model_name": "google/palm-2-codechat-bison"},
            (("name", "meta-llama/llama-2-13b-chat"), ("kind", "CHAT"), ("api_id", 29)): {
                "model_name": "meta-llama/llama-2-13b-chat"},
            (("name", "meta-llama/llama-2-70b-chat"), ("kind", "CHAT"), ("api_id", 29)): {
                "model_name": "meta-llama/llama-2-70b-chat"},

            # PaLM API Google
            (("name", "palm/chat-bison"), ("kind", "CHAT"), ("api_id", 14)): {
                "model_name": "chat-bison"},

            # Perplexity AI
            (("name", "llama-3.1-sonar-small-128k-chat"), ("kind", "CHAT"), ("api_id", 19)): {
                "model_name": "llama-3.1-sonar-small-128k-chat"},
            (("name", "llama-3.1-sonar-large-128k-chat"), ("kind", "CHAT"), ("api_id", 19)): {
                "model_name": "llama-3.1-sonar-large-128k-chat"},
            (("name", "llama-3.1-sonar-small-128k-online"), ("kind", "CHAT"), ("api_id", 19)): {
                "model_name": "llama-3.1-sonar-small-128k-online"},
            (("name", "llama-3.1-sonar-large-128k-online"), ("kind", "CHAT"), ("api_id", 19)): {
                "model_name": "llama-3.1-sonar-large-128k-online"},
            (("name", "llama-3.1-sonar-huge-128k-online"), ("kind", "CHAT"), ("api_id", 19)): {
                "model_name": "llama-3.1-sonar-huge-128k-online"},
            (("name", "llama-3.1-8b-instruct"), ("kind", "CHAT"), ("api_id", 19)): {
                "model_name": "llama-3.1-8b-instruct"},
            (("name", "llama-3.1-70b-instruct"), ("kind", "CHAT"), ("api_id", 19)): {
                "model_name": "llama-3.1-70b-instruct"},

            # Petals
            (("name", "petals-team/StableBeluga2"), ("kind", "CHAT"), ("api_id", 31)): {
                "model_name": "petals-team/StableBeluga2"},
            (("name", "huggyllama/llama-65b"), ("kind", "CHAT"), ("api_id", 31)): {
                "model_name": "huggyllama/llama-65b"},

            # Replicate
            (("name", "llama-2-70b-chat:2796ee9483c3fd7aa2e171d38f4ca12251a30609463dcfd4cd76703f22e96cdf"),
             ("kind", "CHAT"), ("api_id", 8)): {
                "model_name": "llama-2-70b-chat:2796ee9483c3fd7aa2e171d38f4ca12251a30609463dcfd4cd76703f22e96cdf"},
            (("name", "a16z-infra/llama-2-13b-chat:2a7f981751ec7fdf87b5b91ad4db53683a98082e9ff7bfd12c8cd5ea85980a52"),
             ("kind", "CHAT"), ("api_id", 8)): {
                "model_name": "a16z-infra/llama-2-13b-chat:2a7f981751ec7fdf87b5b91ad4db53683a98082e9ff7bfd12c8cd5ea85980a52"},
            (("name", "vicuna-13b:6282abe6a492de4145d7bb601023762212f9ddbbe78278bd6771c8b3b2f2a13b"), ("kind", "CHAT"),
             ("api_id", 8)): {
                "model_name": "vicuna-13b:6282abe6a492de4145d7bb601023762212f9ddbbe78278bd6771c8b3b2f2a13b"},
            (("name", "daanelson/flan-t5-large:ce962b3f6792a57074a601d3979db5839697add2e4e02696b3ced4c022d4767f"),
             ("kind", "CHAT"), ("api_id", 8)): {
                "model_name": "daanelson/flan-t5-large:ce962b3f6792a57074a601d3979db5839697add2e4e02696b3ced4c022d4767f"},
            (("name", "custom-llm-version-id"), ("kind", "CHAT"), ("api_id", 8)): {
                "model_name": "custom-llm-version-id"},
            (("name", "deployments/ishaan-jaff/ishaan-mistral"), ("kind", "CHAT"), ("api_id", 8)): {
                "model_name": "deployments/ishaan-jaff/ishaan-mistral"},

            # Together AI
            (("name", "togethercomputer/llama-2-70b-chat"), ("kind", "CHAT"), ("api_id", 26)): {
                "model_name": "togethercomputer/llama-2-70b-chat"},
            (("name", "togethercomputer/llama-2-70b"), ("kind", "CHAT"), ("api_id", 26)): {
                "model_name": "togethercomputer/llama-2-70b"},
            (("name", "togethercomputer/LLaMA-2-7B-32K"), ("kind", "CHAT"), ("api_id", 26)): {
                "model_name": "togethercomputer/LLaMA-2-7B-32K"},
            (("name", "togethercomputer/Llama-2-7B-32K-Instruct"), ("kind", "CHAT"), ("api_id", 26)): {
                "model_name": "togethercomputer/Llama-2-7B-32K-Instruct"},
            (("name", "togethercomputer/llama-2-7b"), ("kind", "CHAT"), ("api_id", 26)): {
                "model_name": "togethercomputer/llama-2-7b"},
            (("name", "togethercomputer/falcon-40b-instruct"), ("kind", "CHAT"), ("api_id", 26)): {
                "model_name": "togethercomputer/falcon-40b-instruct"},
            (("name", "togethercomputer/falcon-7b-instruct"), ("kind", "CHAT"), ("api_id", 26)): {
                "model_name": "togethercomputer/falcon-7b-instruct"},
            (("name", "togethercomputer/alpaca-7b"), ("kind", "CHAT"), ("api_id", 26)): {
                "model_name": "togethercomputer/alpaca-7b"},
            (("name", "HuggingFaceH4/starchat-alpha"), ("kind", "CHAT"), ("api_id", 26)): {
                "model_name": "HuggingFaceH4/starchat-alpha"},
            (("name", "togethercomputer/CodeLlama-34b"), ("kind", "CHAT"), ("api_id", 26)): {
                "model_name": "togethercomputer/CodeLlama-34b"},
            (("name", "togethercomputer/CodeLlama-34b-Instruct"), ("kind", "CHAT"), ("api_id", 26)): {
                "model_name": "togethercomputer/CodeLlama-34b-Instruct"},
            (("name", "togethercomputer/CodeLlama-34b-Python"), ("kind", "CHAT"), ("api_id", 26)): {
                "model_name": "togethercomputer/CodeLlama-34b-Python"},
            (("name", "defog/sqlcoder"), ("kind", "CHAT"), ("api_id", 26)): {
                "model_name": "defog/sqlcoder"},
            (("name", "NumbersStation/nsql-llama-2-7B"), ("kind", "CHAT"), ("api_id", 26)): {
                "model_name": "NumbersStation/nsql-llama-2-7B"},
            (("name", "WizardLM/WizardCoder-15B-V1.0"), ("kind", "CHAT"), ("api_id", 26)): {
                "model_name": "WizardLM/WizardCoder-15B-V1.0"},
            (("name", "WizardLM/WizardCoder-Python-34B-V1.0"), ("kind", "CHAT"), ("api_id", 26)): {
                "model_name": "WizardLM/WizardCoder-Python-34B-V1.0"},
            (("name", "NousResearch/Nous-Hermes-Llama2-13b"), ("kind", "CHAT"), ("api_id", 26)): {
                "model_name": "NousResearch/Nous-Hermes-Llama2-13b"},
            (("name", "Austism/chronos-hermes-13b"), ("kind", "CHAT"), ("api_id", 26)): {
                "model_name": "Austism/chronos-hermes-13b"},
            (("name", "upstage/SOLAR-0-70b-16bit"), ("kind", "CHAT"), ("api_id", 26)): {
                "model_name": "upstage/SOLAR-0-70b-16bit"},
            (("name", "WizardLM/WizardLM-70B-V1.0"), ("kind", "CHAT"), ("api_id", 26)): {
                "model_name": "WizardLM/WizardLM-70B-V1.0"},

            # VLLM
            (("name", "meta-llama/Llama-2-7b"), ("kind", "CHAT"), ("api_id", 20)): {
                "model_name": "meta-llama/Llama-2-7b"},
            (("name", "tiiuae/falcon-7b-instruct"), ("kind", "CHAT"), ("api_id", 20)): {
                "model_name": "tiiuae/falcon-7b-instruct"},
            (("name", "mosaicml/mpt-7b-chat"), ("kind", "CHAT"), ("api_id", 20)): {
                "model_name": "mosaicml/mpt-7b-chat"},
            (("name", "codellama/CodeLlama-34b-Instruct-hf"), ("kind", "CHAT"), ("api_id", 20)): {
                "model_name": "codellama/CodeLlama-34b-Instruct-hf"},
            (("name", "WizardLM/WizardCoder-Python-34B-V1.0"), ("kind", "CHAT"), ("api_id", 20)): {
                "model_name": "WizardLM/WizardCoder-Python-34B-V1.0"},
            (("name", "Phind/Phind-CodeLlama-34B-v2"), ("kind", "CHAT"), ("api_id", 20)): {
                "model_name": "Phind/Phind-CodeLlama-34B-v2"},

            # VertexAI Google
            (("name", "chat-bison-32k"), ("kind", "CHAT"), ("api_id", 13)): {
                "model_name": "chat-bison-32k"},
            (("name", "chat-bison"), ("kind", "CHAT"), ("api_id", 13)): {
                "model_name": "chat-bison"},
            (("name", "chat-bison@001"), ("kind", "CHAT"), ("api_id", 13)): {
                "model_name": "chat-bison@001"},
            (("name", "codechat-bison"), ("kind", "CHAT"), ("api_id", 13)): {
                "model_name": "codechat-bison"},
            (("name", "codechat-bison-32k"), ("kind", "CHAT"), ("api_id", 13)): {
                "model_name": "codechat-bison-32k"},
            (("name", "codechat-bison@001"), ("kind", "CHAT"), ("api_id", 13)): {
                "model_name": "codechat-bison@001"},
            (("name", "text-bison"), ("kind", "CHAT"), ("api_id", 13)): {
                "model_name": "text-bison"},
            (("name", "text-bison@001"), ("kind", "CHAT"), ("api_id", 13)): {
                "model_name": "text-bison@001"},
            (("name", "code-bison"), ("kind", "CHAT"), ("api_id", 13)): {
                "model_name": "code-bison"},
            (("name", "code-bison@001"), ("kind", "CHAT"), ("api_id", 13)): {
                "model_name": "code-bison@001"},
            (("name", "code-gecko@001"), ("kind", "CHAT"), ("api_id", 13)): {
                "model_name": "code-gecko@001"},
            (("name", "code-gecko@latest"), ("kind", "CHAT"), ("api_id", 13)): {
                "model_name": "code-gecko@latest"},
            (("name", "gemini-pro"), ("kind", "CHAT"), ("api_id", 13)): {
                "model_name": "gemini-pro"},
            (("name", "gemini-1.5-pro"), ("kind", "CHAT"), ("api_id", 13)): {
                "model_name": "gemini-1.5-pro"},
            (("name", "gemini-pro-vision"), ("kind", "CHAT"), ("api_id", 13)): {
                "model_name": "gemini-pro-vision"},
            (("name", "gemini-1.5-pro-vision"), ("kind", "CHAT"), ("api_id", 13)): {
                "model_name": "gemini-1.5-pro-vision"},

            # Voyage
            (("name", "voyage-01"), ("kind", "CHAT"), ("api_id", 35)): {
                "model_name": "voyage-01"},
            (("name", "voyage-lite-01"), ("kind", "CHAT"), ("api_id", 35)): {
                "model_name": "voyage-lite-01"},
            (("name", "voyage-lite-01-instruct"), ("kind", "CHAT"), ("api_id", 35)): {
                "model_name": "voyage-lite-01-instruct"},

            # xAI
            (("name", "Grok 3"), ("kind", "CHAT"), ("api_id", 40)): {
                "model_name": "grok-3"},
            (("name", "Grok 3 (Fast)"), ("kind", "CHAT"), ("api_id", 40)): {
                "model_name": "grok-3-fast"},
            (("name", "Grok 3 Mini"), ("kind", "CHAT"), ("api_id", 40)): {
                "model_name": "grok-3-mini"},
            (("name", "Grok 3 Mini (Fast)"), ("kind", "CHAT"), ("api_id", 40)): {
                "model_name": "grok-3-mini-fast"},
            (("name", "Grok 2"), ("kind", "CHAT"), ("api_id", 40)): {
                "model_name": "grok-2"},
            (("name", "Grok 2 Vision"), ("kind", "CHAT"), ("api_id", 40)): {
                "model_name": "grok-2-vision"},
            (("name", "Grok 2 Image"), ("kind", "CHAT"), ("api_id", 40)): {
                "model_name": "grok-2-image"},
        }
    )

    from core.providers.elevenlabs import ElevenLabsProvider
    elevenlabs_provider = ElevenLabsProvider(None, 3)
    elevenlabs_provider.sync_all_voices()
    pass

