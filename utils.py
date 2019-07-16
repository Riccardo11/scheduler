from receipt import *
import networkx as nx
import matplotlib.pyplot as plt
import json


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
    PREBLAST_STEP_ID = "Preraffreddamento Hard"
    OVEN_STEP_ID = "WorkflowCore.Steps.OvenStep, ProvaWOrkflowCorewebapp"
    PREHEAT_STEP_ID = "Preriscalda"
    VACUUM_STEP_ID = "WorkflowCore.Steps.VacuumStep, ProvaWOrkflowCorewebapp"
    HUMAN_STEP_ID = "WorkflowCore.Steps.HumanStep, ProvaWOrkflowCorewebapp"

    NORMAL_STEP_IDS = [BLAST_STEP_ID, OVEN_STEP_ID, VACUUM_STEP_ID, HUMAN_STEP_ID]

    def __init__(self, wfcore_json_str):
        self.wfcore_json = json.loads(wfcore_json_str)
        self.step_dict = {}


    '''
    Get the json form of a step giving its id
    '''
    def get_step_from_id(self, step_id):
        return self.__get_step_from_id_rec(step_id, self.wfcore_json)

    def __get_step_from_id_rec(self, step_id, json):
        for k, v in self.wfcore_json:
            if k == "Id" and v == step_id:
                return json
            elif isinstance(v, dict):
                return self.__get_step_from_id_rec(step_id, v)
        return 0


    '''
    Get every step as object, associated to its id in workflow
    '''
    def get_steps_objects_from_wf(self):
        step_list = self.wfcore_json["Steps"]

        self.__get_steps_objects_from_wf_rec(step_list)
        

    def __get_steps_objects_from_wf_rec(self, step_json):
        if isinstance(step_json, dict) and step_json["StepType"] in self.NORMAL_STEP_IDS:
            step_id = step_json["Id"]
            if (step_json["StepType"] == self.OVEN_STEP_ID):
                if step_json["Inputs"]["OvenValue1"] == self.PREHEAT_STEP_ID:
                    self.step_dict[step_id] = PreHeat({"duration": 5}, None)
                else:
                    self.step_dict[step_id] = OvenCook({"duration": 4, "temperature": 2})
            elif (step_json["StepType"] == self.BLAST_STEP_ID):
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

        


    '''
    Convert a workflow-core json in a networkx graph
    '''
    # def get_graph_from_json(self):
    #     return self.__get_graph_from_json_rec(self.wfcore_json, nx.DiGraph())

    # def __get_graph_from_json_rec(self, wf_json, graph):
    #     for k, v in wf_json:
    #         if k == "StepType" and (v in self.NORMAL_STEP_IDS):
    #             updated_graph = self.update_graph(wf_json, graph)


    '''
    Add new activities to an existing graph
    '''
    def update_graph(self, wf_json, old_graph):
        if "NextStepId" in wf_json:

            step_type = wf_json["StepType"]
            
            if step_type == self.BLAST_STEP_ID:            
                step_input = wf_json["Inputs"]["BlastValue1"]
                
                if step_input == self.PREBLAST_STEP_ID:
                    wait_preblast_step_id = wf_json["NextStepId"]
                    wait_preblast_step_json = self.get_step_from_id(wait_preblast_step_id)
                    blast_step_id = wait_preblast_step_json["NextStepId"]
                    blast_step_json = self.get_step_from_id(blast_step_id)

                    blast_step = BlastStep({"duration": 5})
                    preblast_step = PreBlast({"duration": 6}, blast_step)



    '''
    Obtain the object representation of a step
    '''
    def get_step_from_json(self, json_step):
        step_type = json_step["StepType"]

        if step_type == self.BLAST_STEP_ID:            
            step_input = json_step["Inputs"]["BlastValue1"]
            
            if step_input == self.PREBLAST_STEP_ID:
                wait_preblast_step = json_step["NextStepId"]
                wait_preblast_step_json = self.get_step_from_id(wait_preblast_step)
                blast_step = wait_preblast_step_json["NextStepId"]
                blast_step_json = self.get_step_from_id(blast_step)


if __name__ == '__main__':
    with open("C:\\Users\\Riccardo Minato\\Desktop\\Universita\\SIAF\\BPMN\\Bistecca Perfetta.json", "r") as f:
        wf_json = f.read()
        wfutils = WFCoreUtils(wf_json)
        wfutils.get_steps_objects_from_wf()

        print(wfutils.step_dict)

