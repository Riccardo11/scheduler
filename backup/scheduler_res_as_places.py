'''
This version of the scheduler is intended to provide a scheduling
of the receipts, considering the resources as the number of free
spaces, rather than the physical machines. The key idea is that
we consider three different resources, with a capacity equal to
the sum of all similar resources (Ovens, Blast Chillers and Vacuum
Machines). With this approach, a post-processing phase will be
needed.

The reason why we're trying this is that the cumulative global
constraint assumes that every step can be assigned to only one resource.
'''

from ortools.sat.python import cp_model
import collections
from receipt import BlastStep, OvenCook, OvenFry, VacuumStep
from machine import BlastChiller, Oven, VacuumMachine


class VarArrayAndObjectiveSolutionPrinter(cp_model.CpSolverSolutionCallback):
    """Print intermediate solutions."""

    def __init__(self, variables):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self.__variables = variables
        self.__solution_count = 0

    def on_solution_callback(self):
        print('Solution %i' % self.__solution_count)
        print('  objective value = %i' % self.ObjectiveValue())
        for v in self.__variables:
            print('  %s = %i' % (v, self.Value(v)), end=' ')
        print()
        self.__solution_count += 1

    def solution_count(self):
        return self.__solution_count


# Some useful types used below
step_type = collections.namedtuple('step_type', 'start end interval')
assigned_step_type = collections.namedtuple('assigned_step_type',
                                            'start receipt index')


# Ricetta: composta da step che consistono di 
# durata e capabilities richieste
# receipts_old = [
#     [(3, [0,3]), (4, [2])],
#     [(2, [0,3]), (2, [0,3]), (4, [1])],
#     [(2, [3])]
# ]

receipts = [
    [OvenCook(3, 120, 150), BlastStep(4)],
    [OvenCook(2, 100, 130), VacuumStep(4)],
    [OvenCook(2, 50, 90)]
]

# receipts_clusters = {
#     "OvenCook": [step for receipt in receipts for step in receipt if isinstance(step, OvenCook)],
#     "BlastStep": [step for receipt in receipts for step in receipt if isinstance(step, BlastStep)],
#     "VacuumStep": [step for receipt in receipts for step in receipt if isinstance(step, VacuumStep)]
# }

EOH = sum([step.duration for receipt in receipts for step in receipt])
print("End of Horizon: %i" % EOH)

# Macchine: composte da capacità e capabilities
# machines_old = [(1,[2]), (1,[1,2]), (2,[3])]

machines = [Oven(1, 0, 300, False), Oven(2, 0, 250, True), Oven(1, 0, 300, True), BlastChiller(2), VacuumMachine(2)]
resources = { "Oven": Oven(0, 0, 0, False), "BlastChiller": BlastChiller(0), "VacuumMachine": VacuumMachine(0) }
for machine in machines:
    machine_name = type(machine).__name__
    resources[machine_name].capacity = resources[machine_name].capacity + machine.capacity
    if isinstance(machine, Oven):
        if machine.max_temperature > resources["Oven"].max_temperature:
            resources["Oven"].max_temperature = machine.max_temperature
        if machine.can_fry:
            resources["Oven"].can_fry = True

