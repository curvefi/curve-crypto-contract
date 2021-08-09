import brownie
from brownie.test import given, strategy
from hypothesis import settings  # noqa
from .conftest import INITIAL_PRICES

MAX_SAMPLES = 50


@given(
    amount=strategy('uint256', min_value=10**6, max_value=2 * 10**6 * 10**18),  # Can be more than we have
    i=strategy('uint8', min_value=0, max_value=2),
    j=strategy('uint8', min_value=0, max_value=2))
@settings(max_examples=MAX_SAMPLES)
def test_exchange(crypto_swap_with_deposit, token, coins, accounts, amount, i, j):
    user = accounts[1]

    if i == j or i > 1 or j > 1:
        with brownie.reverts():
            crypto_swap_with_deposit.get_dy(i, j, 10**6)
        with brownie.reverts():
            crypto_swap_with_deposit.exchange(i, j, 10**6, 0, {'from': user})

    else:
        prices = [10**18] + INITIAL_PRICES
        amount = amount * 10**18 // prices[i]
        coins[i]._mint_for_testing(user, amount)

        calculated = crypto_swap_with_deposit.get_dy(i, j, amount)
        measured_i = coins[i].balanceOf(user)
        measured_j = coins[j].balanceOf(user)
        d_balance_i = crypto_swap_with_deposit.balances(i)
        d_balance_j = crypto_swap_with_deposit.balances(j)

        crypto_swap_with_deposit.exchange(i, j, amount, int(0.999 * calculated), {'from': user})

        measured_i -= coins[i].balanceOf(user)
        measured_j = coins[j].balanceOf(user) - measured_j
        d_balance_i = crypto_swap_with_deposit.balances(i) - d_balance_i
        d_balance_j = crypto_swap_with_deposit.balances(j) - d_balance_j

        assert amount == measured_i
        assert calculated == measured_j

        assert d_balance_i == amount
        assert -d_balance_j == measured_j
