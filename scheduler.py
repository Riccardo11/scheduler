from ortools.sat.python import cp_model
import collections
from receipt import *
from machine import BlastChiller, Oven, VacuumMachine, Human
import warnings

# Some useful types used below
step_type = collections.namedtuple('step_type', 'start duration end interval')
assigned_step_type = collections.namedtuple('assigned_step_type',
                                            'start duration receipt index')


# Ricetta: composta da step che consistono di 
# durata e capabilities richieste
# receipts_old = [
#     [(3, [0,3]), (4, [2])],
#     [(2, [0,3]), (2, [0,3]), (4, [1])],
#     [(2, [3])]
# ]

oven_cook = OvenCook({"duration": 3, "temperature": 120})
oven_cook_1 = OvenCook({"duration": 3, "temperature": 120})

receipts = [
    # [OvenCook({"duration": 1, "temperature": 150})],#, OvenCook({"duration": 3, "temperature": 150}), BlastStep({"duration": 3})],
    [PreHeat({"duration": 6, "temperature": 120}, oven_cook), oven_cook],# OvenCook({"duration": 2, "temperature": 75}), VacuumStep({"duration": 5})],
    [PreHeat({"duration": 6, "temperature": 120}, oven_cook_1), oven_cook_1] #, VacuumStep({"duration": 2})]
]

N_STEPS = 0
for receipt in receipts:
    for step in receipt:
        N_STEPS = N_STEPS+1

EOH = sum([step.attributes["duration"] for receipt in receipts for step in receipt]) + sum([1]*N_STEPS)
print("End of Horizon (Upper Bound): %i" % EOH)

lb = 0
for receipt in receipts:
    dur_receipt = 0
    for step in receipt:
        dur_receipt += step.attributes["duration"]+1
    if dur_receipt > lb:
        lb = dur_receipt

print("Lower Bound: %i" % (lb-1))

# Macchine: composte da capacità e capabilities
# machines_old = [(1,[2]), (1,[1,2]), (2,[3])]

machines = [Oven(1, 300, True), BlastChiller(2), VacuumMachine(1)]

