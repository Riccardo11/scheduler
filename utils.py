from receipt import *
import networkx as nx
import matplotlib.pyplot as plt
import json, pprint


def read_steps(filepath):
    '''
    The first line of the file should contain each step in the receipe, divided with a ",",
    where presteps are immediately **preceded** by their next step
    '''
    with open(filepath, "r") as f:
        steps = f.readline()
        step_list = steps.split(",")
        step_list = [step.strip() for step in step_list]

        step_dict = get_steps_objects(step_list)
        return step_dict


def create_graph(filepath):
    '''
    Given the filepath containing the receipe, it returns the networkx digraph
    '''
    step_dict = read_steps(filepath)
    g = nx.DiGraph()
    with open(filepath, "r") as f:
        for _ in range(2):
            f.readline()
        for line in f:
            link = line.split()

            source = link[0].split("_")[0] + link[0].split("_")[1]
            dest = link[1].split("_")[0] + link[1].split("_")[1]

            g.add_edge(step_dict[source], step_dict[dest])

    nx.draw(g, with_labels=True)
    plt.show()

    return step_dict, g


def get_steps_objects(step_list):
    '''
    Translate the string format of the elements of a step list in thier corresponding objects
    '''
    step_dict = {}
    for step_str in step_list:
        step_attributes = step_str.split("_")

        step_type = step_attributes[0]
        step_id = step_attributes[1]
        step_duration = int(step_attributes[2])

        if step_type == "oc":
            temperature = int(step_attributes[3])
            step_dict[step_type + step_id] = OvenCook(
                                                {
                                                    "duration": step_duration,
                                                    "temperature": temperature
                                                })
        elif step_type == "ph":
            temperature = step_dict["oc" + step_id].attributes["temperature"]
            step_dict[step_type + step_id] = PreHeat(
                                                {
                                                    "duration": step_duration,
                                                    "temperature": temperature
                                                },
                                                step_dict["oc" + step_id])
        elif step_type == "bs":
            step_dict[step_type + step_id] = Blast({"duration": step_duration})
        elif step_type == "pb":
            step_dict[step_type + step_id] = PreBlast({"duration": step_duration},
                                                      step_dict["bs" + step_id])
        elif step_type == "h":
            step_dict[step_type + step_id] = HumanStep({"duration": step_duration})
        elif step_type == "v":
            step_dict[step_type + step_id] = VacuumStep({"duration": step_duration})
        else:
            return Exception("Error: Step not recognized")

    return step_dict