def SIAF_scheduler():
    # create the model
    model = cp_model.CpModel()

    # It will contain every task in their interval representation
    all_steps = {}

    # It will contain every machine variable
    all_machines = {}

    # Create variables
    for rec_id, receipt in enumerate(receipts):
        for step_id, step in enumerate(receipt):
            duration = step.duration
            # each step can start in every moment
            start_var = model.NewIntVar(0, EOH, 'start_%i_%i' % (rec_id, step_id))
            
            # each step can end in every moment
            end_var = model.NewIntVar(0, EOH, 'end_%i_%i' % (rec_id, step_id))

            # interval variable
            interval_var = model.NewIntervalVar(
                start_var, duration, end_var, 'interval_%i_%i' % (rec_id, step_id)
            )

            # update the task dictionary
            all_steps[rec_id, step_id] = step_type(
                start=start_var, end=end_var, interval=interval_var)

            # What machines can be used for the current step?
            # compatible_machines = []
            # for m_id, machine in enumerate(machines):
            #     if set(step[1]).issubset(machine[1]):
            #         compatible_machines.append(m_id)

            compatible_machines = find_compatible_machines(step)
            # machine variable
            machine_var = model.NewEnumeratedIntVar(
                create_flatten_domain(compatible_machines), 
                'machine_%i_%i' % (rec_id, step_id)
            )
            all_machines[rec_id, step_id] = machine_var

    # Constraints definition

    # Precedence constraints
    for rec_id, receipt in enumerate(receipts):
        for step_id in range(len(receipt) - 1):
            model.Add(
                all_steps[(rec_id, step_id+1)].start
                >
                all_steps[(rec_id, step_id)].end
            )

    # Cumulative constraints
    for m_id, machine in enumerate(machines):
        interval_list = []
        for rec_id, receipt in enumerate(receipts):
            for step_id, step in enumerate(receipt):
                # if set(step[1]).issubset(machine[1]):
                if m_id in find_compatible_machines(step):
                    interval_list.append(all_steps[(rec_id, step_id)].interval)
        # for rec_id, receipt in enumerate(receipts):
            # interval_list = [all_steps[(rec_id, step_id)].interval for step_id in range(len(receipt))]
        model.AddCumulative(interval_list, [1]*len(interval_list), 2)

    model.Add(all_machines[(2,0)] != 0)        

    # Objective function
    # Our goal is to minimize the makespan, that is the total time of execution
    obj_var = model.NewIntVar(0, EOH, 'makespan')
    model.AddMaxEquality(
        obj_var,
        [all_steps[(rec_id, len(receipts[rec_id]) - 1)].end for rec_id in range(len(receipts))]
    )
    model.Minimize(obj_var)

    
    # Solve model
    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    print("Status of the solver: %i" % status)
        
    # Display results

    # Print makespan
    print("Optimal Schedule Length: %i" % solver.ObjectiveValue())
    print()

    # Create one list of assigned steps per machine
    assigned_receipts = [[] for _ in range(len(machines))]
    for rec_id, receipt in enumerate(receipts):
        for step_id, step in enumerate(receipt):
            machine = solver.Value(all_machines[(rec_id, step_id)])
            assigned_receipts[machine].append(
                assigned_step_type(
                    start=solver.Value(all_steps[(rec_id, step_id)].start),
                    receipt=rec_id,
                    index=step_id
                )
            )

    disp_col_width = 10
    sol_line = ''
    sol_line_steps = ''

    print('Optimal Schedule', '\n')

    for i in range(len(machines)):
        # Sort by starting time.
        assigned_receipts[i].sort()
        sol_line += 'Machine ' + str(i) + ': '
        sol_line_steps += 'Machine ' + str(i) + ': '

        for assigned_step in assigned_receipts[i]:
            name = 'step_%i_%i' % (assigned_step.receipt, assigned_step.index)
            # Add spaces to output to align columns.
            sol_line_steps += name + ' ' * (disp_col_width - len(name))
            start = assigned_step.start
            duration = receipts[assigned_step.receipt][assigned_step.index].duration

            sol_tmp = '[%i,%i]' % (start, start + duration)
            # Add spaces to output to align columns.
            sol_line += sol_tmp + ' ' * (disp_col_width - len(sol_tmp))

        sol_line += '\n'
        sol_line_steps += '\n'

    print(sol_line_steps)
    print('Step Time Intervals\n')
    print(sol_line)
    print()


# Function required to provide the (improbable) right input format to NewEnumeratedIntVar
def create_flatten_domain(compatible_machines):
    flatten_domain = []
    for i, machine_id in enumerate(compatible_machines):
        if i == 0:
            flatten_domain.append(machine_id)

        if i == len(compatible_machines)-1:
            flatten_domain.append(machine_id)
            return flatten_domain

        if machine_id+1 != compatible_machines[i+1]:
            flatten_domain.append(machine_id)
            flatten_domain.append(compatible_machines[i+1])

    # never used
    return flatten_domain


def find_compatible_machines(step):
    if isinstance(step, OvenCook):
        return [m_id 
                for m_id, machine in enumerate(machines)
                if isinstance(machine, Oven) and
                   machine.min_temperature <= step.min_temperature and
                   machine.max_temperature >= step.max_temperature]
    elif isinstance(step, VacuumStep):
        return [m_id for m_id, machine in enumerate(machines) if isinstance(machine, VacuumMachine)]
    elif isinstance(step, BlastStep):
        return [m_id for m_id, machine in enumerate(machines) if isinstance(machine, BlastChiller)]
    elif isinstance(step, OvenFry):
        return [m_id for m_id, machine in enumerate(machines) if isinstance(machine, Oven) and
                                                                 machine.can_fry]

    return []


if __name__ == '__main__':
    SIAF_scheduler()
