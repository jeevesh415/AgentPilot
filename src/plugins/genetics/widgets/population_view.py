from PySide6.QtWidgets import QVBoxLayout, QLabel
from gui.widgets.config_widget import ConfigWidget
import pyqtgraph as pg

class PopulationView(ConfigWidget):
    def __init__(self, parent):
        super().__init__(parent=parent)
        self.layout = QVBoxLayout(self)
        
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('w')
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.setAspectLocked(True)
        self.plot_widget.hideAxis('left')
        self.plot_widget.hideAxis('bottom')
        self.plot_widget.enableAutoRange()
        
        self.path_curve = self.plot_widget.plot(pen=pg.mkPen('b', width=2))
        self.cities_scatter = self.plot_widget.plot(pen=None, symbol='o', symbolBrush='r', symbolSize=10)
        
        self.layout.addWidget(self.plot_widget)
        
        self.cities = []

    def set_cities(self, cities):
        print(f"PopulationView.set_cities: {len(cities)} cities")
        self.cities = cities
        x = [c[0] for c in cities]
        y = [c[1] for c in cities]
        self.cities_scatter.setData(x, y)
        self.plot_widget.autoRange()

    def update_view(self, best_individual):
        if not self.cities:
            print("PopulationView.update_view: No cities set")
            return
            
        path_indices = best_individual.genes
        print(f"PopulationView.update_view: Path indices: {len(path_indices)}")
        path_x = [self.cities[i][0] for i in path_indices]
        path_y = [self.cities[i][1] for i in path_indices]
        
        # Close the loop
        path_x.append(path_x[0])
        path_y.append(path_y[0])
        
        self.path_curve.setData(path_x, path_y)
        # self.plot_widget.autoRange()

    def clear(self):
        self.path_curve.setData([], [])
        self.cities_scatter.setData([], [])
