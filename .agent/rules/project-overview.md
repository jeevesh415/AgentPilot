---
trigger: always_on
---

# Project Overview

This application is a modular desktop platform built with Python, PySide6 and qAsync. At its core, it features a dynamic architecture where modules—ranging from backend services to interactive GUI widgets—can be loaded and modified, even at runtime. This design empowers both developers and users to customize functionality and adapt the user interface to their evolving needs.

Beyond its modular foundation, the application ships with a powerful and extensible workflow engine, a task scheduler, project manager and block library. Together, these tools provide a robust environment for building AI agents and interactive user interfaces with ease.

## Dependencies
- Uses Poetry for dependency management (pyproject.toml)
- Python 3.11 required
- Key dependencies: PySide6, qasync, jinja2, litellm, instructor

## Architecture Overview

The application follows a modular, plugin-based architecture centered around a `SystemManager`:

- **SystemManager** (`src/gui/main.py`): Central orchestrator that dynamically loads all Manager modules, one of which is the `ModuleManager`.

- **ModuleManager** (`src/core/managers/modules.py`): A special `manager` module that loads and maintains all modules, even other `manager` modules.

All modules fall under a specific type, each of these types are defined as `controller` modules under `src/core/controllers/`.
Note that because Controllers are themselves a type of module, they have their own `controller` module (`src/core/controllers/core/controllers.py`)

The types of modules (Controllers) built in to the app are listed below:

### Core module types:

- **Controllers**:  _No description available._ 

- **Behaviors**: Workflow behavior modules 

- **Connectors**: Database connection modules 

- **Daemons**: Background tasks or periodic jobs 

- **Environments**: Code execution environment modules 

- **Managers**: System-level management modules 

- **Members**: Workflow member modules 

- **Primitives**:  _No description available._ 

- **Providers**: AI model provider modules 


### GUI module types:

- **Bubbles**:  Chat message bubble modules 

- **Fields**:  Form field components 

- **Highlighters**:  Syntax highlighting modules 

- **Pages**:  UI page modules for the application 

- **Studios**:  Studio modules 

- **Widgets**:  Reusable UI widget components 


### GUI Architecture

The codebase implements a three-tier abstraction system for building
hierarchical UIs, where complexity is progressively abstracted into
reusable components:

#### The Hierarchy

1. Fields (src/gui/fields/)

Lowest level - Atomic, reusable input widgets, typically used from a ConfigFields or ConfigTree derived widget.

- Purpose: Individual form controls (text inputs, combos, buttons, color
pickers, etc.)
- Examples: Text, Combo, Boolean, FilePicker, ModelField
- Key traits:
- Extend Qt base widgets (QWidget, QLineEdit, etc.)
- Implement get_value() and set_value() methods
- Self-contained with their own validation and styling
- Have an option_schema defining how they themselves can be configured

2. Widgets (src/gui/widgets/)

Mid level - Configurable interfaces

Widgets are reusable configurable components that have a specific functionality
They can orchestrate multiple fields or other widgets
Ideally they extend ConfigWidget, or any other class derived from ConfigWidget

Key built-in Widgets:
{{ ConfigWidget }}
{{ ConfigFields }}
{{ ConfigJoined }}
{{ ConfigTabs }}
{{ ConfigPages }}
{{ ConfigDBTree }}

a) ConfigFields - Schema-driven form builder
- Takes a schema list defining fields
- Dynamically instantiates Field widgets via get_field_widget()
- Auto-binds values to/from config dict

b) ConfigDBTree - Database-backed tree view with config panel
- Left panel: Tree view of database items (with folders)
- Right panel: Configuration widget for selected item
- Handles CRUD operations, search, filtering

c) ConfigJoined - Combines multiple widgets
- Vertical or horizontal layout
- Aggregates configs from child widgets

d) WorkflowSettings - Complex workflow designer
- Visual graph editor with drag-drop
- Combines header fields + workflow canvas + member config
- A complete specialized configuration interface

e) Other specialized widgets:
- AgentSettings, InputSettings, NotifSettings, etc.
- Domain-specific configurations built from Fields/Widgets

Widget Responsibilities:

- Schema building: `build_schema()` - construct UI from schema
- Config loading: `load_config(json_config)` - populate from data source
- UI loading: `load()` - load UI from the config
- Propagation: `update_config()` - propagates up to root, runs save_config
- Config extraction: `get_config()` - serialize current state
- Config saving: `save_config()` - persist to database

Propagation:
a) Down from root to all leaf widgets:
- `build_schema()`
-` load_config()`
- `load()`

b) Up to root from any leaf widget:
- `update_config()`

Any widget can set the boolean attribute `self.propagate_config` which allows or prevents propagation of `load_config` and `update_config`.
This is True by default for all widgets, but some widgets such as `ConfigDBTree` and `ConfigTable` have it set to False.

3. Pages (src/gui/pages/)

