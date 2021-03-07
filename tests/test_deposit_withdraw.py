import brownie
from brownie.test import given, strategy
from hypothesis import settings  # noqa
from .conftest import INITIAL_PRICES

MAX_SAMPLES = 50


def test_1st_deposit_and_last_withdraw(crypto_swap, coins, token, accounts):
    user = accounts[1]
    quantities = [10**36 // p for p in [10**18] + INITIAL_PRICES]  # $3 worth
    for coin, q in zip(coins, quantities):
        coin._mint_for_testing(user, q)
        coin.approve(crypto_swap, 2**256-1, {'from': user})

    # Very first deposit
    crypto_swap.add_liquidity(quantities, 0, {'from': user})

    token_balance = token.balanceOf(user)
    assert token_balance == token.totalSupply() > 0
    assert abs(crypto_swap.get_virtual_price() / 1e18 - 1) < 1e-3

    # Empty the contract
    crypto_swap.remove_liquidity(token_balance, [0] * 3, {'from': user})

    assert token.balanceOf(user) == token.totalSupply() == 0


@given(values=strategy('uint256[3]', min_value=10**16, max_value=10**6 * 10**18))
@settings(max_examples=MAX_SAMPLES)
def test_second_deposit(crypto_swap_with_deposit, token, coins, accounts, values):
    user = accounts[1]
    amounts = [v * 10**18 // p for v, p in zip(values, [10**18] + INITIAL_PRICES)]
    for c, v in zip(coins, amounts):
        c._mint_for_testing(user, v)

    calculated = crypto_swap_with_deposit.calc_token_amount(amounts, True)
    measured = token.balanceOf(user)
    crypto_swap_with_deposit.add_liquidity(amounts, int(calculated * 0.999), {'from': user})
    measured = token.balanceOf(user) - measured

    assert calculated == measured


@given(token_amount=strategy('uint256', min_value=10**12, max_value=4000 * 10**18))  # supply is 2400 * 1e18
@settings(max_examples=MAX_SAMPLES)
def test_immediate_withdraw(crypto_swap_with_deposit, token, coins, accounts, token_amount):
    user = accounts[1]

    f = token_amount / token.totalSupply()
    if f <= 1:
        expected = [int(f * crypto_swap_with_deposit.balances(i)) for i in range(3)]
        measured = [c.balanceOf(user) for c in coins]
        crypto_swap_with_deposit.remove_liquidity(
                token_amount,
                [int(0.999 * e) for e in expected],
                {'from': user})
        measured = [c.balanceOf(user) - m for c, m in zip(coins, measured)]
        for e, m in zip(expected, measured):
            assert abs(e - m) / e < 1e-3
    else:
        with brownie.reverts():
            crypto_swap_with_deposit.remove_liquidity(token_amount, [0] * 3, {'from': user})
