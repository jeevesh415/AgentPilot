import random
from PySide6.QtCore import QObject, Signal

class GeneticAlgorithm(QObject):
    generation_completed = Signal(int, float, float, object) # generation, max_fitness, avg_fitness, best_individual

    def __init__(self, population_size, mutation_rate, elitism, individual_class, **kwargs):
        super().__init__()
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.elitism = elitism
        self.individual_class = individual_class
        self.kwargs = kwargs
        self.population = []
        self.generation = 0
        self.running = False

    def initialize_population(self):
        self.population = [self.individual_class.create_random(**self.kwargs) for _ in range(self.population_size)]
        self.generation = 0
        self.evaluate_fitness()

    def evaluate_fitness(self):
        for ind in self.population:
            ind.calculate_fitness()

    def step(self):
        if not self.population:
            return

        # Selection (Tournament)
        new_population = []
        
        # Elitism
        if self.elitism:
            # Sort by fitness descending
            sorted_pop = sorted(self.population, key=lambda x: x.fitness, reverse=True)
            new_population.extend(sorted_pop[:max(1, int(self.population_size * 0.05))]) # Keep top 5% or at least 1

        while len(new_population) < self.population_size:
            parent1 = self.tournament_selection()
            parent2 = self.tournament_selection()
            child = parent1.crossover(parent2)
            child.mutate(self.mutation_rate)
            child.calculate_fitness()
            new_population.append(child)

        self.population = new_population
        self.generation += 1

        # Stats
        best_ind = max(self.population, key=lambda x: x.fitness)
        avg_fitness = sum(ind.fitness for ind in self.population) / len(self.population)
        
        self.generation_completed.emit(self.generation, best_ind.fitness, avg_fitness, best_ind)

    def tournament_selection(self, k=3):
        tournament = random.sample(self.population, k)
        return max(tournament, key=lambda x: x.fitness)

    def run(self, max_generations=1000):
        self.running = True
        while self.running and self.generation < max_generations:
            self.step()
            # In a real UI loop, we'd process events here or run this in a thread
