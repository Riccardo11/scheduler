import copy

class Step:
    def __init__(self, attributes):
        self.attributes = attributes

    def __str__(self):
        r = ""
        if self.attributes["receipe"] == '"Sous-Vide_Lemon_Curd"':
            r = "S"
        elif self.attributes["receipe"] == '"Bistecca_Perfetta"':
            r = "B"
        else:
            return self.attributes["receipe"] + ";" + self.attributes["step"]
        return r + ";" + self.attributes["step"]

    # def __eq__(self, other):
    #     if isinstance(other, self.__class__):
    #         return self.attributes == other.attributes
    #     else:
    #         return False

    # def __hash__(self):
    #     return hash(frozenset(self.attributes.items()))


class FakeActivity(Step):
    def __init__(self, attributes):
        super().__init__(attributes)


class HumanStep(Step):
    def __init__(self, attributes):
        super().__init__(attributes)

    # def __str__(self):
    #     return "HumanStep"

class PreStep(Step):
    def __init__(self, attributes, next_step):
        super().__init__(attributes)
        self.next_step = next_step

    # def __eq__(self, other):
    #     if isinstance(other, self.__class__):
    #         return (self.attributes == other.attributes
    #                 and
    #                 self.next_step == other.next_step)
    #     else:
    #         return False

    # def __hash__(self):
    #     hashable_dict = copy.copy(self.attributes)
    #     hashable_dict["next"] = self.next_step
    #     return hash(frozenset(hashable_dict.items()))


class OvenStep(Step):
    def __init__(self, attributes):
        super().__init__(attributes)

class BlastStep(Step):
    def __init__(self, attributes):
        super().__init__(attributes)

class OvenCook(OvenStep):
    def __init__(self, attributes):
        super().__init__(attributes)

    # def __str__(self):
    #     return "OvenCook"

class OvenFry(OvenStep):
    def __init__(self, attributes):
        super().__init__(attributes)

    # def __str__(self):
    #     return "OvenFry"


class VacuumStep(Step):
    def __init__(self, attributes):
        super().__init__(attributes)

    # def __str__(self):
    #     return "Vacuum"


class PreBlast(PreStep, BlastStep):
    def __init__(self, attirbutes, blast):
        super().__init__(attirbutes, blast)

    # def __str__(self):
    #     return "Preblast"

class Blast(BlastStep):
     def __init__(self, attributes):
         super().__init__(attributes)

    #  def __str__(self):
    #     return "Blast"

class PreHeat(PreStep, OvenStep):
    def __init__(self, attributes, oven_cook):
        super().__init__(attributes, oven_cook)

    # def __str__(self):
    #     return "PreHeat"

'''
Function to obtain how much time should be taken
to pass from temperature t1 to t2
'''
def get_dur_from_temperatures(t1, t2, ):
    return round(abs((t1 - t2) / 5))
