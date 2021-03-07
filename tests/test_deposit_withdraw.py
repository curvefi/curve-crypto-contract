from .conftest import INITIAL_PRICES


def test_1st_deposit_and_last_withdraw(crypto_swap, coins, token, accounts, crypto_math):
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
