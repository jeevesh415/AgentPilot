from abc import ABC, abstractmethod
import random

class Individual(ABC):
    def __init__(self, genes=None):
        self.genes = genes
        self.fitness = 0.0

    @abstractmethod
    def calculate_fitness(self):
        """Calculate and return the fitness of the individual."""
        pass

    @abstractmethod
    def crossover(self, partner):
        """Perform crossover with a partner and return a child."""
        pass

    @abstractmethod
    def mutate(self, mutation_rate):
        """Mutate the individual's genes."""
        pass

    def __lt__(self, other):
        return self.fitness < other.fitness

    def __gt__(self, other):
        return self.fitness > other.fitness
