import random
import math
from ..core.individual import Individual
from ..widgets.population_view import PopulationView
from PySide6.QtWidgets import QWidget

class TravellingSalesman:
    def __init__(self):
        self.cities = []

    def create_individual(self, **kwargs):
        return TSPIndividual(cities=self.cities, **kwargs)

    def setup(self):
        # Generate random cities
        self.cities = [(random.uniform(0, 100), random.uniform(0, 100)) for _ in range(20)]
        return self.cities

    def get_visualization_widget(self, parent=None):
        return PopulationView(parent)

    def update_visualization(self, widget, best_individual):
        # print(f"Controller update_viz: widget={widget}, cities={len(self.cities)}")
        if hasattr(widget, 'set_cities') and hasattr(widget, 'update_view'):
            if not getattr(widget, 'cities', []) and self.cities:
                 widget.set_cities(self.cities)
            widget.update_view(best_individual)
        else:
            print(f"Widget {widget} does not have required methods")

class TSPIndividual(Individual):
    def __init__(self, genes=None, cities=None):
        super().__init__(genes)
        self.cities = cities
        if self.genes is None and self.cities is not None:
            self.genes = list(range(len(self.cities)))
            random.shuffle(self.genes)

    @classmethod
    def create_random(cls, cities, **kwargs):
        return cls(cities=cities)

    def calculate_fitness(self):
        distance = 0
        for i in range(len(self.genes)):
            city_a = self.cities[self.genes[i]]
            city_b = self.cities[self.genes[(i + 1) % len(self.genes)]]
            distance += math.hypot(city_a[0] - city_b[0], city_a[1] - city_b[1])
        
        self.fitness = 1 / distance if distance > 0 else 0
        return self.fitness

    def crossover(self, partner):
        # Ordered Crossover (OX1)
        size = len(self.genes)
        start, end = sorted(random.sample(range(size), 2))
        
        child_genes = [None] * size
        child_genes[start:end] = self.genes[start:end]
        
        current_pos = end
        for gene in partner.genes:
            if gene not in child_genes:
                if current_pos >= size:
                    current_pos = 0
                while child_genes[current_pos] is not None:
                    current_pos += 1
                    if current_pos >= size:
                        current_pos = 0
                child_genes[current_pos] = gene
                
        return TSPIndividual(genes=child_genes, cities=self.cities)

    def mutate(self, mutation_rate):
        for i in range(len(self.genes)):
            if random.random() < mutation_rate:
                j = random.randint(0, len(self.genes) - 1)
                self.genes[i], self.genes[j] = self.genes[j], self.genes[i]
