from time import time

import biorbd_casadi as biorbd
from bioptim import Solver, OdeSolver

from .gait.load_experimental_data import LoadData
from .gait.ocp import prepare_ocp, get_phase_time_shooting_numbers, get_experimental_data


def generate_table(out):
    root_path = "/".join(__file__.split("/")[:-1])

    # Define the problem -- model path
    biorbd_model = (
        biorbd.Model(root_path + "/models/Gait_1leg_12dof_heel.bioMod"),
        biorbd.Model(root_path + "/models/Gait_1leg_12dof_flatfoot.bioMod"),
        biorbd.Model(root_path + "/models/Gait_1leg_12dof_forefoot.bioMod"),
        biorbd.Model(root_path + "/models/Gait_1leg_12dof_0contact.bioMod"),
    )

    # --- files path ---
    c3d_file = root_path + "/data/normal01_out.c3d"
    q_kalman_filter_file = root_path + "/data/normal01_q_KalmanFilter.txt"
    qdot_kalman_filter_file = root_path + "/data/normal01_qdot_KalmanFilter.txt"
    data = LoadData(biorbd_model[0], c3d_file, q_kalman_filter_file, qdot_kalman_filter_file)

    # --- phase time and number of shooting ---
    phase_time, number_shooting_points = get_phase_time_shooting_numbers(data, 0.01)
    # --- get experimental data ---
    q_ref, qdot_ref, markers_ref, grf_ref, moments_ref, cop_ref = get_experimental_data(data, number_shooting_points, phase_time)

    for i, ode_solver in enumerate([OdeSolver.RK4(), OdeSolver.COLLOCATION()]):
        biorbd_model = (
            biorbd.Model(root_path + "/models/Gait_1leg_12dof_heel.bioMod"),
            biorbd.Model(root_path + "/models/Gait_1leg_12dof_flatfoot.bioMod"),
            biorbd.Model(root_path + "/models/Gait_1leg_12dof_forefoot.bioMod"),
            biorbd.Model(root_path + "/models/Gait_1leg_12dof_0contact.bioMod"),
        )
        ocp = prepare_ocp(
            biorbd_model=biorbd_model,
            final_time=phase_time,
            nb_shooting=number_shooting_points,
            markers_ref=markers_ref,
            grf_ref=grf_ref,
            q_ref=q_ref,
            qdot_ref=qdot_ref,
            nb_threads=8,
            ode_solver=ode_solver,
        )

        solver = Solver.IPOPT()
        solver.set_linear_solver("ma57")
        solver.set_convergence_tolerance(1e-3)
        solver.set_hessian_approximation("exact")
        solver.set_maximum_iterations(3000)
        solver.set_print_level(0)

        # --- Solve the program --- #
        tic = time()
        sol = ocp.solve(solver=solver)
        toc = time() - tic
        sol_merged = sol.merge_phases()

        out.solver.append(out.Solver("Ipopt"))
        out.solver[i].nx = sol_merged.states["all"].shape[0]
        out.solver[i].nu = sol_merged.controls["all"].shape[0]
        out.solver[i].ns = sol_merged.ns[0]
        out.solver[i].ode_solver = ode_solver
        out.solver[i].n_iteration = sol.iterations
        out.solver[i].cost = sol.cost
        out.solver[i].convergence_time = toc
        out.solver[i].compute_error_single_shooting(sol)
