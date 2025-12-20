from PySide6.QtWidgets import QVBoxLayout, QLabel
from PySide6.QtGui import QColor
from gui.widgets.config_widget import ConfigWidget
import pyqtgraph as pg

class FitnessChart(ConfigWidget):
    def __init__(self, parent):
        super().__init__(parent=parent)
        self.layout = QVBoxLayout(self)
        
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('w')
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.setLabel('left', 'Fitness')
        self.plot_widget.setLabel('bottom', 'Generation')
        self.plot_widget.addLegend()
        
        self.max_fitness_curve = self.plot_widget.plot(pen=pg.mkPen('b', width=2), name='Max Fitness')
        self.avg_fitness_curve = self.plot_widget.plot(pen=pg.mkPen('r', width=2), name='Avg Fitness')
        
        self.layout.addWidget(self.plot_widget)
        
        self.generations = []
        self.max_fitness = []
        self.avg_fitness = []

    def update_chart(self, generation, max_fit, avg_fit):
        self.generations.append(generation)
        self.max_fitness.append(max_fit)
        self.avg_fitness.append(avg_fit)
        
        self.max_fitness_curve.setData(self.generations, self.max_fitness)
        self.avg_fitness_curve.setData(self.generations, self.avg_fitness)

    def clear(self):
        self.generations = []
        self.max_fitness = []
        self.avg_fitness = []
        self.max_fitness_curve.setData([], [])
        self.avg_fitness_curve.setData([], [])
