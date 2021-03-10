from math import log2
from brownie.test import strategy, given
from hypothesis import settings
from .conftest import INITIAL_PRICES

MAX_SAMPLES = 50


def test_initial(crypto_swap_with_deposit):
    for i in range(2):
        assert crypto_swap_with_deposit.price_scale(i) == INITIAL_PRICES[i]
        assert crypto_swap_with_deposit.price_oracle(i) == INITIAL_PRICES[i]


@given(
    amount=strategy('uint256', min_value=10**6, max_value=2 * 10**6 * 10**18),  # Can be more than we have
    i=strategy('uint8', min_value=0, max_value=2),
    j=strategy('uint8', min_value=0, max_value=2))
@settings(max_examples=MAX_SAMPLES)
def test_last_price_exchange(crypto_swap_with_deposit, token, coins, accounts, amount, i, j):
    user = accounts[1]
    if i == j:
        return

    prices = [10**18] + INITIAL_PRICES
    amount = amount * 10**18 // prices[i]
    coins[i]._mint_for_testing(user, amount)

    out = coins[j].balanceOf(user)
    crypto_swap_with_deposit.exchange(i, j, amount, 0, {'from': user})
    out = coins[j].balanceOf(user) - out

    if amount <= 10**5 or out <= 10**5:
        # A very rough sanity check
        for k in [1, 2]:
            oracle_price = crypto_swap_with_deposit.last_prices(k-1)
            assert abs(log2(oracle_price / prices[k])) < 1
        return

    if i > 0 and j > 0:
        price_j = crypto_swap_with_deposit.last_prices(i-1) * amount // out
        assert price_j == crypto_swap_with_deposit.last_prices(j-1)
    elif i == 0:
        price_j = amount * 10**18 // out
        assert price_j == crypto_swap_with_deposit.last_prices(j-1)
    else:  # j == 0
        price_i = out * 10**18 // amount
        assert price_i == crypto_swap_with_deposit.last_prices(i-1)


@given(
    token_frac=strategy('uint256', min_value=10**6, max_value=10**17),
    i=strategy('uint8', min_value=0, max_value=2))
@settings(max_examples=MAX_SAMPLES)
def test_last_price_remove_liq(crypto_swap_with_deposit, token, coins, accounts, token_frac, i):
    user = accounts[1]

    prices = [10**18] + INITIAL_PRICES
    token_amount = token_frac * token.totalSupply() // 10**18

    out = coins[i].balanceOf(user)
    crypto_swap_with_deposit.remove_liquidity_one_coin(token_amount, i, 0, {'from': user})
    out = coins[i].balanceOf(user) - out

    for k in [1, 2]:
        oracle_price = crypto_swap_with_deposit.last_prices(k-1)
        assert abs(log2(oracle_price / prices[k])) < 0.1
