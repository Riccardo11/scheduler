class StepReceipt:
    def __init__(self, duration):
        self.duration = duration


class OvenCook(StepReceipt):
    def __init__(self, duration, min_temperature, max_temperature):
        super().__init__(duration)
        self.min_temperature = min_temperature
        self.max_temperature = max_temperature

    def __str__(self):
        return "Oven Cook Step"

class OvenFry(StepReceipt):
    
    def __str__(self):
        return "Oven Fry Step"


class VacuumStep(StepReceipt):
    
    def __str__(self):
        return "Vacuum Step"


class BlastStep(StepReceipt):
     
     def __str__(self):
        return "Vacuum Step"