from receipt import *
import networkx as nx
import matplotlib.pyplot as plt
import json, pprint
import warnings


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

    STEP_MAP = {
        "Blast": BLAST_STEP_ID,
        "PreBlast": BLAST_STEP_ID,
        "OvenCook": OVEN_STEP_ID,
        "PreHeat": OVEN_STEP_ID,
        "VacuumStep": VACUUM_STEP_ID,
        "HumanStep": HUMAN_STEP_ID
    }

    def __init__(self, wfcore_path):
        with open(wfcore_path) as f:
            wfcore_json_str = f.read()
            self.wfcore_json = json.loads(wfcore_json_str)
            self.receipe_name = self.wfcore_json["Id"]
            self.step_dict = {}
            self.graph = nx.DiGraph()

            # global variables useful to transform graph in workflow
            self.n_parallels = 0
            self.visited = []
            self.incoming = {}
            self.parallel_index = 0
            self.n_fake = 0
            self.new_json = {}
            self.new_json["Id"] = "New Workflow"
            self.new_json["Version"] = 1
            self.new_json["Steps"] = []


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
            step_duration = step_json["Inputs"]["Duration"]
            if (step_json["StepType"] == self.OVEN_STEP_ID):
                if step_json["Inputs"]["OvenValue1"] == self.PREHEAT_STEP_ID:
                    self.step_dict[step_id] = PreHeat({"receipe": "\"" + self.receipe_name + "\"", "step": "\"" + step_id + "\"", "duration": step_duration}, None)
                else:
                    step_temperature = step_json["Inputs"]["OvenValue2"]
                    self.step_dict[step_id] = OvenCook({"receipe": "\"" + self.receipe_name + "\"", "step": "\"" + step_id + "\"", "duration": step_duration, "temperature": step_temperature})
            elif (step_json["StepType"] == self.BLAST_STEP_ID):
                if step_json["Inputs"]["BlastValue1"] == self.PREBLAST_STEP_ID:
                    self.step_dict[step_id] = PreBlast({"receipe": "\"" + self.receipe_name + "\"", "step": "\"" + step_id + "\"", "duration": step_duration}, None)
                else:
                    step_temperature = step_json["Inputs"]["BlastValue2"]
                    self.step_dict[step_id] = Blast({"receipe": "\"" + self.receipe_name + "\"", "step": "\"" + step_id + "\"", "duration": step_duration, "temperature": step_temperature})
            elif (step_json["StepType"] == self.HUMAN_STEP_ID):
                self.step_dict[step_id] = HumanStep({"receipe": "\"" + self.receipe_name + "\"", "step": "\"" + step_id + "\"", "duration": step_duration})
            elif (step_json["StepType"] == self.VACUUM_STEP_ID):
                self.step_dict[step_id] = VacuumStep({"receipe": "\"" + self.receipe_name + "\"", "step": "\"" + step_id + "\"", "duration": step_duration})

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
            json_step = list(self.get_step_from_id(step_id))[0]
            next_steps_id = self.get_next_steps(json_step)

            for next_step_id in next_steps_id:
                if isinstance(self.step_dict[step_id], PreHeat) and isinstance(self.step_dict[next_step_id], OvenCook):
                    self.step_dict[step_id].attributes["temperature"] = self.step_dict[next_step_id].attributes["temperature"]
                    self.step_dict[step_id].next_step = self.step_dict[next_step_id]
                if isinstance(self.step_dict[step_id], PreBlast) and isinstance(self.step_dict[next_step_id], Blast):
                    self.step_dict[step_id].attributes["temperature"] = self.step_dict[next_step_id].attributes["temperature"]
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


    def create_graph_from_schedule(self, scheduled_graphs):
        """
        Create a new workflow in networkx DiGraph format, starting from
        the output obtained by the scheduler. Currently only supported for
        two workflows.

        Parameters
        ----------
        graph_1: networkx.classes.digraph.DiGraph
            Graph representation of the 1st workflow

        graph_2: networkx.classes.digraph.DiGraph
            Graph representation of the 2nd workflow

        schedule: dict
            Dictionary containing start-times and end-times
            associated to each step of the receipes

        Returns
        -------
        combined_graph: networkx.classes.digraph.DiGraph
            Graph representation of the new worfklow obtained
            after the schedule activity

        """

        starts, ends, machines = {}, {}, {}
        final_graph = nx.DiGraph()

        for scheduled_graph in scheduled_graphs:
            starts[scheduled_graph] = nx.get_node_attributes(scheduled_graph, "start")
            ends[scheduled_graph] = nx.get_node_attributes(scheduled_graph, "end")
            machines[scheduled_graph] = nx.get_node_attributes(scheduled_graph, "resource")

            final_graph = nx.compose(final_graph, scheduled_graph)

        # pprint.pprint(starts)

        for scheduled_graph in scheduled_graphs:
            for scheduled_step in scheduled_graph:
                if (scheduled_graph.in_degree(scheduled_step) != 0):
                    # inter_precedences is True if a precedence among different receipes is found
                    inter_precedences = True
                    for predecessor in scheduled_graph.predecessors(scheduled_step):
                        # if in the schedule a step is immediately preceded by one of the previous step,
                        # it means that there are not inter precedences to add
                        if ends[scheduled_graph][predecessor] == starts[scheduled_graph][scheduled_step] - 1:
                            inter_precedences = False
                    
                    if inter_precedences:
                        # print(scheduled_step)
                        for other_scheduled_graph in scheduled_graphs:
                            if not nx.is_isomorphic(scheduled_graph, other_scheduled_graph):
                                for other_scheduled_step in other_scheduled_graph:
                                    if (ends[other_scheduled_graph][other_scheduled_step] + 1 == starts[scheduled_graph][scheduled_step]
                                        and
                                        machines[other_scheduled_graph][other_scheduled_step] == machines[scheduled_graph][scheduled_step]):
                                        final_graph.add_edge(other_scheduled_step, scheduled_step)

                else:
                    if starts[scheduled_graph][scheduled_step] != 0:
                        for other_scheduled_graph in scheduled_graphs:
                            if not nx.is_isomorphic(scheduled_graph, other_scheduled_graph):
                                for other_scheduled_step in other_scheduled_graph:
                                    if ((ends[other_scheduled_graph][other_scheduled_step] + 1 == starts[scheduled_graph][scheduled_step]
                                         or
                                         ends[other_scheduled_graph][other_scheduled_step] == starts[scheduled_graph][scheduled_step])
                                        and
                                        machines[other_scheduled_graph][other_scheduled_step] == machines[scheduled_graph][scheduled_step]):
                                        print(scheduled_step.attributes["receipe"] + " " + scheduled_step.attributes["step"])
                                        final_graph.add_edge(other_scheduled_step, scheduled_step)

        nx.draw(final_graph, with_labels=True)
        plt.show()
        
        scheduled_json = self.create_json_from_graph(final_graph)

        # pprint.pprint(self.create_json_from_graph(final_graph))

        # pprint.pprint(self.visited)

        with open("new_workflow.json", "w") as f:
            json.dump(scheduled_json, f, indent=4)            
        
    
    def create_json_from_graph(self, graph):

        starting_nodes = self.find_starting_nodes(graph)

        for step in graph:
            self.incoming[step] = sum([len(list(nx.all_simple_paths(graph, starting_step, step))) 
                                       for starting_step in starting_nodes])

        # pprint.pprint(self.incoming)
       
        if len(starting_nodes) == 1:
            json_step, wait_json_step, json_parallel = 0, 0, 0

            json_step, wait_json_step, json_parallel = self.get_json_from_step(starting_nodes[0], list(graph.successors(starting_nodes[0])), graph)
                

            # This condition is not verified if at the beginning there is a parallel after another parallel
            # Check get_parallel_json_step to undestand
            if self.new_json == [] or self.new_json["Steps"][0] != 0: 
                self.new_json["Steps"].append(json_step)
                self.new_json["Steps"].append(wait_json_step)

                if json_parallel:
                    self.new_json["Steps"].append(json_parallel)
            else:
                self.new_json["Steps"][0](json_step)
                self.new_json["Steps"].insert(1, json_step)

                if json_parallel:
                    self.new_json["Steps"].insert(2, json_parallel)

        else:
            json_parallel = self.get_parallel_json_step(starting_nodes, graph)
            self.n_parallels = self.n_parallels + 1
            # This condition is not verified if at the beginning there is a parallel after another parallel
            # Check get_parallel_json_step to undestand
            if self.new_json == [] or self.new_json["Steps"][0] != 0: 
                self.new_json["Steps"].append(json_parallel)
            else:
                self.new_json["Steps"][0] = json_parallel

        for step in graph:
            if not (step in self.visited):
                print(step.attributes["receipe"] + step.attributes["step"])
                json_step, wait_json_step, json_parallel = self.get_json_from_step(step, list(graph.successors(step)), graph)

                self.new_json["Steps"].append(json_step)
                self.new_json["Steps"].append(wait_json_step)
                self.visited.append(step)

                if json_parallel:
                    self.new_json["Steps"].append(json_parallel)

        return self.new_json
            
    def find_starting_nodes(self, graph):
        starting_nodes = []
        for step in graph:
            if graph.in_degree(step) == 0:
                starting_nodes.append(step)
                self.visited.append(step)
        return starting_nodes

    def get_json_from_step(self, step, next_steps, graph):
        
        json_step = {}
        json_step["Id"] = step.attributes["receipe"][:-1] + ";" + step.attributes["step"][1:]
        json_step["StepType"] = self.STEP_MAP[step.__class__.__name__]
        json_step["Inputs"] = step.attributes
        json_step["NextStepId"] = "\"wait_" + json_step["Id"][1:]
        if self.incoming[step] > 1:
            json_step["Inputs"]["Ingoing"] = self.incoming[step]
            json_step["Inputs"]["ParallelIndex"] = self.parallel_index
            self.parallel_index += 1

        wait_json_step = {}
        wait_json_step["Id"] = json_step["NextStepId"]
        wait_json_step["StepType"] = "WorkflowCore.Primitives.WaitFor, WorkflowCore"
        wait_json_step["Inputs"] = {
            "EventName": wait_json_step["Id"],
            "EventKey": wait_json_step["Id"][:-1] + "_key" + "\""
        }

        json_parallel = 0

        if len(next_steps) == 1:
            wait_json_step["NextStepId"] = (next_steps[0].attributes["receipe"][:-1] +
                                            ";" +
                                            next_steps[0].attributes["step"][1:])
        elif len(next_steps) > 1:
            wait_json_step["NextStepId"] = "parallel_" + str(self.n_parallels)
            json_parallel = self.get_parallel_json_step(next_steps, graph)

        
        return json_step, wait_json_step, json_parallel


    def get_parallel_json_step(self, next_steps, graph):
        json_parallel = {
            "Id": "parallel_" + str(self.n_parallels),
            "StepType": "WorkflowCore.Primitives.Sequence, WorkflowCore",
            "Do": [ [] for _ in next_steps ]
        }

        self.n_parallels = self.n_parallels + 1

        for i, next_step in enumerate(next_steps):
            if (not (next_step in self.visited)) or (next_step in self.find_starting_nodes(graph)):
                # print("Parallel")
                # print(next_step.attributes["receipe"] + next_step.attributes["step"])
                json_next_step, json_wait_next_step, other_json_parallel = self.get_json_from_step(next_step, list(graph.successors(next_step)), graph)
                if other_json_parallel and self.new_json["Steps"] != []:
                    self.new_json["Steps"].append(other_json_parallel)
                elif other_json_parallel:
                    self.new_json["Steps"].append(0)
                    self.new_json["Steps"].append(other_json_parallel)
                json_parallel["Do"][i].append(json_next_step)
                json_parallel["Do"][i].append(json_wait_next_step)
                self.visited.append(next_step)
            else:
                fake_activity = {
                    "Id": "\"fake_" + str(self.n_fake) + "\"",
                    "StepType": "WorkflowCore.Steps.FakeStep, ProvaWOrkflowCorewebapp",
                    "NextStepId": next_step.attributes["receipe"][:-1] + ";" + next_step.attributes["step"][1:]
                }
                self.n_fake += 1

                json_parallel["Do"][i].append(fake_activity)

        return json_parallel

    

