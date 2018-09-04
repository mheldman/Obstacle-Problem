from multigrid import fmg
from Poisson2D import Poisson2D
import numpy as np

f = lambda x,y: -8.0*(np.pi**2)*np.sin(2.0*np.pi*x)*np.sin(2.0*np.pi*y)
minm = 2
numcycles = 4
m = minm
for i in range(0, numcycles):
    m = 2 * m + 1
print(m)
A, U, F, P, X = Poisson2D(m, f, bvals = True)

U = fmg(m, F, f, numcycles = 4)

m = 2*m + 1
X = np.linspace(-1.0, 1.0, m + 2)
Uexact = np.zeros(((m + 2)**2, 1))
uexact = lambda x,y: np.sin(2.0*np.pi*x)*np.sin(2.0*np.pi*y)
kk = lambda i,j: j * (m + 2) + i
for j in range(0, m + 2):
    for i in range(0, m + 2):
        k = kk(i,j)
        Uexact[k] = uexact(X[i],X[j])
print(np.linalg.norm(Uexact - U, np.inf))
for j in range(15, 20):
    for i in range(15, 20):
        k = kk(i, j)
        print(U[k], Uexact[k], X[i], X[j])