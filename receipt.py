class HumanStep:
    def __init__(self, attributes):
        self.attributes = attributes

class PreStep:
    pass

class OvenCook:
    def __init__(self, attributes):
        self.attributes = attributes

    def __str__(self):
        return "Oven Cook Step"

class OvenFry:
    def __init__(self, attributes):
        self.attributes = attributes

    def __str__(self):
        return "Oven Fry Step"


class VacuumStep:
    def __init__(self, attributes):
        self.attributes = attributes

    def __str__(self):
        return "Vacuum Step"


class BlastStep:
     def __init__(self, attributes):
        self.attributes = attributes

     def __str__(self):
        return "Vacuum Step"

class PreHeat:
    def __init__(self, attributes, oven_cook):
        self.attributes = attributes
        self.oven_cook = oven_cook

    def __str__(self):
        return "PreHeat Step"