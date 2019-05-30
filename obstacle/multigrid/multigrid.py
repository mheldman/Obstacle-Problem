# -*- coding: utf-8 -*-

import numpy as np
from scipy.sparse.linalg import spsolve
import scipy.sparse
import matplotlib.pyplot as plt

class multigrid_solver:
    '''
    Stores the multigrid hierarchy and implements recursive geometric multigrid solvers. The current implementation
    assumes the PDE is being solved on a rectangular region with a discretization in horizontal rows and vertical
    columns.

    Attributes:

        levels {iterable} : Contains level objects, which store the information for each level
        coarse_solver {callable} : Exact solver for the coarse grid.
        Inputs to coarse_solver should have the form (A, x, b, **kwargs)
        coarse_mx {int} : Number of unknowns in the horizontal direction
        coarse_my {int} : Number of unknowns in the vectrical direction
        level {level} : Stores the current level during the multigrid iteration. Initially set to the
        finest grid.
        smoother {callable} : Smoother to be used on each grid. Inputs should have the form (A, x, b, **kwargs),
        where A is a sparse square matrix, x is the current iterate, to be used as the intial guess for the smoother,
        and b is the right-hand side vector. The system is square with size (self.level.mx + 2)*(self.level.my + 2).

    Methods:

        lvl_solve: Recursively solves the discretized PDE.
        solve: Initializes the system and calls lvl_solve to solve the PDE


    '''

    def __repr__(self):
        output = 'Multigrid solver\n'
        output += 'Number of levels = ' + str(len(self.levels)) + '\n'
        output += 'Fine grid size (' + str((self.levels[0].mx + 2)) + ' x ' + str((self.levels[0].my + 2)) + ')\n'
        output += str(self.levels[0].mx * self.levels[0].my) + ' fine grid unknowns\n'
        output += 'Coarse grid size (' + str(self.coarse_mx + 2) + ' x ' + str(self.coarse_my + 2) + ')\n'
        output += str(self.coarse_mx * self.coarse_my) + ' coarse grid unknown(s)\n'
        return output

    def __init__(self, levels, coarse_mx, coarse_my, smoother, coarse_solver=spsolve, diagnostics=()):

        self.levels = levels
        self.coarse_solver = coarse_solver
        self.coarse_mx = coarse_mx
        self.coarse_my = coarse_my
        self.level = self.levels[0]
        self.smoother = smoother
        self.residuals = []
        self.diagnostics = diagnostics

    def lvl_solve(self, lvl, u, b, cycle, smoothing_iters=1):

        self.level = self.levels[lvl]
        A = self.level.A
        R = self.level.R
        if 'show levels' in self.diagnostics:
            print(lvl * "    " + "Grid " + str(lvl) + ", mx = " + str(self.level.mx) + ", my = " + str(self.level.my))

        for i in range(smoothing_iters):
            self.smoother(A, u, b, maxiters=1)

        r = b - A.dot(u)
        coarse_b = R.dot(r)
        if lvl < len(self.levels) - 2:
            coarse_u = np.zeros_like(coarse_b)
            if cycle == 'W':
                self.lvl_solve(lvl + 1, coarse_u, coarse_b, cycle)
                self.lvl_solve(lvl + 1, coarse_u, coarse_b, cycle)

            elif cycle == 'V':
                self.lvl_solve(lvl + 1, coarse_u, coarse_b, cycle)

            elif cycle == 'FV':
                self.lvl_solve(lvl + 1, coarse_u, coarse_b, cycle)
                self.lvl_solve(lvl + 1, coarse_u, coarse_b, 'V')

            elif cycle == 'FW':
                self.lvl_solve(lvl + 1, coarse_u, coarse_b, cycle)
                self.lvl_solve(lvl + 1, coarse_u, coarse_b, 'W')

        else:
            if 'show levels' in self.diagnostics:
                print((lvl + 1) * "    " + "Grid " + str(lvl + 1) + ", mx = " + str(self.coarse_mx) + ", my = " + str(
                    self.coarse_my))
            coarse_u = self.coarse_solver(self.levels[-1].A, coarse_b)

        P = self.levels[lvl + 1].P
        u += P.dot(coarse_u)
        for i in range(smoothing_iters):
            self.smoother(A, u, b)
        self.level = self.levels[lvl]
        if 'show levels' in self.diagnostics:
            print(lvl * "    " + "Grid " + str(lvl) + ", mx = " + str(self.level.mx) + ", my = " + str(
                self.level.my))

    '''
    def aspreconditioner(self, cycle='V')
        
      from scipy.sparse.linalg import LinearOperator
      shape = self.levels[0].A.shape
      dtype = self.levels[0].A.dtype

      def matvec(b):
          return self.solve(b, maxiter=1, cycle=cycle, tol=1e-12)

      return LinearOperator(shape, matvec, dtype=dtype, maxiters=1)
    '''
    
    def solve(self, b, u0=None, cycle='FV', tol=1e-12, maxiters=50, smoothing_iters=1):
      
      if cycle != 'fmg':
        
        if u0 is None:
            u0 = np.zeros_like(b)

        u = np.array(u0)
        self.residuals.append(np.linalg.norm(b - self.level.A.dot(u), np.inf))
        z = 0
        normb = np.linalg.norm(b)
        while self.residuals[-1] / normb > tol and z < maxiters:
            print('gmg residual iteration ' + str(z) + ': ' + str(self.residuals[-1]))
            self.lvl_solve(0, u, b, cycle, smoothing_iters=smoothing_iters)
            self.residuals.append(np.linalg.norm(b - self.level.A.dot(u), np.inf))
            z += 1
        residuals = self.residuals
        print('gmg final residual iteration ' + str(z) + ': ' + str(residuals[-1]))
        print('convergence factor gmg: ' + str((residuals[-1] / residuals[0]) ** (1.0 / len(residuals))) + '\n')
        return u
    
      else:

        blist = [b]
        for k in range(0, len(self.levels)-1):
          blist.append(self.levels[k].R.dot(blist[-1]))
        
        u0 = self.coarse_solver(self.levels[-1].A, blist[-1])
        u = np.array(u0)
        L = len(self.levels)
        
        for n in range(1, L):
          gmg_solver = multigrid_solver(self.levels[L-1-n: L], self.coarse_mx, self.coarse_my, self.smoother, coarse_solver=self.coarse_solver, diagnostics=self.diagnostics)
          u = self.levels[-n].P.dot(u)
          u = gmg_solver.solve(blist[L-1-n], u0=u, cycle='V', smoothing_iters=smoothing_iters, maxiters=1)
        self.residuals.append(np.linalg.norm(b - self.levels[0].A.dot(u), np.inf))
        residuals = self.residuals
        print('fmg final residual: ' + str(residuals[-1]))
        return u

      



