from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSpinBox, QDoubleSpinBox, QComboBox, QGroupBox
from gui.widgets.config_widget import ConfigWidget
from gui.util import CVBoxLayout, CHBoxLayout

class ControlPanel(ConfigWidget):
    def __init__(self, parent):
        super().__init__(parent=parent)
        self.layout = CVBoxLayout(self)
        
        # Problem Selection
        problem_group = QGroupBox("Problem")
        problem_layout = CVBoxLayout()
        self.problem_combo = QComboBox()
        self.problem_combo.addItem("Traveling Salesperson (TSP)")
        problem_layout.addWidget(self.problem_combo)
        problem_group.setLayout(problem_layout)
        self.layout.addWidget(problem_group)
        
        # Parameters
        params_group = QGroupBox("Parameters")
        params_layout = CVBoxLayout()
        
        # Population Size
        pop_layout = CHBoxLayout()
        pop_layout.addWidget(QLabel("Population Size:"))
        self.pop_size_spin = QSpinBox()
        self.pop_size_spin.setRange(10, 1000)
        self.pop_size_spin.setValue(100)
        pop_layout.addWidget(self.pop_size_spin)
        params_layout.addLayout(pop_layout)
        
        # Mutation Rate
        mut_layout = CHBoxLayout()
        mut_layout.addWidget(QLabel("Mutation Rate:"))
        self.mut_rate_spin = QDoubleSpinBox()
        self.mut_rate_spin.setRange(0.0, 1.0)
        self.mut_rate_spin.setSingleStep(0.01)
        self.mut_rate_spin.setValue(0.01)
        mut_layout.addWidget(self.mut_rate_spin)
        params_layout.addLayout(mut_layout)
        
        # Elitism
        # elitism_layout = CHBoxLayout()
        # elitism_layout.addWidget(QLabel("Elitism:"))
        # self.elitism_check = QCheckBox()
        # self.elitism_check.setChecked(True)
        # elitism_layout.addWidget(self.elitism_check)
        # params_layout.addLayout(elitism_layout)
        
        params_group.setLayout(params_layout)
        self.layout.addWidget(params_group)
        
        # Controls
        controls_layout = CHBoxLayout()
        self.start_btn = QPushButton("Start")
        self.stop_btn = QPushButton("Stop")
        self.reset_btn = QPushButton("Reset")
        
        self.stop_btn.setEnabled(False)
        
        controls_layout.addWidget(self.start_btn)
        controls_layout.addWidget(self.stop_btn)
        controls_layout.addWidget(self.reset_btn)
        self.layout.addLayout(controls_layout)
        
        self.layout.addStretch()

    def get_parameters(self):
        return {
            'population_size': self.pop_size_spin.value(),
            'mutation_rate': self.mut_rate_spin.value(),
            'elitism': True # self.elitism_check.isChecked()
        }