Highest level - Widget definitions
Pages are special widgets with a navigation button added to the sidebar or settings page for users to navigate to. They are typically thin widget definitions, inheritting from any ConfigWidget derived class.

Pattern: Pages instantiate re-usable Widgets with specific configurations rather than implementing UI logic themselves.

Example: Page_Tool_Settings (src/gui/pages/tools.py:28-92)

class Page_Tool_Settings(ConfigDBTree):  # ← Extends ConfigDBTree widget
  display_name = 'Tools'
  icon_path = ":/resources/icon-tool.png"

  def __init__(self, parent):
      super().__init__(
          parent=parent,
          manager='tools',           # ← Configuration
          query="...",              # ← What data to show
          schema=[...],             # ← Tree columns
          config_widget=self.ToolWorkflowSettings(parent=self),  # ←
Right panel
          layout_type='horizontal',
          searchable=True,
          # ... more configuration
      )

  class ToolWorkflowSettings(WorkflowSettings):  # ← Nested widget class
      pass  # Inherits all behavior, just configures it

The Page does almost nothing - it just:
1. Extends ConfigDBTree widget
2. Configures it with table, query, schema
3. Specifies WorkflowSettings as the config widget
4. Optionally overrides methods like on_edited()

The Abstraction Philosophy:
1. Fields handle their own rendering and value management
2. Widgets handle schema interpretation and config flow
3. Pages just declare "what" (data source, schema), not "how" (UI logic)

All UI logic lives in reusable Widgets and Fields. This means:
- Pages are easily maintainable
- New pages are trivial to create
- Widgets are testable in isolation
- Consistent UX across the app

#### Schema-Driven UI

Some widgets have a `schema` attribute, which contains a list of dictionaries.
Fields and widgets are defined by schema dictionaries:

schema = [
  {
      'text': 'Name',        # Label
      'key': 'name',         # Config key
      'type': str,           # Field type (or tuple for Combo)
      'default': '',
      'width': 150,
      'is_config_field': True,  # Save to config vs DB column
  }
]

The system automatically:
- Instantiates the correct Field class
- Binds it to the config key
- Handles value serialization

#### Nested Widget Classes

Pages define widget subclasses inline to configure them:

class Page_Entities(ConfigDBTree):
  def __init__(self, parent):
      super().__init__(
          config_widget=self.Entity_Config_Widget(parent=self),  # ←
      )

  class Entity_Config_Widget(ConfigJoined):  # ← Nested class
      # ... configuration ...

This keeps related configurations together while maintaining separation.

### Agent Pilot
An **AgentPilot plugin** is a collection of modules bundled together and placed in the `src/plugins` directory.

By organizing related modules into a single plugin, all modules related to a feature or integration are kept together, making development and maintenance easier.

The application automatically discovers and loads plugins from the `src/plugins` directory at startup. Each module inside a plugin is registered and made available in the app, just like core codebase modules.

#### Plugin Structure

To create a plugin:

1. **Create a directory for your plugin under `src/plugins`**
   For example, if your plugin is called `my_plugin`, create the directory `src/plugins/my_plugin` with the following structure:
```
src/
    plugins/
        my_plugin/
            __init__.py
            pages/
                __init__.py
                my_page_module.py
            widgets/
                __init__.py
                my_widget_module.py
            [any other type of module]/
                [my_other_module.py]
   ```

2. **Organize your modules by type, mirroring the core codebase structure**
   Each module type (e.g., managers, providers, widgets, etc.) should have its own folder inside your plugin directory.
   Place your module files (Python files containing classes that inherit from the appropriate base class, such as `BaseManager`, `Provider`, etc.) in the corresponding folder.

3. **(Optional) Add extra source code**
   If your plugin needs additional code, you can add other files inside your plugin directory without needing them to be declared as modules.

4. **Ensure each folder has an `__init__.py` file**
   This makes sure Python recognizes it as a standard package.
{ Widget System }
{ PageSystem }
{ workflows }

## Database and Persistence

- SQLite database (`data.db`) stores contexts, messages, configurations
- Message history with branching support
- Workflow state persistence and resumption

## Important Implementation Details

### Module Loading
- **Dynamic module loading**: `ModuleManager` handles runtime loading/unloading
- **Multi-type module support**: 12+ module types with automatic discovery
- **Configuration hashing**: Change detection for module updates
- **Type controllers**: `ModulesController` manages each module type
- **Plugin organization**: Plugins contain collections of related modules
- Modules can be edited while application is running (if enabled)
- Plugin system allows extending functionality without core changes

### Configuration Management
- Configurations are JSON-based, stored in database
- Hierarchical config system supports complex nested structures
- UI automatically generates configuration interfaces from schemas

### File Organization
- `src/core/`: Core system logic and managers
- `src/gui/`: User interface components
- `src/plugins/`: Modular plugin implementations
- `src/utils/`: Shared utilities and helpers