if __name__ == '__main__':
        wfutils = WFCoreUtils("C:\\Users\\Riccardo Minato\\Desktop\\Universita\\SIAF\\BPMN\\Sous-Vide Lemon Curd_globals.json")
        wfutils.create_graph()

        oven_cook_1 = OvenCook({"receipe": "Ricettona", "step": "oven_1", "duration": 3, "temperature": 120})
        blast_step_1 = Blast({"receipe": "Ricettona", "step": "blast_1", "duration": 4})
        human_step_1 = HumanStep({"receipe": "Ricettona", "step": "human_1", "duration": 6})
        vacuum_1 = VacuumStep({"receipe": "Ricettona", "step": "vacuum_1", "duration": 2})
        human_step_2 = HumanStep({"receipe": "Ricettona", "step": "human_2", "duration": 6})

        g = nx.DiGraph()
        g.add_edge(oven_cook_1, blast_step_1)
        g.add_edge(oven_cook_1, human_step_1)
        g.add_edge(blast_step_1, vacuum_1)
        g.add_edge(human_step_1, vacuum_1)
        g.add_edge(vacuum_1, human_step_2)

        # pprint.pprint(wfutils.create_json_from_graph(g))

        # This function is useful to set the "ingoing" parameter
        for path in nx.all_simple_paths(g, oven_cook_1, vacuum_1): 
            print(path)

        wfutils.create_graph_from_schedule([g])
        # wfutils.draw_graph()

        # print(wfutils.step_dict)
        print("END")