class level:
    '''
    Stores one level of the multigrid hierarchy and implements recursive geometric multigrid solvers. The current
    implementation assumes the PDE is being solved on a rectangular region with a discretization in horizontal rows
    and vertical columns. This class functions as a struct.

    Attributes:

      mx {int}: Number of unknowns in the horizontal direction on the current level
      my {int}: Number of unknowns in the vectical direction on the current level
      x1, x2, y1, y2 {int}: Determines the region where the problem is being solved. x1 and x2 are the bounds
      in the horizontal direction, y1 and y2 are the bounds in the vertical direction.
      hx {float}: Grid spacing the horizontal direction on the current level. Given by (x2 - x1) / (mx + 1)
      hy {float}: Grid spacing in the vertical direction on the current level. Given by (y2 - y1) / (my + 1)
      A {spmatrix}: A square spmatrix of size (mx + 2)*(my + 2). The differential operator on the current
      level.
      R {spmatrix}: Restriction matrix. Transfers the problem to the next coarser grid.
      P {spmatrix}: Prolongation matrix. Transfers the problem to the next finer grid.

    '''

    def __init__(self, mx, my, A, R, P, x1, x2, y1, y2, bndry_pts):

        if callable(A):
            self.A = A(mx, my, x1, x2, y1, y2)
        else:
            self.A = A

        if callable(R):
            self.R = R(mx, my)
        else:
            self.R = R

        if callable(P):
            self.P = P(mx, my)
        else:
            self.P = P
        self.bounds = (x1, x2, y1, y2)
        self.mx = mx
        self.my = my
        self.hx = (x2 - x1) / (mx + 1)
        self.hy = (y2 - y1) / (my + 1)
        self.bndry_pts = bndry_pts


