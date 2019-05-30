import numpy as np

Alpha = .68026
Beta = .47152

def psi(x, y):
    x = np.array([x])
    y = np.array([y])
    z = np.sqrt(np.maximum(1 - x ** 2 - y ** 2, 0.0))
    z[[z < 1 / np.sqrt(2)]] = -(x[[z < 1 / np.sqrt(2)]] ** 2 + y[[z < 1 / np.sqrt(2)]] ** 2) / np.sqrt(2) \
                              + np.sqrt(2) - 1 / (2 * np.sqrt(2))
    return z[0]

f = lambda x, y: 0.0
g = lambda x, y: -Alpha * np.log(np.sqrt(x ** 2 + y ** 2)) + Beta
x1, x2, y1, y2 = -2.0, 2.0, -2.0, 2.0
bounds = (x1,x2,y1,y2)

def uexact(x, y):
    r = np.sqrt(x ** 2 + y ** 2)
    cond1 = (r > .69797)
    cond2 = ~cond1
    Uexact = 0.*x
    Uexact[cond1] = g(x[cond1], y[cond1])
    Uexact[cond2] = psi(x[cond2], y[cond2])
    return Uexact

