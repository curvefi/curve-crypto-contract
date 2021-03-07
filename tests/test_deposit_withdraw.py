from brownie.test import given, strategy
from .conftest import INITIAL_PRICES


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


@given(values=strategy('uint256[3]', min_value=0, max_value=10**6 * 10**18))
def test_second_deposit(crypto_swap_with_deposit, coins, accounts, values):
    user = accounts[1]
    if all(v == 0 for v in values):
        return
    amounts = [v * 10**18 // p for v, p in zip(values, [10**18] + INITIAL_PRICES)]
    for c, v in zip(coins, amounts):
        c._mint_for_testing(user, v)

    crypto_swap_with_deposit.add_liquidity(amounts, 0, {'from': user})