def compute_Fomega(x, F):  # merit function (residual) for LCP
    Fomega = np.minimum(F, 0.0)
    bool_array = (x > 1e-16)
    Fomega[bool_array] = F[bool_array]
    return Fomega


class linear_pfas_solver:
    '''
    Stores the multigrid hierarchy and implements the projected full-approximation scheme (developed in [1]) for the
    solution of linear complementarity problems arising from free boundary problems. The free-boundary problem should
    occur on a rectangular region with a discretization in horizontal rows and vertical columns.

    Attributes:

        levels {iterable} : Contains level objects, which store the information for each level
        coarse_solver {callable} : Exact solver for the coarse grid.
        Inputs to coarse_solver should have the form (A, x, b, **kwargs)
        coarse_mx {int} : Number of unknowns in the horizontal direction
        coarse_my {int} : Number of unknowns in the vectrical direction
        level {level} : Stores the current level during the multigrid iteration. Initially set to the
        finest grid.
        smoother {callable} : Smoother to be used on each grid. Inputs should have the form (A, x, b, **kwargs),
        where A is a sparse square matrix, x is the current iterate, to be used as the initial guess for the smoother,
        and b is the right-hand side vector. The system is square with size (self.level.mx + 2)*(self.level.my + 2).

    Methods:

        lvl_solve: Recursively solves the discretized free boundary problem
        solve: Initializes the system and calls lvl_solve to solve the free boundary problem

    Sources:

    [1] Achi Brandt and Colin W. Cryer. Multigrid algorithms for the solution of linear complementarity problems
        arising from free boundary problems. Siam Journal on Scientific and Statistical Computing, 4(4):655–684, 1983.

    '''

    def __repr__(self):
        output = 'PFAS solver\n'
        output += 'Number of levels = ' + str(len(self.levels)) + '\n'
        output += 'Fine grid size (' + str((self.levels[0].mx + 2)) + ' x ' + str((self.levels[0].my + 2)) + ')\n'
        output += str(self.levels[0].mx * self.levels[0].my) + ' fine grid unknowns\n'
        output += 'Coarse grid size (' + str((self.coarse_mx + 2)) + ' x ' + str((self.coarse_my + 2)) + ')\n'
        output += str(self.coarse_mx * self.coarse_my) + ' coarse grid unknown(s)\n'
        return output

    def __init__(self, levels, coarse_mx, coarse_my, smoother, coarse_solver=None, diagnostics=None):

        self.levels = levels
        if coarse_solver is None:
          self.coarse_solver = smoother
        else:
          self.coarse_solver = coarse_solver
        self.coarse_mx = coarse_mx
        self.coarse_my = coarse_my
        self.level = self.levels[0]
        self.smoother = smoother
        self.mu = .15
        self.diagnostics = diagnostics
        self.residuals = []
        self.bndry_pts = []

    def lvl_solve(self, lvl, u, b, cycle, smoothing_iters=1):

        self.level = self.levels[lvl]
        if 'show levels' in self.diagnostics:
            print(lvl * "    " + "Grid " + str(lvl) + ", mx = " + str(self.level.mx) + ", my = " + str(self.level.my))
        A = self.level.A
        for i in range(smoothing_iters):
            self.smoother(A, u, b)


        R = self.level.R
        coarse_u = R.dot(u)
        coarse_b = R.dot(b - A.dot(u))
        coarse_A = self.levels[lvl + 1].A  # needs at least two levels
        coarse_b = coarse_b + coarse_A.dot(coarse_u)
        if lvl < len(self.levels) - 2:

            if cycle == 'W':
                self.lvl_solve(lvl + 1, coarse_u, coarse_b, cycle)
                self.lvl_solve(lvl + 1, coarse_u, coarse_b, cycle)

            elif cycle == 'V':
                self.lvl_solve(lvl + 1, coarse_u, coarse_b, cycle)

            elif cycle == 'FV':
                self.lvl_solve(lvl + 1, coarse_u, coarse_b, 'FV')
                self.lvl_solve(lvl + 1, coarse_u, coarse_b, 'V')

            elif cycle == 'FW':
                self.lvl_solve(lvl + 1, coarse_u, coarse_b, 'FW')
                self.lvl_solve(lvl + 1, coarse_u, coarse_b, 'W')

            elif cycle == 'fmgV':
                coarse_b2 = R.dot(b)
                self.lvl_solve(lvl + 1, coarse_u, coarse_b2, 'fmgV')
                self.lvl_solve(lvl + 1, coarse_u, coarse_b, 'V')

        else:
            if 'show levels' in self.diagnostics:
                print((lvl + 1) * "    " + "Grid " + str(lvl + 1) + ", mx = " + str(self.coarse_mx) + ", my = " + str(
                    self.coarse_my))
            du = 1.0
            while du > 10 ** -12:
                uold = coarse_u.copy()
                self.smoother(coarse_A, coarse_u, coarse_b)
                du = (self.coarse_mx + 1) * np.linalg.norm(uold - coarse_u)

        P = self.levels[lvl + 1].P
        u += P.dot(coarse_u - R.dot(u))
        self.level = self.levels[lvl]

        if 'show levels' in self.diagnostics:
            print(lvl * "    " + "Grid " + str(lvl) + ", mx = " + str(self.level.mx) + ", my = " + str(self.level.my))

        for i in range(smoothing_iters):
            self.smoother(A, u, b)


    def plot_active_set(self, u):

      x1, x2, y1, y2 = self.level.bounds
      mx, my = self.level.mx, self.level.my
      Z = u.reshape((mx + 2, my + 2))
      X = np.linspace(x1, x2, mx + 2)
      Y = np.linspace(y1, y2, my + 2)
      A, B = np.meshgrid(X, Y)
      A, B = np.transpose(A), np.transpose(B)
      plt.ion()
      plt.plot(A[[Z < 1e-10]], B[[Z < 1e-10]], 'o', color='k')
      plt.xlim(x1, x2)
      plt.ylim(y1, y2)
      plt.show()
      plt.pause(2)
      plt.close('all')
    
    def plot_residual(self, r):
    
      x1, x2, y1, y2 = self.level.bounds
      r = abs(r)
      mx, my = self.level.mx, self.level.my
      Z = r.reshape((mx + 2, my + 2))
      X = np.linspace(x1, x2, mx + 2)
      Y = np.linspace(y1, y2, my + 2)
      A, B = np.meshgrid(X, Y)
      A, B = np.transpose(A), np.transpose(B)
      ax = plt.scatter(A, B, s=20, c=Z, marker = '.', cmap = 'copper')
      plt.colorbar(ax)
      plt.ion()
      plt.show()
      plt.pause(2)
      plt.close('all')
    
    

    def active_set(self, u, r):
        return np.arange(len(r))[(u < 1e-16) & (r > 0.0)]

    def solve(self, b, u0=None, cycle='FV', tol=1e-8, maxiters=400, smoothing_iters=1, accel=None):
      
      if cycle != 'fmg':
        print('pfas solver maxiters: ' + str(maxiters))
        print('pfas solver residual tolerance: ' + str(tol) + '\n')
        
        if u0 is None or u0 == 'zero':
            u0 = np.zeros_like(b)
            if len(self.levels[0].bndry_pts) == 0:
                'Warning: zero initial guess with no specified boundary points. Initial guess may not be feasible'
            else:
                u0[self.levels[0].bndry_pts] = b[self.levels[0].bndry_pts]

        elif isinstance(u0, type(np.zeros((1,)))):
            pass

        elif isinstance(u0, str):
        
            if u0 == 'spsolve':
                print('computing pfas initial guess using ' + u0 + '\n')
                u0 = spsolve(self.level.A, b)
            
            elif u0 == 'gmg':
                print('computing pfas initial guess using ' + u0 + '\n')
                linear_solver = multigrid_solver(self.levels, self.coarse_mx, self.coarse_my, gs, coarse_solver=spsolve)
                print(linear_solver)
                u0 = linear_solver.solve(b, tol=tol * np.sqrt(len(b)))
                
            elif u0 == 'gs':
                print('computing pfas initial guess using ' + u0 + '\n')
                r0 = np.linalg.norm(b, np.inf)
                u = np.zeros_like(b)
                r = r0
                while r/r0 > tol:
                    gs(self.level.A, u, b)
                    r = np.linalg.norm(self.level.A.dot(u) - b)
                
            else:
                print('str option for initial guess not recognized. using u0 = zeros_like(b) or u0 = b' + '\n')
                if len(self.levels[0].bndry_pts) > 0:
                    u0 = np.zeros_like(b)
                    u0[self.levels[0].bndry_pts] = b[self.levels[0].bndry_pts]
                else:
                    u0 = b

        u = np.array(u0)
        u[u < 0.0] = 0.0
        residuals = []
        r = b - self.level.A.dot(u)
        fomega = compute_Fomega(u, r)
        residuals.append(np.linalg.norm(fomega, np.inf))
        z = 0

        if 'show residuals' in self.diagnostics:
            print('pfas residual iteration ' + str(z) + ': ' + str(residuals[-1]))
        
        if 'residual heat map' in self.diagnostics:
          self.plot_residual(fomega)

        if 'show reduced space' in self.diagnostics:
          self.plot_active_set(u)

        active_set_old = set(self.active_set(u, r))
        active_set_new = active_set_old
        normb = np.linalg.norm(b)

        while residuals[-1] / normb > tol and z < maxiters:
        
            self.lvl_solve(0, u, b, cycle, smoothing_iters=smoothing_iters)
            z += 1
            r = b - self.level.A.dot(u)
            fomega = compute_Fomega(u, r)
            residuals.append(np.linalg.norm(fomega, np.inf))

            if 'show residuals' in self.diagnostics:
                print('pfas residual iteration ' + str(z) + ': ' + str(residuals[-1]))

            if 'show reduced space' in self.diagnostics:
                self.plot_active_set(u)
                
            if 'residual heat map' in self.diagnostics:
              self.plot_residual(fomega)
            
            active_set_old = active_set_new
            active_set_new = set(self.active_set(u, r))
            conv_factor = (residuals[-1] / residuals[0]) ** (1.0 / (len(residuals) - 1.0))
            
            if accel == 'rsp':
              if len(active_set_new) != 0:
                active_set_change = len(set(active_set_new).symmetric_difference(set(active_set_old)))/len(active_set_new)
              else:
                active_set_change = 0.

              if z != 0 and (active_set_change < .01 or conv_factor > .3):
              
                if conv_factor > .3:
                  print('stalled convergence.. total convergence factor > .3')
                  print('switching to reduced space method')
                else:
                  print('\n' + 'active set converged to within tolerance. solving BVP...')
                print('geometric convergence factor PFAS: ' + str(conv_factor) + '\n')
                break

            else:
              if z != 0 and (active_set_new == active_set_old):  # z!=0 and residuals[-1]/residuals[-2] > .5:
                if conv_factor > .75:
                    print('solver diverged.. convergence factors > .75')
                else:
                    print('\n' + 'active set converged. solving BVP...')
                print('geometric convergence factor PFAS: ' + str(conv_factor) + '\n')
                break

        gmg_called = False
        from obstacle.multigrid.GS import gs
        while residuals[-1] / residuals[0] > tol and z < maxiters:
            if gmg_called:
                active_set_new = self.active_set(u, b1)
            if not gmg_called:
                b1 = b.copy()
                Alist = []
                for i in range(len(self.levels)):
                    Alist.append(self.levels[i].A.copy())
            gmg_called = True
            active_set_vec = np.zeros((self.level.mx + 2) * (self.level.my + 2))
            active_set_new = list(active_set_new)
            b[active_set_new] = 0.
            active_set_vec[active_set_new] = 1

            for i in range(len(self.levels)):
                self.levels[i].A = Alist[i]
                I_elim = -scipy.sparse.diags(active_set_vec - 1, 0, shape=self.levels[i].A.shape, format='csr')
                I_add = scipy.sparse.diags(active_set_vec, 0, shape=self.levels[i].A.shape, format='csr')
                self.levels[i].A = I_elim.dot(self.levels[i].A.dot(I_elim)) + I_add
                active_set_vec = self.levels[i].R.dot(active_set_vec)
            gmg_solver = multigrid_solver(self.levels, self.coarse_mx, self.coarse_my, gs, coarse_solver=spsolve)
            print(gmg_solver)
            normb = np.linalg.norm(b)
            u = gmg_solver.solve(b, u0=u, tol=tol / normb * residuals[0], cycle=cycle, smoothing_iters=smoothing_iters)
            u[u < 0.] = 0.
            b = b1.copy()
            residuals.append(np.linalg.norm(compute_Fomega(u, b - Alist[0].dot(u)), np.inf))
            for i in range(len(self.levels)):
                self.levels[i].A = Alist[i]
            print('pfas residual iteration ' + str(z) + ': ' + str(residuals[-1]))
            z += 1
            if len(gmg_solver.residuals) == 1:
              break
        num_pfas = len(residuals) - 1
        if gmg_called:
            for i in range(len(gmg_solver.residuals)):
                residuals = residuals[0:num_pfas] + gmg_solver.residuals
        else:
            num_pfas = len(residuals)
        

        if residuals[-1] / normb < tol:
        
            print('\n' + 'convergence summary')
            print('-------------------')
            # residuals = residuals + residuals_rsp[2:len(residuals_rsp)]
            for i in range(len(residuals)):
                if i == 0:
                    print('pfas residual ' + str(i) + ': ' + str(residuals[i]) + ' ' * (
                    22 + len(str(maxiters)) - len(str(residuals[i])) - len(
                        str(i))) + 'convergence factor 0: ---------------')
                elif i < num_pfas:
                    print('pfas residual ' + str(i) + ': ' + str(residuals[i]) + ' ' * (
                    22 + len(str(maxiters)) - len(str(residuals[i])) - len(str(i))) \
                          + 'convergence factor ' + str(i) + ': ' + str(residuals[i] / residuals[i - 1]))
                elif i > num_pfas:
                    print('gmg residual  ' + str(i - 1) + ': ' + str(residuals[i]) + ' ' * (
                    22 + len(str(maxiters)) - len(str(residuals[i])) - (len(str(i - 1)))) \
                          + 'convergence factor ' + str(i - 1) + ': ' + str(residuals[i] / residuals[i - 1]))

        self.residuals = residuals

        if 'show reduced space' in self.diagnostics:
        
            mx, my = self.level.mx, self.level.my
            x1, x2, y1, y2 = self.level.bounds
            kk = lambda i, j: (self.level.mx + 2) * i + j
            Z, Z1 = np.zeros((mx + 2, my + 2)), np.zeros((mx + 2, my + 2))
            for i in range(0, my + 2):
                for j in range(0, mx + 2):
                    k = kk(i, j)
                    Z[j, i] = u[k]
                    Z1[j, i] = 0.0
            X = np.linspace(x1, x2, mx + 2)
            Y = np.linspace(y1, y2, my + 2)
            A, B = np.meshgrid(Y, X)
            fig = plt.figure()
            ax = fig.gca(projection='3d')
            surf1 = ax.plot_surface(A, B, Z, cmap='Greens', vmin=0.0, vmax=5.1, alpha=.4)
            surf2 = ax.plot_surface(A, B, Z1, color='b', vmin=0.0, vmax=5.1, alpha=1.0)
            plt.ioff()
            plt.show()

        print('aggregate convergence factor: ' + str((residuals[-1] / residuals[0]) ** (1.0 / (len(residuals) - 1.0))))
        print('residual reduction: ' + str(residuals[-1] / residuals[0]) + '\n')
        return u

      else:

        blist = [b]
        for k in range(0, len(self.levels)-1):
          blist.append(self.levels[k].R.dot(blist[-1]))
        u = np.zeros_like(blist[-1])
        bndry = self.levels[-1].bndry_pts
        u[bndry] = blist[-1][bndry]
        du = 1.0
        while du > 1e-12:
          uold = u.copy()
          self.smoother(self.levels[-1].A, u, blist[-1])
          du = (self.coarse_mx + 1) * np.linalg.norm(uold - u)
        L = len(self.levels)
        u = self.levels[-1].P.dot(u)
        for n in range(2, L):
          pfas_solver = linear_pfas_solver(self.levels[L-1-n:L], self.coarse_mx, self.coarse_my, self.smoother, coarse_solver=self.coarse_solver, diagnostics=self.diagnostics)
          u = self.levels[-n].P.dot(u)
          bndry = self.levels[-1-n].bndry_pts
          b = blist[-1-n]
          u[bndry] = b[bndry]
          u = pfas_solver.solve(b, u0=u, cycle='V', smoothing_iters=smoothing_iters, tol=1e-8)
          
        return u




