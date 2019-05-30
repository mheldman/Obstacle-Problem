from obstacle.multigrid import linear_pfas_solver, level, multigrid_solver, restrict_inj, interpolate
from obstacle.reduced_space import rspmethod_lcp_solver, multilevel_rsp_solver
import numpy as np
from obstacle.obstacle_problem import box_obstacle_problem, poisson2d
from obstacle.multigrid.GS import gs, pgs
from time import time
import matplotlib.pyplot as plt
from scipy.sparse.linalg import spsolve
import sys, getopt

def main(argv):

  outputfile = ''
  show_residuals = ''
  show_active_set = ''
  coarse_mx = 1
  coarse_my = 1
  num_levels = 8
  mx = 255
  my = 255
  maxiters = 100
  linear_solver = 'cg'
  preconditioner = 'amg'
  cycle = 'W'
  tol = 1e-10
  plot_solution = ''
  show_reduced_space = ''
  solver_type = 'pfas'
  pfas_accel = False
  smoothing_iters = 2
  
  try:
   opts, args = getopt.getopt(argv,"hi:o:",["ofile=", "show_residuals=", "show_active_set=", "num_grids=", "coarse_mx=", "coarse_my=", "maxiters=", "ksp_type=", "pc_type=", "tol=", "plot_solution=", "solver_type=", "cycle_type=", "pfas_accel="])
  except getopt.GetoptError:
    print('radial_example.py --show_active_set --show_residuals --verbose --num_grids <int> --coarse_mx <int> --coarse_my --mx <int> --my <int> <int> -o <outputfile> --maxiters <int> --ksp_type <cg> --pc_type <ilu, lu, amg, gmg> --cycle_type <V, F, W, fmg> --tol <float> --plot_solution --solver_type <rsp, pfas, pfas_rsp>')
    sys.exit(2)
  for opt, arg in opts:
    if opt == '-h':
       print('radial_example.py --show_active_set --show_residuals --verbose --num_grids <int> --coarse_mx <int> --coarse_my --mx <int> --my <int> <int> -o <outputfile> --maxiters <int> --ksp_type <cg> --pc_type <ilu, lu, amg, gmg> --cycle_type <V, F, W, fmg> --tol <float> --plot_solution --solver_type <rsp, pfas, pfas_rsp>')
       sys.exit()
    elif opt in ("-o", "--ofile"):
       outputfile = arg
    elif opt == "--show_residuals":
      show_residuals = "show residuals"
    elif opt == "--show_active_set":
      show_active_set = "show active set"
    elif opt == "--num_grids":
      num_levels = int(arg)
    elif opt == "--coarse_mx":
      coarse_mx = int(arg)
    elif opt == "--coarse_my":
      coarse_my = int(arg)
    elif opt == "--mx":
      mx = int(arg)
    elif opt == "--my":
      my = int(arg)
    elif opt == "--maxiters":
      maxiters = int(arg)
    elif opt == "--ksp_type":
      linear_solver = arg
    elif opt == "--pc_type":
      preconditioner = arg
    elif opt == "--cycle_type":
      cycle = arg
    elif opt == "--tol":
      tol = float(arg)
    elif opt == "--plot_solution":
      plot_solution = "plot solution"
    elif opt == "--solver_type":
      solver_type = arg
    elif opt == "--pfas_accel":
      pfas_accel = True
    else:
      print('option ' + opt + ' not recongnized')

  if solver_type == 'pfas' or solver_type == 'mlrsp': #add grid sequenced version
  
    if solver_type == 'mlrsp':
      from obstacle.reduced_space import level
    else:
      from obstacle.multigrid import level

    levels = [] #build multilevel hierarchy
    mx, my = coarse_mx, coarse_my
    tstart = time()
    obstacle_problem = box_obstacle_problem(bounds, f, g, psi)
    obstacle_problem.discretize(mx, my)
    if solver_type == 'mlrsp':
      lvl = level(mx, my, poisson2d, obstacle_problem.F, interpolate, x1, x2, y1, y2, bndry_pts=obstacle_problem.bndry_pts)
    else:
      lvl = level(mx, my, poisson2d, restrict_inj, interpolate, x1, x2, y1, y2, bndry_pts=obstacle_problem.bndry_pts)
    levels.append(lvl)
    
    for j in range(1, num_levels):
        mx = 2 * mx + 1
        my = 2 * my + 1
        obstacle_problem = box_obstacle_problem(bounds, f, g, psi)
        obstacle_problem.discretize(mx, my)
        if solver_type == 'mlrsp':
          lvl = level(mx, my, poisson2d, obstacle_problem.F, interpolate, x1, x2, y1, y2, bndry_pts=obstacle_problem.bndry_pts)
        else:
          lvl = level(mx, my, poisson2d, restrict_inj, interpolate, x1, x2, y1, y2, bndry_pts=obstacle_problem.bndry_pts)

        levels.append(lvl)
    

    if solver_type == 'pfas':
    
      levels.reverse()
      pfas_solver = linear_pfas_solver(levels, coarse_mx, coarse_my, pgs, diagnostics= (show_residuals, 'geometric convergence factor', show_reduced_space))
      
      print('system setup time: ' + str(time() - tstart) + '\n')
      print(pfas_solver)
      tstart = time()
      
      U = obstacle_problem.solve(pfas_solver.solve, obstacle_problem.F, cycle=cycle, maxiters=100, smoothing_iters=smoothing_iters, accel=None, tol=tol)
      
      timex = time() - tstart

    elif solver_type == 'mlrsp':

      ml_solver = multilevel_rsp_solver(levels, coarse_mx, coarse_my, linear_solver=linear_solver, preconditioner=preconditioner, diagnostics=(show_residuals, 'geometric convergence factor', show_reduced_space))
      tstart = time()
      U = obstacle_problem.solve(ml_solver.solve, obstacle_problem.F, tol, maxiters)
      timex = time() - tstart
  elif solver_type == 'rsp':

    if pfas_accel == True:
      from obstacle.multigrid import level
      
      levels = [] #build multilevel hierarchy
      mx, my = coarse_mx, coarse_my
      tstart = time()
      obstacle_problem = box_obstacle_problem(bounds, f, g, psi)
      obstacle_problem.discretize(mx, my)
      lvl = level(mx, my, poisson2d, restrict_inj, interpolate, x1, x2, y1, y2, bndry_pts=obstacle_problem.bndry_pts)
      levels.append(lvl)
      
      for j in range(1, num_levels):
          mx = 2 * mx + 1
          my = 2 * my + 1
          obstacle_problem = box_obstacle_problem(bounds, f, g, psi)
          obstacle_problem.discretize(mx, my)
          lvl = level(mx, my, poisson2d, restrict_inj, interpolate, x1, x2, y1, y2, bndry_pts=obstacle_problem.bndry_pts)  # currently uses only injection operator
          levels.append(lvl)

      levels.reverse()

      pfas_solver = linear_pfas_solver(levels, coarse_mx, coarse_my, pgs, diagnostics=(show_residuals, 'geometric convergence factor', show_reduced_space))
      
      
      print(pfas_solver)
      tstart = time()
      U = obstacle_problem.solve(pfas_solver.solve, obstacle_problem.F, cycle=cycle, maxiters=3, smoothing_iters=smoothing_iters, accel=None, tol=tol)
      U -= obstacle_problem.P
      rsp_solver = rspmethod_lcp_solver(obstacle_problem.A, obstacle_problem.F, 1e-8, 100, diagnostics=('show reduced space'), bvals=obstacle_problem.bndry_pts)
      
      print(rsp_solver)
      
      U = obstacle_problem.solve(rsp_solver.solve, linear_solver = linear_solver, init_iterate=U, preconditioner=preconditioner, bounds=(x1,x2,y1,y2), mx = mx, my=my)

      timex = time() - tstart

    else:

      obstacle_problem = box_obstacle_problem(bounds, f, g, psi)
      obstacle_problem.discretize(mx, my)
      rsp_solver = rspmethod_lcp_solver(obstacle_problem.A, obstacle_problem.F, 1e-8, 100, diagnostics=('show reduced space'), bvals=obstacle_problem.bndry_pts)
      print(rsp_solver)
      U = obstacle_problem.solve(rsp_solver.solve, linear_solver = linear_solver, preconditioner=preconditioner, bounds=(x1,x2,y1,y2), mx = mx, my=my)

      timex = time() - tstart



  print('time for ' + solver_type + ': ' + str(timex) + '\n')


if __name__ == "__main__":
   main(sys.argv[1:])
