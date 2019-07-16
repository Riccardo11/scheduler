class Machine:
    def __init__(self, capacity):
        self.capacity = capacity


class Oven(Machine):
    def __init__(self, capacity, max_temperature, can_fry):
        super().__init__(capacity)
        self.max_temperature = max_temperature
        self.can_fry = can_fry

    def __str__(self):
        return "Oven"

class BlastChiller(Machine):

    def __str__(self):
        return "Blast"
    pass


class VacuumMachine(Machine):
    def __str__(self):
        return "Vacuum"
    pass

class Human(Machine):
    def __str__(self):
        return "Chef"
    pass
