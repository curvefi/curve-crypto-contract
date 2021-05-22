import brownie
import pytest
from brownie.test import given, strategy
from hypothesis import settings  # noqa
from .conftest import INITIAL_PRICES

MAX_SAMPLES = 50


@given(
    amount=strategy('uint256', min_value=10**6, max_value=2 * 10**6 * 10**18),  # Can be more than we have
    i=strategy('uint8', min_value=0, max_value=3),
    j=strategy('uint8', min_value=0, max_value=3))
@settings(max_examples=MAX_SAMPLES)
def test_exchange(crypto_swap_with_deposit, token, coins, accounts, amount, i, j):
    user = accounts[1]

    if i == j or i > 2 or j > 2:
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


@pytest.mark.parametrize("j", [0, 1])
@given(amount=strategy('uint256', min_value=10**6, max_value=2 * 10**6 * 10**18))
@settings(max_examples=MAX_SAMPLES)
def test_exchange_from_eth(crypto_swap_with_deposit, token, coins, accounts, amount, j):
    user = accounts[1]

    prices = [10**18] + INITIAL_PRICES
    amount = amount * 10**18 // prices[2]

    calculated = crypto_swap_with_deposit.get_dy(2, j, amount)
    measured_i = user.balance()
    measured_j = coins[j].balanceOf(user)
    d_balance_i = crypto_swap_with_deposit.balances(2)
    d_balance_j = crypto_swap_with_deposit.balances(j)

    crypto_swap_with_deposit.exchange(
        2, j, amount, int(0.999 * calculated), True, {'from': user, 'value': amount}
    )

    measured_i -= user.balance()
    measured_j = coins[j].balanceOf(user) - measured_j
    d_balance_i = crypto_swap_with_deposit.balances(2) - d_balance_i
    d_balance_j = crypto_swap_with_deposit.balances(j) - d_balance_j

    assert amount == measured_i
    assert calculated == measured_j

    assert d_balance_i == amount
    assert -d_balance_j == measured_j


@pytest.mark.parametrize("i", [0, 1])
@given(amount=strategy('uint256', min_value=10**6, max_value=2 * 10**6 * 10**18))
@settings(max_examples=MAX_SAMPLES)
def test_exchange_into_eth(crypto_swap_with_deposit, token, coins, accounts, amount, i):
    user = accounts[1]

    prices = [10**18] + INITIAL_PRICES
    amount = amount * 10**18 // prices[i]
    coins[i]._mint_for_testing(user, amount)

    calculated = crypto_swap_with_deposit.get_dy(i, 2, amount)
    measured_i = coins[i].balanceOf(user)
    measured_j = user.balance()
    d_balance_i = crypto_swap_with_deposit.balances(i)
    d_balance_j = crypto_swap_with_deposit.balances(2)

    crypto_swap_with_deposit.exchange(i, 2, amount, int(0.999 * calculated), True, {'from': user})

    measured_i -= coins[i].balanceOf(user)
    measured_j = user.balance() - measured_j
    d_balance_i = crypto_swap_with_deposit.balances(i) - d_balance_i
    d_balance_j = crypto_swap_with_deposit.balances(2) - d_balance_j

    assert amount == measured_i
    assert calculated == measured_j

    assert d_balance_i == amount
    assert -d_balance_j == measured_j


@pytest.mark.parametrize("j", [0, 1])
@pytest.mark.parametrize("modifier", [0, 1.01, 2])
def test_incorrect_eth_amount(crypto_swap_with_deposit, accounts, j, modifier):
    amount = 10**18
    with brownie.reverts("dev: incorrect eth amount"):
        crypto_swap_with_deposit.exchange(
            2, j, amount, 0, True, {'from': accounts[1], 'value': int(amount * modifier)}
        )


@pytest.mark.parametrize("j", [0, 1])
def test_send_eth_without_use_eth(crypto_swap_with_deposit, accounts, j):
    amount = 10**18
    with brownie.reverts("dev: nonzero eth amount"):
        crypto_swap_with_deposit.exchange(
            2, j, amount, 0, False, {'from': accounts[1], 'value': amount}
        )


@pytest.mark.parametrize("i", [0, 1])
def test_send_eth_with_incorrect_i(crypto_swap_with_deposit, accounts, i):
    amount = 10**18
    with brownie.reverts("dev: nonzero eth amount"):
        crypto_swap_with_deposit.exchange(
            i, 2, amount, 0, True, {'from': accounts[1], 'value': amount}
        )
