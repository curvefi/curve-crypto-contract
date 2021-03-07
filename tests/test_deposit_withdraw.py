from .conftest import INITIAL_PRICES


def test_deposit_and_withdraw(crypto_swap, coins, token, accounts, crypto_math):
    user = accounts[1]
    quantities = [10**36 // p for p in [10**18] + INITIAL_PRICES]
    for coin, q in zip(coins, quantities):
        coin._mint_for_testing(user, q)
        coin.approve(crypto_swap, 2**256-1, {'from': user})

    # Very first deposit
    crypto_swap.add_liquidity(quantities, 0, {'from': user})
