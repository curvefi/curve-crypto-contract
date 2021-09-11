import brownie
from . import simulation_int_many as sim
from brownie.test import given, strategy
from hypothesis import settings  # noqa
from .conftest import INITIAL_PRICES

MAX_SAMPLES = 50


def test_1st_deposit_and_last_withdraw(crypto_swap, coins, token, accounts):
    user = accounts[1]
    quantities = [10**36 // p for p in [10**18] + INITIAL_PRICES]  # $2 worth
    for coin, q in zip(coins, quantities):
        coin._mint_for_testing(user, q)
        coin.approve(crypto_swap, 2**256-1, {'from': user})

    # Very first deposit
    crypto_swap.add_liquidity(quantities, 0, {'from': user})

    token_balance = token.balanceOf(user)
    assert token_balance == token.totalSupply() > 0
    assert abs(crypto_swap.get_virtual_price() / 1e18 - 1) < 1e-3

    # Empty the contract
    crypto_swap.remove_liquidity(token_balance, [0] * 2, {'from': user})

    assert token.balanceOf(user) == token.totalSupply() == 0


@given(values=strategy('uint256[2]', min_value=10**16, max_value=10**9 * 10**18))
@settings(max_examples=MAX_SAMPLES)
def test_second_deposit(crypto_swap_with_deposit, token, coins, accounts, values):
    user = accounts[1]
    amounts = [v * 10**18 // p for v, p in zip(values, [10**18] + INITIAL_PRICES)]

    xp = [10**6 * 10**18] * 2
    for i in range(2):
        xp[i] += values[i]
    _A = crypto_swap_with_deposit.A()
    _gamma = crypto_swap_with_deposit.gamma()
    _D = sim.solve_D(_A, _gamma, xp)
    safe = all(f >= 1.1e16 and f <= 0.9e20 for f in [_x * 10**18 // _D for _x in xp])

    for c, v in zip(coins, amounts):
        c._mint_for_testing(user, v)

    try:
        calculated = crypto_swap_with_deposit.calc_token_amount(amounts)
        measured = token.balanceOf(user)
        d_balances = [crypto_swap_with_deposit.balances(i) for i in range(2)]
        crypto_swap_with_deposit.add_liquidity(amounts, int(calculated * 0.999), {'from': user})
        d_balances = [crypto_swap_with_deposit.balances(i) - d_balances[i] for i in range(2)]
        measured = token.balanceOf(user) - measured

        assert abs(calculated - measured) / measured < 1e-10
        assert tuple(amounts) == tuple(d_balances)

    except Exception:
        if safe:
            raise

    # This is to check that we didn't end up in a borked state after
    # a deposit succeeded
    crypto_swap_with_deposit.get_dy(0, 1, 10**16)


@given(value=strategy('uint256', min_value=10**16, max_value=10**6 * 10**18))
@given(i=strategy('uint8', max_value=1))
@settings(max_examples=MAX_SAMPLES)
def test_second_deposit_one(crypto_swap_with_deposit, token, coins, accounts, value, i):
    user = accounts[1]
    amounts = [0] * 2
    amounts[i] = value * 10**18 // ([10**18] + INITIAL_PRICES)[i]
    for c, v in zip(coins, amounts):
        c._mint_for_testing(user, v)

    calculated = crypto_swap_with_deposit.calc_token_amount(amounts)
    measured = token.balanceOf(user)
    d_balances = [crypto_swap_with_deposit.balances(i) for i in range(2)]
    crypto_swap_with_deposit.add_liquidity(amounts, int(calculated * 0.999), {'from': user})
    d_balances = [crypto_swap_with_deposit.balances(i) - d_balances[i] for i in range(2)]
    measured = token.balanceOf(user) - measured

    assert abs(calculated - measured) / measured < 1e-10
    assert tuple(amounts) == tuple(d_balances)


@given(token_amount=strategy('uint256', min_value=10**12, max_value=4000 * 10**18))  # supply is 2400 * 1e18
@settings(max_examples=MAX_SAMPLES)
def test_immediate_withdraw(crypto_swap_with_deposit, token, coins, accounts, token_amount):
    user = accounts[1]

    f = token_amount / token.totalSupply()
    if f <= 1:
        expected = [int(f * crypto_swap_with_deposit.balances(i)) for i in range(2)]
        measured = [c.balanceOf(user) for c in coins]
        d_balances = [crypto_swap_with_deposit.balances(i) for i in range(2)]
        crypto_swap_with_deposit.remove_liquidity(
                token_amount,
                [int(0.999 * e) for e in expected],
                {'from': user})
        d_balances = [d_balances[i] - crypto_swap_with_deposit.balances(i) for i in range(2)]
        measured = [c.balanceOf(user) - m for c, m in zip(coins, measured)]

        for e, m in zip(expected, measured):
            assert abs(e - m) / e < 1e-3

        assert tuple(d_balances) == tuple(measured)

    else:
        with brownie.reverts():
            crypto_swap_with_deposit.remove_liquidity(token_amount, [0] * 2, {'from': user})


@given(
    token_amount=strategy('uint256', min_value=10**12, max_value=4 * 10**6 * 10**18),  # Can be more than we have
    i=strategy('uint8', min_value=0, max_value=1))
@settings(max_examples=MAX_SAMPLES)
def test_immediate_withdraw_one(crypto_swap_with_deposit, token, coins, accounts, token_amount, i):
    user = accounts[1]

    if token_amount >= token.totalSupply():
        with brownie.reverts():
            crypto_swap_with_deposit.calc_withdraw_one_coin(token_amount, i)

    else:
        # Test if we are safe
        xp = [10**6 * 10**18] * 2
        _supply = token.totalSupply()
        _A = crypto_swap_with_deposit.A()
        _gamma = crypto_swap_with_deposit.gamma()
        _D = crypto_swap_with_deposit.D() * (_supply - token_amount) // _supply
        xp[i] = sim.solve_x(_A, _gamma, xp, _D, i)
        safe = all(f >= 1.1e16 and f <= 0.9e20 for f in [_x * 10**18 // _D for _x in xp])

        try:
            calculated = crypto_swap_with_deposit.calc_withdraw_one_coin(token_amount, i)
        except Exception:
            if safe:
                raise
            else:
                return
        measured = coins[i].balanceOf(user)
        d_balances = [crypto_swap_with_deposit.balances(k) for k in range(2)]
        try:
            crypto_swap_with_deposit.remove_liquidity_one_coin(token_amount, i, int(0.999 * calculated), {'from': user})
        except Exception:
            # Check if it could fall into unsafe region here
            frac = (d_balances[i] - calculated) * ([10**18] + INITIAL_PRICES)[i] // crypto_swap_with_deposit.D()
            if frac > 1.1e16 or frac < 0.9e20:
                raise
            else:
                return
        d_balances = [d_balances[k] - crypto_swap_with_deposit.balances(k) for k in range(2)]
        measured = coins[i].balanceOf(user) - measured

        assert calculated == measured

        for k in range(2):
            if k == i:
                assert d_balances[k] == measured
            else:
                assert d_balances[k] == 0

        # This is to check that we didn't end up in a borked state after
        # a withdrawal succeeded
        crypto_swap_with_deposit.get_dy(0, 1, 10**16)
