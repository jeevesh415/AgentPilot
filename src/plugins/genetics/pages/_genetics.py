import random
import importlib
from PySide6.QtWidgets import QSplitter, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, QTimer
from gui.widgets.config_db_tree import ConfigDBTree
from gui.widgets.config_joined import ConfigJoined
from gui.widgets.config_widget import ConfigWidget
from gui.widgets.config_fields import ConfigFields
from utils.helpers import set_module_type
from gui import system

from ..widgets.control_panel import ControlPanel
from ..widgets.fitness_chart import FitnessChart
from ..widgets.population_view import PopulationView
from ..core.engine import GeneticAlgorithm

@set_module_type('Pages')
class Page_Genetics(ConfigDBTree):
    display_name = 'Genetics'
    icon_path = ":/resources/icon-gene.png"
    page_type = 'main'

    def __init__(self, parent):
        super().__init__(
            parent=parent,
            table_name='evolutions',
            query='''
                SELECT
                    name,
                    id
                FROM evolutions
            ''',
            schema=[
                {
                    'text': 'Name',
                    'key': 'name',
                    'type': str,
                    'stretch': True,
                },
                {
                    'text': 'id',
                    'key': 'id',
                    'type': int,
                    'visible': False,
                },
            ],
            layout_type='horizontal',
            config_widget=self.Genetics_Config_Widget(parent=self),
        )

    class Genetics_Config_Widget(ConfigJoined):
        def __init__(self, parent):
            super().__init__(
                parent=parent,
                widgets=[
                    self.Genetics_Settings(parent=self),
                    self.Genetics_Run_Widget(parent=self),
                ]
            )

        class Genetics_Settings(ConfigFields):
            def __init__(self, parent):
                super().__init__(
                    parent=parent,
                    schema=[
                        {
                            'text': 'Name',
                            'key': 'name',
                            'type': str,
                        },
                        {
                            'text': 'Problem Type',
                            'key': '_TYPE',
                            'type': 'combo',
                            'items': ['TravellingSalesman'],
                            'default': 'TravellingSalesman',
                        },
                    ]
                )

        class Genetics_Run_Widget(ConfigWidget):
            def __init__(self, parent):
                super().__init__(parent)
                self.layout = QVBoxLayout(self)
                
                self.ga_engine = None
                self.controller = None
                self.timer = QTimer(self)
                self.timer.timeout.connect(self.on_timer_tick)

                # Splitter for layout
                splitter = QSplitter(Qt.Horizontal)
                
                # Left Panel (Controls)
                self.control_panel = ControlPanel(self)
                self.control_panel.start_btn.clicked.connect(self.start_ga)
                self.control_panel.stop_btn.clicked.connect(self.stop_ga)
                self.control_panel.reset_btn.clicked.connect(self.reset_ga)
                splitter.addWidget(self.control_panel)
                
                # Right Panel (Visuals)
                right_splitter = QSplitter(Qt.Vertical)
                
                self.fitness_chart = FitnessChart(self)
                right_splitter.addWidget(self.fitness_chart)
                
                self.population_view = PopulationView(self)
                right_splitter.addWidget(self.population_view)
                
                splitter.addWidget(right_splitter)
                splitter.setSizes([300, 800])
                
                self.layout.addWidget(splitter)

            def load_config(self, json_config=None):
                super().load_config(json_config)
                self.load_controller()

            def load_controller(self):
                problem_type = self.config.get('_TYPE', 'TravellingSalesman')
                try:
                    # Dynamic import of controller
                    # Assuming problem_type matches the filename in snake_case
                    module_name = problem_type.lower()
                    if module_name == 'travellingsalesman':
                        module_name = 'travelling_salesman'
                        
                    module_path = f"plugins.genetics.ga_types.{module_name}"
                    module = importlib.import_module(module_path)
                    
                    # Assuming the class name matches the problem_type
                    controller_class = getattr(module, problem_type)
                    self.controller = controller_class()

                    # Setup visualization
                    if hasattr(self.controller, 'setup'):
                         self.controller.setup()
                    
                except Exception as e:
                    print(f"Error loading controller {problem_type}: {e}")

            def start_ga(self):
                if not self.controller:
                    self.load_controller()
                
                if not self.controller:
                    return

                params = self.control_panel.get_parameters()
                
                # Controller setup (e.g. cities)
                # We might want to persist cities in config, but for now random each run
                cities = self.controller.setup()
                self.population_view.set_cities(cities)
                
                self.ga_engine = GeneticAlgorithm(
                    population_size=params['population_size'],
                    mutation_rate=params['mutation_rate'],
                    elitism=params['elitism'],
                    individual_class=self.controller.create_individual().__class__, # Hacky, should use factory
                    cities=cities # specific to TSP
                )
                
                self.ga_engine.initialize_population()
                self.ga_engine.generation_completed.connect(self.on_generation_completed)
                
                self.fitness_chart.clear()
                self.population_view.clear()
                self.population_view.set_cities(cities)
                
                self.control_panel.start_btn.setEnabled(False)
                self.control_panel.stop_btn.setEnabled(True)
                self.control_panel.reset_btn.setEnabled(False)
                
                self.timer.start(10)

            def stop_ga(self):
                self.timer.stop()
                self.control_panel.start_btn.setEnabled(True)
                self.control_panel.stop_btn.setEnabled(False)
                self.control_panel.reset_btn.setEnabled(True)

            def reset_ga(self):
                self.stop_ga()
                self.fitness_chart.clear()
                self.population_view.clear()
                self.ga_engine = None

            def on_generation_completed(self, generation, max_fit, avg_fit, best_ind):
                # print(f"Gen {generation}: Max {max_fit}")
                self.fitness_chart.update_chart(generation, max_fit, avg_fit)
                if self.controller:
                    self.controller.update_visualization(self.population_view, best_ind)

            def on_timer_tick(self):
                if self.ga_engine:
                    self.ga_engine.step()
                else:
                    print("Timer tick but no engine")
