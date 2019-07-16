class Step:
    def __init__(self, attributes):
        self.attributes = attributes

class HumanStep(Step):
    def __init__(self, attributes):
        super().__init__(attributes)

    def __str__(self):
        return "HumanStep"

class PreStep(Step):
    def __init__(self, attributes, next_step):
        super().__init__(attributes)
        self.next_step = next_step


class OvenStep(Step):
    def __init__(self, attributes):
        super().__init__(attributes)

class BlastStep(Step):
    def __init__(self, attributes):
        super().__init__(attributes)

class OvenCook(OvenStep):
    def __init__(self, attributes):
        super().__init__(attributes)

    def __str__(self):
        return "OvenCook"

class OvenFry(OvenStep):
    def __init__(self, attributes):
        super().__init__(attributes)

    def __str__(self):
        return "OvenFry"


class VacuumStep(Step):
    def __init__(self, attributes):
        super().__init__(attributes)

    def __str__(self):
        return "Vacuum"


class Blast(BlastStep):
     def __init__(self, attributes):
         super().__init__(attributes)

     def __str__(self):
        return "Blast"

class PreHeat(OvenStep):
    def __init__(self, attributes, oven_cook):
        super().__init__(attributes)
        self.oven_cook = oven_cook

    def __str__(self):
        return "PreHeat"

PreHeat({"x": 2}, 3)

'''
Function to obtain how much time should be taken
to pass from temperature t1 to t2
'''
def get_dur_from_temperatures(t1, t2, ):
    return round(abs((t1 - t2) / 5))
