class Machine:
    def __init__(self, capacity):
        self.capacity = capacity


class Oven(Machine):
    def __init__(self, capacity, max_temperature, can_fry):
        super().__init__(capacity)
        self.max_temperature = max_temperature
        self.can_fry = can_fry

class BlastChiller(Machine):
    pass


class VacuumMachine(Machine):
    pass