def SIAF_scheduler():
    # create the model
    model = cp_model.CpModel()

    # It will contain every task in their interval representation
    all_steps = {}
    all_steps_start_literals = {}
    all_steps_dur_literals = {}

    # It will contain every machine variable
    all_machines = {}

    # interval variables for fry steps
    all_fries = {}

    # interval variables for cooking steps
    all_cooks = {}

    # Create variables
    for rec_id, receipt in enumerate(receipts):
        for step_id, step in enumerate(receipt):

            compatible_machines = find_compatible_machines(step)
            for compatible_machine in compatible_machines:

                if isinstance(machines[compatible_machine], Oven):

                    for is_frying in range(2):

                        duration_var = 0
                        if step.attributes["duration"] == 1:
                            duration_var = model.NewEnumeratedIntVar([0, 1], 
                                                      'duration_%i_%i__m_%i_f_%i' % (rec_id, step_id, compatible_machine, is_frying))
                        else:
                            duration_var = model.NewEnumeratedIntVar([0,0, step.attributes["duration"],step.attributes["duration"]], 
                                                                     'duration_%i_%i__m_%i_f_%i' % (rec_id, step_id, compatible_machine, is_frying))

                        # Creation of boolean variables as support: if dur_literal is True, then duration > 0
                        dur_literal = model.NewBoolVar('b_dur_%i_%i__m_%i_f_%i' % (rec_id, step_id, compatible_machine, is_frying))
                        all_steps_dur_literals[rec_id, step_id, compatible_machine, is_frying] = dur_literal
                        model.Add(duration_var > 0).OnlyEnforceIf(dur_literal)

                        # each step can start in every moment
                        start_var = model.NewIntVar(-1, EOH, 'start_%i_%i__m_%i_f_%i' % (rec_id, step_id, compatible_machine, is_frying))

                        # Creation of boolean variables as support: if start_literal is True, then start time > -1
                        start_literal = model.NewBoolVar('b_start_%i_%i__m_%i_f_%i' % (rec_id, step_id, compatible_machine, is_frying))
                        all_steps_start_literals[rec_id, step_id, compatible_machine, is_frying] = start_literal
                        model.Add(start_var > -1).OnlyEnforceIf(start_literal)
                        
                        # each step can end in every moment
                        end_var = model.NewIntVar(-1, EOH, 'end_%i_%i__m_%i_f_%i' % (rec_id, step_id, compatible_machine, is_frying))

                        # interval variable
                        interval_var = model.NewIntervalVar(
                            start_var, duration_var, end_var, 'interval_%i_%i__m_%i_f_%i' % (rec_id, step_id, compatible_machine, is_frying)
                        )

                        if isinstance(step, OvenCook):
                            if not compatible_machine in all_cooks:
                                all_cooks[compatible_machine] = []
                            all_cooks[compatible_machine].append(interval_var)
                        elif isinstance(step, OvenFry):
                            if not compatible_machine in all_fries:
                                all_fries[compatible_machine] = []
                            all_fries[compatible_machine].append(interval_var)

                        # update the task dictionary
                        all_steps[rec_id, step_id, compatible_machine, is_frying] = step_type(
                            start=start_var, duration=duration_var, end=end_var, interval=interval_var)

                        # What machines can be used for the current step?
                        # compatible_machines = []
                        # for m_id, machine in enumerate(machines):
                        #     if set(step[1]).issubset(machine[1]):
                        #         compatible_machines.append(m_id)

                        # machine variables
                        machine_var = model.NewBoolVar( 
                            'machine_%i_%i__m_%i_f_%i' % (rec_id, step_id, compatible_machine, is_frying)
                        )
                        all_machines[rec_id, step_id, compatible_machine, is_frying] = machine_var
                else:

                    duration_var = 0
                    if step.attributes["duration"] == 1:
                        duration_var = model.NewEnumeratedIntVar([0, 1], 
                                                                 'duration_%i_%i__m_%i' % (rec_id, step_id, compatible_machine))
                    else:
                        duration_var = model.NewEnumeratedIntVar([0,0, step.attributes["duration"],step.attributes["duration"]], 
                                                                 'duration_%i_%i__m_%i' % (rec_id, step_id, compatible_machine))

                    # Creation of boolean variables as support: if dur_literal is True, then duration > 0
                    dur_literal = model.NewBoolVar('b_dur_%i_%i__m_%i' % (rec_id, step_id, compatible_machine))
                    all_steps_dur_literals[rec_id, step_id, compatible_machine] = dur_literal
                    model.Add(duration_var > 0).OnlyEnforceIf(dur_literal)

                    # each step can start in every moment
                    start_var = model.NewIntVar(-1, EOH, 'start_%i_%i__m_%i' % (rec_id, step_id, compatible_machine))

                    # Creation of boolean variables as support: if start_literal is True, then start time > -1
                    start_literal = model.NewBoolVar('b_start_%i_%i__m_%i' % (rec_id, step_id, compatible_machine))
                    all_steps_start_literals[rec_id, step_id, compatible_machine] = start_literal
                    model.Add(start_var > -1).OnlyEnforceIf(start_literal)
                    
                    # each step can end in every moment
                    end_var = model.NewIntVar(-1, EOH, 'end_%i_%i__m_%i' % (rec_id, step_id, compatible_machine))

                    # interval variable
                    interval_var = model.NewIntervalVar(
                        start_var, duration_var, end_var, 'interval_%i_%i__m_%i' % (rec_id, step_id, compatible_machine)
                    )

                    # update the task dictionary
                    all_steps[rec_id, step_id, compatible_machine] = step_type(
                        start=start_var, duration=duration_var, end=end_var, interval=interval_var)

                    # What machines can be used for the current step?
                    # compatible_machines = []
                    # for m_id, machine in enumerate(machines):
                    #     if set(step[1]).issubset(machine[1]):
                    #         compatible_machines.append(m_id)

                    # machine variables
                    machine_var = model.NewBoolVar( 
                        'machine_%i_%i__m_%i' % (rec_id, step_id, compatible_machine)
                    )
                    all_machines[rec_id, step_id, compatible_machine] = machine_var 

    # Constraints definition

    # Precedence constraints
    for rec_id, receipt in enumerate(receipts):
        for step_id, step in enumerate(receipt):
            if step_id != len(receipt)-1:
                for compatible_machine in find_compatible_machines(step):
                    for succ_comp_machine in find_compatible_machines(receipt[step_id+1]):
                        if (not isinstance(machines[compatible_machine], Oven)
                            and
                            not isinstance(machines[succ_comp_machine], Oven)):
                            model.Add(
                                all_steps[(rec_id, step_id+1, succ_comp_machine)].start
                                >
                                all_steps[(rec_id, step_id, compatible_machine)].end
                            )
                        elif (isinstance(machines[compatible_machine], Oven)
                              and
                              not isinstance(machines[succ_comp_machine], Oven)):
                            for is_frying in range(2):
                                model.Add(
                                    all_steps[(rec_id, step_id+1, succ_comp_machine)].start
                                    >
                                    all_steps[(rec_id, step_id, compatible_machine, is_frying)].end
                                )
                        elif (not isinstance(machines[compatible_machine], Oven)
                              and
                              isinstance(machines[succ_comp_machine], Oven)):
                            for is_frying in range(2):
                                model.Add(
                                    all_steps[(rec_id, step_id+1, succ_comp_machine, is_frying)].start
                                    >
                                    all_steps[(rec_id, step_id, compatible_machine)].end)
                        else:
                           for is_frying in range(2):
                               for is_frying_succ in range(2):
                                   model.Add(
                                    all_steps[(rec_id, step_id+1, succ_comp_machine, is_frying_succ)].start
                                    >
                                    all_steps[(rec_id, step_id, compatible_machine, is_frying)].end)


    # Constraints saying "if a step has a valid start time for a machine,
    # every other start time for the same step on another machine must be -1"
    # Only for the duration variables
    for rec_id, receipt in enumerate(receipts):
        for step_id, step in enumerate(receipt):
                same_step_dur_var = []
                for compatible_machine in find_compatible_machines(step):
                    if not isinstance(machines[compatible_machine], Oven):
                        same_step_dur_var.append(all_steps[rec_id, step_id, compatible_machine].duration)            
                    else:
                        for is_frying in range(2):
                            same_step_dur_var.append(all_steps[rec_id, step_id, compatible_machine, is_frying].duration)
                if not isinstance(step, PreHeat):
                    model.AddSumConstraint(same_step_dur_var,
                                            step.attributes["duration"], 
                                            step.attributes["duration"])
                else:
                    model.AddSumConstraint(same_step_dur_var,
                                            0, 
                                            step.attributes["duration"])


    # # Constraints saying "if a step is assigned to a machine, its start time
    # # and duration must be different from -1 and 0 respectively"
    for rec_id, receipt in enumerate(receipts):
        for step_id, step in enumerate(receipt):
                for compatible_machine in find_compatible_machines(step):
                    if not isinstance(machines[compatible_machine], Oven):
                        model.AddImplication(all_machines[(rec_id, step_id, compatible_machine)],
                                            all_steps_start_literals[(rec_id, step_id, compatible_machine)])
                        model.AddImplication(all_machines[(rec_id, step_id, compatible_machine)],
                                                all_steps_dur_literals[(rec_id, step_id, compatible_machine)])
                    else:
                        for is_frying in range(2):
                            model.AddImplication(all_machines[rec_id, step_id, compatible_machine, is_frying],
                                                all_steps_start_literals[rec_id, step_id, compatible_machine, is_frying])
                            if not isinstance(step, PreHeat):
                                model.AddImplication(all_machines[rec_id, step_id, compatible_machine, is_frying],
                                                    all_steps_dur_literals[rec_id, step_id, compatible_machine, is_frying])
            

    # # Constraints saying "if one step is assigned to a machine, it can't be assigned
    # # to another machine"
    # # for rec_id, receipt in enumerate(receipts):
    # #     for step, step_id in enumerate(receipt):
    # #         for compatible_machine in find_compatible_machines(step):
    # #             for other_comp_machine in find_compatible_machines(step):
    # #                 if compatible_machine != other_comp_machine:
    # #                     model.AddImplication(all_machines[rec_id, step_id, compatible_machine] == 1,
    # #                                          all_machines[rec_id, step_id, compatible_machine] == 0)


    # # Constraints saying "exactly one of the machine variables must be set to 1"
    for rec_id, receipt in enumerate(receipts):
        for step_id, step in enumerate(receipt):
            same_step_var = []
            for compatible_machine in find_compatible_machines(step):
                if not isinstance(machines[compatible_machine], Oven):
                    same_step_var.append(all_machines[rec_id, step_id, compatible_machine])
                else:
                    for is_frying in range(2):
                        same_step_var.append(all_machines[rec_id, step_id, compatible_machine, is_frying])
            model.AddSumConstraint(same_step_var, 1, 1)


    # Cumulative constraints for the machines' capacities
    for m_id, machine in enumerate(machines):
        interval_list = []
        for rec_id, receipt in enumerate(receipts):
            for step_id, step in enumerate(receipt):
                # if set(step[1]).issubset(machine[1]):
                if m_id in find_compatible_machines(step):
                    if not isinstance(machines[m_id], Oven):
                        interval_list.append(all_steps[(rec_id, step_id, m_id)].interval)
                    else:
                        for is_frying in range(2):
                            interval_list.append(all_steps[(rec_id, step_id, m_id, is_frying)].interval)
        # for rec_id, receipt in enumerate(receipts):
            # interval_list = [all_steps[(rec_id, step_id)].interval for step_id in range(len(receipt))]
        model.AddCumulative(interval_list, [1]*len(interval_list), machine.capacity)
            

    # If a step is not an OvenFry, the is_frying index of the matrix variables
    # should be 0
    for rec_id, receipt in enumerate(receipts):
        for step_id, step in enumerate(receipt):
            if isinstance(step, OvenStep) and (not isinstance(step, OvenFry)):
                for m_id in find_compatible_machines(step):
                    model.Add(all_machines[rec_id, step_id, m_id, 1] == 0)

    # Cooking and frying activities should not be performed
    # in the same oven
    for fry_comp_machine in all_fries.keys():
        for cook_comp_machine in all_cooks.keys():
            if fry_comp_machine == cook_comp_machine:
                for interval_fry_var in all_fries[fry_comp_machine]:
                    for interval_cook_var in all_cooks[cook_comp_machine]:
                        model.AddNoOverlap([interval_fry_var, interval_cook_var])


    # An Oven cannot be used while it's preheating
    overlap_start_preheats = {}
    preHeats_start_after_dict = {}
    preHeats_start_before_dict = {}
    before_and_after_dict = {}
    for rec_id, receipt in enumerate(receipts):
        for step_id, step in enumerate(receipt):
            if isinstance(step, PreHeat):
                for rec_id_1, receipt_1 in enumerate(receipts):
                    for step_id_1, step_1 in enumerate(receipt_1):
                        if step != step_1:
                            preHeat_cms = find_compatible_machines(step)
                            for compatible_machine in find_compatible_machines(step_1):
                                if compatible_machine in preHeat_cms:
                                    model.AddNoOverlap([all_steps[(rec_id, step_id, compatible_machine, 0)].interval,
                                                        all_steps[(rec_id_1, step_id_1, compatible_machine, 0)].interval])
                                    if ((isinstance(step_1, OvenCook) or isinstance(step_1, PreHeat))
                                        and
                                        step_1.attributes["temperature"] == step.attributes["temperature"]
                                        and
                                        step_1 != step.oven_cook):
                                        
                                        preHeats_start_after = model.NewBoolVar(
                                            "preHeat_after_%i_%i_%i_%i__m_%i" % (rec_id, step_id, rec_id_1, step_id_1, compatible_machine))
                                        preHeats_start_before = model.NewBoolVar(
                                                "preHeat_before_%i_%i_%i_%i__m_%i" % (rec_id, step_id, rec_id_1, step_id_1, compatible_machine))

                                        preHeats_start_after_dict[(rec_id, step_id, rec_id_1, step_id_1, compatible_machine)] = preHeats_start_after
                                        preHeats_start_before_dict[(rec_id, step_id, rec_id_1, step_id_1, compatible_machine)] = preHeats_start_before

                                        model.Add(all_steps[(rec_id, step_id, compatible_machine, 0)].start 
                                                  > 
                                                  all_steps[(rec_id_1, step_id_1, compatible_machine, 0)].start).OnlyEnforceIf(
                                                                preHeats_start_after
                                                            )

                                        model.Add(all_steps[(rec_id, step_id, compatible_machine, 0)].start 
                                                  <=
                                                  all_steps[(rec_id_1, step_id_1, compatible_machine, 0)].start).OnlyEnforceIf(
                                                                preHeats_start_after.Not()
                                                            )

                                        if (isinstance(step_1, OvenCook)):
                                            model.Add(all_steps[(rec_id, step_id, compatible_machine, 0)].start
                                                      <
                                                      all_steps[(rec_id_1, step_id_1, compatible_machine, 0)].end).OnlyEnforceIf(
                                                                      preHeats_start_before
                                                                    )
                                            model.Add(all_steps[(rec_id, step_id, compatible_machine, 0)].start
                                                      >=
                                                      all_steps[(rec_id_1, step_id_1, compatible_machine, 0)].end).OnlyEnforceIf(
                                                                      preHeats_start_before.Not()
                                                                    )
                                        else:
                                            cook_activity_index = receipt_1.index(step_1.oven_cook)
                                            model.Add(all_steps[(rec_id, step_id, compatible_machine, 0)].start
                                                      <
                                                      all_steps[(rec_id_1, cook_activity_index, compatible_machine, 0)].end).OnlyEnforceIf(
                                                                      preHeats_start_before
                                                                    )
                                            model.Add(all_steps[(rec_id, step_id, compatible_machine, 0)].start
                                                      >=
                                                      all_steps[(rec_id_1, cook_activity_index, compatible_machine, 0)].end).OnlyEnforceIf(
                                                                      preHeats_start_before.Not()
                                                                    )
                                        
                                        before_and_after_lit = model.NewBoolVar("b_and_a_lit_%i_%i_%i_%i__m_%i" % (rec_id, step_id, rec_id_1, step_id_1, compatible_machine))
                                        before_and_after_dict[(rec_id, step_id, rec_id_1, step_id_1, compatible_machine)] = before_and_after_lit


                                        model.Add(preHeats_start_after == 1).OnlyEnforceIf([before_and_after_lit, all_machines[(rec_id, step_id, compatible_machine, 0)]])
                                        model.Add(preHeats_start_after == 0).OnlyEnforceIf([before_and_after_lit.Not(), all_machines[(rec_id, step_id, compatible_machine, 0)]])

                                        # model.AddBoolAnd([preHeats_start_after,
                                        #                   preHeats_start_before]).OnlyEnforceIf([before_and_after_lit, all_machines[(rec_id, step_id, compatible_machine, 0)]])
                                        # model.AddBoolOr([preHeats_start_after.Not(),
                                        #                  preHeats_start_before.Not()]).OnlyEnforceIf([before_and_after_lit.Not(), all_machines[(rec_id, step_id, compatible_machine, 0)]])

                                        preHeat_dur_gt_0 = model.NewBoolVar("preHeat_dur_gt_0_%i_%i_%i_%i__m_%i" % (rec_id, step_id, rec_id_1, step_id_1, compatible_machine))
                                        model.AddImplication(before_and_after_lit.Not(), all_steps_dur_literals[rec_id, step_id, compatible_machine, 0])
    
    # When you preheat an oven, you must use that oven for the
    # following step and there must be not so much time betweend
    # the end of the preheat activity and the cook activity
    for rec_id, receipt in enumerate(receipts):
        for step_id, step in enumerate(receipt):
            if isinstance(step, PreHeat):
                cook_index = receipt.index(step.oven_cook)
                for compatible_machine in find_compatible_machines(step):
                    model.AddImplication(all_machines[(rec_id, step_id, compatible_machine, 0)],
                                         all_machines[(rec_id, cook_index, compatible_machine, 0)])
                    model.Add(all_steps[(rec_id, step_id, compatible_machine, 0)].end + 2
                              >=
                              all_steps[(rec_id, cook_index, compatible_machine, 0)].start)


    # A preheating activity must be performed only if there isn't
    # another preheating or cooking activity with the same temperature
    # at the same time. Otherwise, preheating is not performed and
    # the corresponding cooking activity is performed in the same oven
    # where the other step is being cooked


    # If you want to cook two dishes in the same oven
    # they must require the same temperature
    for rec_id, receipt in enumerate(receipts):
        for step_id, step in enumerate(receipt):
            for rec_id_1, receipt_1 in enumerate(receipts):
                for step_id_1, step_1 in enumerate(receipt_1):
                    if rec_id_1 > rec_id:
                        # t2 = step_1.attributes["temperature"]
                        if (isinstance(step, OvenCook) and 
                            isinstance(step_1, OvenCook) and
                            step.attributes["temperature"] != step_1.attributes["temperature"]):
                            for m_id in find_compatible_machines(step):
                                for m_id_1 in find_compatible_machines(step_1):
                                    if m_id == m_id_1:
                                        model.AddNoOverlap([all_steps[rec_id, step_id, m_id, 0].interval,
                                                            all_steps[rec_id_1, step_id_1, m_id_1, 0].interval])


    # Objective function
    # Our goal is to minimize the makespan, that is the total time of execution
    obj_var = model.NewIntVar(0, EOH, 'makespan')

    end_steps = []
    for rec_id in range(len(receipts)):
        for m_id in find_compatible_machines(receipts[rec_id][len(receipts[rec_id])-1]):
            if not isinstance(machines[m_id], Oven):
                end_steps.append(all_steps[(rec_id, len(receipts[rec_id]) - 1, m_id)].end)
            else:
                for is_frying in range(2):
                    end_steps.append(all_steps[(rec_id, len(receipts[rec_id]) - 1, m_id, is_frying)].end)

    # warnings.warn("Energy optimization only for ovens")
    # same_temp_steps_dict = {}
    # for rec_id, receipt in enumerate(receipts):
    #     for step_id, step in enumerate(receipt):
    #         if isinstance(step, OvenCook):
    #             if not (step.attributes["temperature"] in same_temp_steps_dict):
    #                 same_temp_steps_dict[step.attributes["temperature"]] = []
    #             same_temp_steps_dict[step.attributes["temperature"]].append((rec_id, step_id))

    # for same_temp_steps_list in same_temp_steps_dict.values():
    #     for same_temp_step in same_temp_steps_list:
    #         for m_id in find_compatible_machines(receipts[same_temp_step[0]]
    #                                                      [same_temp_step[1]]):
                


    model.AddMaxEquality(
        obj_var,
        end_steps
    )
    model.Minimize(obj_var)

    
    # Solve model
    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    print("Status of the solver: %i" % status)

    if (status == cp_model.UNKNOWN):
        print("Schedule doesn't worked well for unknown reason.")
        return
    elif (status == cp_model.MODEL_INVALID):
        print("MODEL INVALID!!")
        return
    elif (status == cp_model.INFEASIBLE):
        print("MODEL INFEASIBLE!!")
        return

        
    # Display results

    # Print makespan
    print("Optimal Schedule Length: %i" % solver.ObjectiveValue())
    print()

    print("AFTER")
    print(preHeats_start_after_dict.keys())
    for value in preHeats_start_after_dict.values():
        print(solver.Value(value))

    print()
    print("BEFORE")
    for value in preHeats_start_before_dict.values():
        print(solver.Value(value))

    print()
    for value in before_and_after_dict.values():
        print(solver.Value(value)) 

    for rec_id, receipt in enumerate(receipts):
        for step_id, step in enumerate(receipt):
            for compatible_machine in find_compatible_machines(step):
                if (not isinstance(machines[compatible_machine], Oven)):
                    print()
                    print(solver.Value(all_steps_start_literals[(rec_id, step_id, compatible_machine)]))
                    print("*"*15)
                    print(all_steps[(rec_id, step_id, compatible_machine)])
                    print(solver.Value(all_steps[(rec_id, step_id, compatible_machine)].start))
                    print(solver.Value(all_steps[(rec_id, step_id, compatible_machine)].end))
                    print("*"*15)
                    print(all_machines[(rec_id, step_id, compatible_machine)])
                    print(solver.Value(all_machines[(rec_id, step_id, compatible_machine)]))
                    print("*"*15)
                    print()
                else:
                    for is_frying in range(2):
                        print()
                        print("*"*15)
                        print(all_steps[(rec_id, step_id, compatible_machine, is_frying)])
                        print(solver.Value(all_steps[(rec_id, step_id, compatible_machine, is_frying)].start))
                        print(solver.Value(all_steps[(rec_id, step_id, compatible_machine, is_frying)].end))
                        print("*"*15)
                        print(all_machines[(rec_id, step_id, compatible_machine, is_frying)])
                        print(solver.Value(all_machines[(rec_id, step_id, compatible_machine, is_frying)]))
                        print("*"*15)
                        print()

    # Create one list of assigned steps per machine
    assigned_receipts = [[] for _ in range(len(machines))]
    for rec_id, receipt in enumerate(receipts):
        for step_id, step in enumerate(receipt):
            for compatible_machine in find_compatible_machines(step):
                for is_frying in range(2):
                    machine = 0
                    if not isinstance(machines[compatible_machine], Oven):
                        machine = solver.Value(all_machines[(rec_id, step_id, compatible_machine)])
                        if machine == 1:
                            assigned_receipts[compatible_machine].append(
                                assigned_step_type(
                                    start=solver.Value(all_steps[(rec_id, step_id, compatible_machine)].start),
                                    receipt=rec_id,
                                    index=step_id
                                )
                            )
                        # break needed to avoid adding twice not-Oven steps
                        break
                    else:
                        machine = solver.Value(all_machines[(rec_id, step_id, compatible_machine, is_frying)])
                        if machine == 1:
                            assigned_receipts[compatible_machine].append(
                                assigned_step_type(
                                    start=solver.Value(all_steps[(rec_id, step_id, compatible_machine, is_frying)].start),
                                    duration=solver.Value(all_steps[(rec_id, step_id, compatible_machine, is_frying)].duration),
                                    receipt=rec_id,
                                    index=step_id
                                )
                            )

    disp_col_width = 10
    sol_line = ''
    sol_line_steps = ''

    warnings.warn("Fare la cosa degli starttime dei preheat compresi tra il periodo di \
        un altro preheat e ovencook, ricordandosi di togliere il vincolo delle durate \
            diverse da 0 per i preheat")

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
            duration = assigned_step.duration

            sol_tmp = '[%i,%i]' % (start, start + duration)
            if isinstance(receipts[assigned_step.receipt][assigned_step.index], OvenFry):
                sol_tmp += "_F"
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
    if isinstance(step, OvenCook) or isinstance(step, PreHeat):
        return [m_id 
                for m_id, machine in enumerate(machines)
                if isinstance(machine, Oven) and
                   machine.max_temperature >= step.attributes['temperature']]
    elif isinstance(step, VacuumStep):
        return [m_id for m_id, machine in enumerate(machines) if isinstance(machine, VacuumMachine)]
    elif isinstance(step, BlastStep):
        return [m_id for m_id, machine in enumerate(machines) if isinstance(machine, BlastChiller)]
    elif isinstance(step, OvenFry):
        return [m_id for m_id, machine in enumerate(machines) if isinstance(machine, Oven) and
                                                                 machine.can_fry]
    elif isinstance(step, HumanStep):
        return [m_id for m_id, machine in enumerate(machines) if isinstance(machine, Human)]

    return []


if __name__ == '__main__':
    SIAF_scheduler()