class WFCoreUtils:

    BLAST_STEP_ID = "WorkflowCore.Steps.BlastStep, ProvaWOrkflowCorewebapp"
    PREBLAST_STEP_ID = "\"Preraffreddamento Hard\""
    OVEN_STEP_ID = "WorkflowCore.Steps.OvenStep, ProvaWOrkflowCorewebapp"
    PREHEAT_STEP_ID = "\"Preriscalda\""
    VACUUM_STEP_ID = "WorkflowCore.Steps.VacuumStep, ProvaWOrkflowCorewebapp"
    HUMAN_STEP_ID = "WorkflowCore.Steps.HumanStep, ProvaWOrkflowCorewebapp"

    NORMAL_STEP_IDS = [BLAST_STEP_ID, OVEN_STEP_ID, VACUUM_STEP_ID, HUMAN_STEP_ID]

    def __init__(self, wfcore_path):
        with open(wfcore_path) as f:
            wfcore_json_str = f.read()
            self.wfcore_json = json.loads(wfcore_json_str)
            self.step_dict = {}
            self.graph = nx.DiGraph()


    '''
    Get the json form of a step giving its id
    '''
    def get_step_from_id(self, step_id):
        # step_list = self.wfcore_json["Steps"]
        return self.__get_step_from_id_rec(step_id, self.wfcore_json)

    def __get_step_from_id_rec(self, step_id, json):
        for k, v in (json.items() if isinstance(json, dict) else
                     enumerate(json) if isinstance(json, list) else []):
            if k == "Id" and v == step_id:
                yield json
            elif isinstance(v, (dict, list)):
                for result in self.__get_step_from_id_rec(step_id, v):
                    yield result


    '''
    Get every step as object, associated to its id in workflow
    '''
    def get_steps_objects_from_wf(self):
        step_list = self.wfcore_json["Steps"]

        self.__get_steps_objects_from_wf_rec(step_list)

        for step_id, step_obj in self.step_dict.items():
            if isinstance(step_obj, PreStep):
                splitted_id = step_id.split("_")
                next_step_id = self.step_dict[splitted_id[0] + "_" + str(int(splitted_id[1]) + 1)]
                step_obj.next_step = next_step_id
        

    def __get_steps_objects_from_wf_rec(self, step_json):
        if isinstance(step_json, dict) and step_json["StepType"] in self.NORMAL_STEP_IDS:
            step_id = step_json["Id"]
            if (step_json["StepType"] == self.OVEN_STEP_ID):
                if step_json["Inputs"]["OvenValue1"] == self.PREHEAT_STEP_ID:
                    self.step_dict[step_id] = PreHeat({"duration": 5}, None)
                else:
                    self.step_dict[step_id] = OvenCook({"duration": 4, "temperature": 2})
            elif (step_json["StepType"] == self.BLAST_STEP_ID):
                if step_json["Inputs"]["BlastValue1"] == self.PREBLAST_STEP_ID:
                    self.step_dict[step_id] = PreBlast({"duration": 5}, None)
                else:
                    self.step_dict[step_id] = Blast({"duration": 4})
            elif (step_json["StepType"] == self.HUMAN_STEP_ID):
                self.step_dict[step_id] = HumanStep({"duration": 4})
            elif (step_json["StepType"] == self.VACUUM_STEP_ID):
                self.step_dict[step_id] = VacuumStep({"duration": 4})

        elif isinstance(step_json, list):
            for step in step_json:
                self.__get_steps_objects_from_wf_rec(step)
        else:
            for _, v in step_json.items():
                if isinstance(v, list):
                    self.__get_steps_objects_from_wf_rec(v)

        
    def create_graph(self):
        self.get_steps_objects_from_wf()
        for step_id in self.step_dict:
            print(step_id)
            json_step = list(self.get_step_from_id(step_id))[0]
            # print(x)
            next_steps_id = self.get_next_steps(json_step)

            for next_step_id in next_steps_id:
                if isinstance(self.step_dict[step_id], PreHeat) and isinstance(self.step_dict[next_step_id], OvenCook):
                    self.step_dict[step_id].attributes["temperature"] = self.step_dict[next_step_id].attributes["temperature"]
                    self.step_dict[step_id].next_step = self.step_dict[next_step_id]
                if isinstance(self.step_dict[step_id], PreBlast) and isinstance(self.step_dict[next_step_id], Blast):
                    self.step_dict[step_id].next_step = self.step_dict[next_step_id]
                self.graph.add_edge(self.step_dict[step_id], self.step_dict[next_step_id])

        return self.graph

    def draw_graph(self):
        nx.draw(self.graph, with_labels=True)
        plt.show()


    def get_next_steps(self, step_json):

        if "NextStepId" in step_json:
            wait_step = list(self.get_step_from_id(step_json["NextStepId"]))[0]

            if "NextStepId" in wait_step:
                step_after_wait = list(self.get_step_from_id(wait_step["NextStepId"]))[0]

                if step_after_wait["StepType"] in self.NORMAL_STEP_IDS:
                    return [step_after_wait["Id"]]
                elif step_after_wait["StepType"] == "WorkflowCore.Primitives.Sequence, WorkflowCore":
                    next_step_list_json = step_after_wait["Do"]
                    next_steps = []
                    # prendere i primi elementi delle liste
                    for next_step_json_ann_list in next_step_list_json:
                        next_steps.append(next_step_json_ann_list[0]["Id"])
                    return next_steps
        return []


if __name__ == '__main__':
        wfutils = WFCoreUtils("C:\\Users\\Riccardo Minato\\Desktop\\Universita\\SIAF\\BPMN\\Sous-Vide Lemon Curd_globals.json")
        wfutils.create_graph()
        wfutils.draw_graph()

        # print(wfutils.step_dict)
        print("END")

