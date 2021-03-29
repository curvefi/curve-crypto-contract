import numpy as np
import pylab

from simulation_int_many import newton_y


A = 135
D = 3


def get_y(x, gamma):
    X = [10**18] * 3
    X[0] = int(x * 1e18)
    return newton_y(A, int(1e18 * gamma), X, int(D * 1e18), 1) / 1e18


x = np.logspace(-1, 1, 500)

for gamma in [1e-2, 1e-3, 1e-4, 1e-6]:
    y = [get_y(_x, gamma) for _x in x]
    pylab.plot(x, y - (1 - x), label=str(gamma))

pylab.legend()
pylab.grid()
pylab.show()
