import pytest
from brownie.test import given, strategy
from itertools import permutations

N_COINS = 3


@pytest.fixture(scope="module")
def test_math(TestMath, accounts):
    return TestMath.deploy({'from': accounts[0]})


def test_sort(test_math, accounts):
    for sample in permutations(range(N_COINS)):
        x = test_math.pub_sort(sample)
        y = sorted(sample, reverse=True)
        assert tuple(x) == tuple(y)


@given(
    x0=strategy('uint256', min_value=10**9, max_value=10**9 * 10**18),
    x1=strategy('uint256', min_value=10**9, max_value=10**9 * 10**18),
    x2=strategy('uint256', min_value=10**9, max_value=10**9 * 10**18)
)
def test_geometric_mean(test_math, accounts, x0, x1, x2):
    val = test_math.pub_geometric_mean([x0, x1, x2])
    assert val > 0
    diff = abs((x0 * x1 * x2)**(1/3) - val)
    assert diff / val <= max(1e-10, 1/min([x0, x1, x2]))
