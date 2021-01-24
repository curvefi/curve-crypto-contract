import pytest
from brownie.test import given, strategy
from itertools import permutations

N_COINS = 3


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
