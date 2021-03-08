import pytest
from . import simulation_int_many as sim
from brownie.test import given, strategy
from itertools import permutations
from hypothesis import settings

N_COINS = 3
MAX_SAMPLES = 50  # Increase for fuzzing


@pytest.fixture(scope="module")
def test_math(TestMath, accounts):
    return TestMath.deploy({'from': accounts[0]})


def test_sort(test_math):
    for sample in permutations(range(N_COINS)):
        x = test_math.pub_sort(sample)
        y = sorted(sample, reverse=True)
        assert tuple(x) == tuple(y)


@given(
    x0=strategy('uint256', min_value=10**9, max_value=10**9 * 10**18),
    x1=strategy('uint256', min_value=10**9, max_value=10**9 * 10**18),
    x2=strategy('uint256', min_value=10**9, max_value=10**9 * 10**18)
)
@settings(max_examples=MAX_SAMPLES)
def test_geometric_mean(test_math, x0, x1, x2):
    val = test_math.pub_geometric_mean([x0, x1, x2])
    assert val > 0
    diff = abs((x0 * x1 * x2)**(1/3) - val)
    assert diff / val <= max(1e-10, 1/min([x0, x1, x2]))


def test_reduction_coefficient(test_math):
    assert test_math.pub_reduction_coefficient([10**18, 10**18, 10**18], 0) == 10**18
    assert test_math.pub_reduction_coefficient([10**18, 10**18, 10**18], 10**15) == 10**18
    result = test_math.pub_reduction_coefficient([10**18, 10**18, 10**17], 10**15)
    assert result > 0
    assert result < 10**18
    result = test_math.pub_reduction_coefficient([10**18, 10**18, int(0.999e18)], 10**15)
    assert result > 0
    assert result < 10**18
    assert result > 9 * 10**17


@given(
    x0=strategy('uint256', min_value=10**9, max_value=10**9 * 10**18),
    x1=strategy('uint256', min_value=10**9, max_value=10**9 * 10**18),
    x2=strategy('uint256', min_value=10**9, max_value=10**9 * 10**18),
    gamma=strategy('uint256', min_value=1, max_value=2**100)
)
@settings(max_examples=MAX_SAMPLES)
def test_reduction_coefficient_property(test_math, x0, x1, x2, gamma):
    coeff = test_math.pub_reduction_coefficient([x0, x1, x2], gamma)
    assert coeff <= 10**18


@given(
    x0=strategy('uint256', min_value=10**9, max_value=10**9 * 10**18),
    x1=strategy('uint256', min_value=10**9, max_value=10**9 * 10**18),
    x2=strategy('uint256', min_value=10**9, max_value=10**9 * 10**18),
    gamma=strategy('uint256', min_value=0, max_value=10**17)
)
@settings(max_examples=MAX_SAMPLES)
def test_reduction_coefficient_sim(test_math, x0, x1, x2, gamma):
    result_contract = test_math.pub_reduction_coefficient([x0, x1, x2], gamma)
    result_sim = sim.reduction_coefficient([x0, x1, x2], gamma)
    assert result_contract == result_sim


@given(
       A=strategy('uint256', min_value=1, max_value=10000),
       x=strategy('uint256', min_value=10**9, max_value=10**14 * 10**18),  # 1e-9 USD to 100T USD
       yx=strategy('uint256', min_value=int(5.0001e15), max_value=int(1.999e20)),  # <- ratio 1e18 * y/x, typically 1e18 * 1
       zx=strategy('uint256', min_value=int(5.0001e15), max_value=int(1.999e20)),  # <- ratio 1e18 * z/x, typically 1e18 * 1
       gamma=strategy('uint256', min_value=10**10, max_value=10**16)  # gamma from 1e-8 up to 0.01
)
@settings(max_examples=MAX_SAMPLES)
def test_newton_D(test_math, A, x, yx, zx, gamma):
    X = [x, x * yx // 10**18, x * zx // 10**18]
    result_sim = sim.solve_D(A, gamma, X)
    # test_math.public_newton_D_w(A, gamma, X)
    result_contract = test_math.public_newton_D(A, gamma, X)
    assert abs(result_sim - result_contract) <= max(1000, result_sim/1e15)  # 1000 is $1e-15


@given(
       A=strategy('uint256', min_value=1, max_value=10000),
       D=strategy('uint256', min_value=10**18, max_value=10**14 * 10**18),  # 1 USD to 100T USD
       xD=strategy('uint256', min_value=int(5.001e15), max_value=int(1.999e20)),  # <- ratio 1e18 * x/D, typically 1e18 * 1
       yD=strategy('uint256', min_value=int(5.001e15), max_value=int(1.999e20)),  # <- ratio 1e18 * y/D, typically 1e18 * 1
       zD=strategy('uint256', min_value=int(5.001e15), max_value=int(1.999e20)),  # <- ratio 1e18 * z/D, typically 1e18 * 1
       gamma=strategy('uint256', min_value=10**10, max_value=10**16),  # gamma from 1e-8 up to 0.01
       j=strategy('uint256', min_value=0, max_value=2),
)
@settings(max_examples=MAX_SAMPLES)
def test_newton_y(test_math, A, D, xD, yD, zD, gamma, j):
    X = [D * xD // 10**18, D * yD // 10**18, D * zD // 10**18]
    result_sim = sim.solve_x(A, gamma, X, D, j)
    result_contract = test_math.public_newton_y(A, gamma, X, D, j)
    assert abs(result_sim - result_contract) <= max(10000, result_sim/1e15)  # 10000 is $1e-14


@given(
    strategy('uint256'),
    strategy('uint256', min_value=10, max_value=10**15)
)
@settings(max_examples=MAX_SAMPLES)
def test_exp(test_math, power, precision):
    pow_int = test_math.public_halfpow(power, precision) / 1e18
    pow_ideal = 0.5 ** (power / 1e18)
    assert abs(pow_int - pow_ideal) < max(5 * precision / 1e18, 5e-16)


@given(strategy('uint256', max_value=2**255 // 10**18))
@settings(max_examples=MAX_SAMPLES)
def test_sqrt(test_math, x):
    sqrt_int = test_math.public_sqrt_int(x)
    sqrt_ideal = int((x / 1e18)**0.5 * 1e18)
    assert abs(sqrt_int - sqrt_ideal) <= max(1, sqrt_ideal/1e15)
