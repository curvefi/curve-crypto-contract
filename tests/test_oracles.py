from math import log2, log
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
    token_frac=strategy('uint256', min_value=10**6, max_value=10**16),
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


@given(
    amount=strategy('uint256', min_value=10**6, max_value=2 * 10**6 * 10**18),  # Can be more than we have
    i=strategy('uint8', min_value=0, max_value=2),
    j=strategy('uint8', min_value=0, max_value=2),
    t=strategy('uint256', min_value=10, max_value=10 * 86400))
@settings(max_examples=MAX_SAMPLES)
def test_ma(chain, crypto_swap_with_deposit, token, coins, accounts, amount, i, j, t):
    user = accounts[1]
    if i == j:
        return

    prices1 = [10**18] + INITIAL_PRICES
    amount = amount * 10**18 // prices1[i]
    coins[i]._mint_for_testing(user, amount)

    half_time = crypto_swap_with_deposit.ma_half_time()

    out = coins[j].balanceOf(user)
    crypto_swap_with_deposit.exchange(i, j, amount, 0, {'from': user})
    out = coins[j].balanceOf(user) - out

    prices2 = [crypto_swap_with_deposit.last_prices(k) for k in [0, 1]]

    chain.sleep(t)
    crypto_swap_with_deposit.remove_liquidity_one_coin(10**15, 0, 0, {'from': user})

    prices3 = [crypto_swap_with_deposit.price_oracle(k) for k in [0, 1]]

    for p1, p2, p3 in zip(INITIAL_PRICES, prices2, prices3):
        alpha = 0.5 ** (t / half_time)
        theory = p1 * alpha + p2 * (1 - alpha)
        assert abs(log2(theory / p3)) < 1e-3


# Sanity check for price scale
@given(
    amount=strategy('uint256', min_value=10**6, max_value=2 * 10**6 * 10**18),  # Can be more than we have
    i=strategy('uint8', min_value=0, max_value=2),
    j=strategy('uint8', min_value=0, max_value=2),
    t=strategy('uint256', max_value=10 * 86400))
@settings(max_examples=MAX_SAMPLES)
def test_price_scale_range(chain, crypto_swap_with_deposit, coins, accounts, amount, i, j, t):
    user = accounts[1]
    if i == j:
        return

    prices1 = [10**18] + INITIAL_PRICES
    amount = amount * 10**18 // prices1[i]
    coins[i]._mint_for_testing(user, amount)

    out = coins[j].balanceOf(user)
    crypto_swap_with_deposit.exchange(i, j, amount, 0, {'from': user})
    out = coins[j].balanceOf(user) - out

    prices2 = [crypto_swap_with_deposit.last_prices(k) for k in [0, 1]]

    chain.sleep(t)
    crypto_swap_with_deposit.remove_liquidity_one_coin(10**15, 0, 0, {'from': user})

    prices3 = [crypto_swap_with_deposit.price_scale(k) for k in [0, 1]]

    for p1, p2, p3 in zip(INITIAL_PRICES, prices2, prices3):
        if p1 > p2:
            assert p3 <= p1 and p3 >= p2
        else:
            assert p3 >= p1 and p3 <= p2


@given(
    i=strategy('uint8', min_value=0, max_value=2),
    j=strategy('uint8', min_value=0, max_value=2))
def test_price_scale_change(chain, crypto_swap_with_deposit, i, j, coins, accounts):
    amount = 10**5 * 10**18
    t = 86400

    user = accounts[1]
    if i == j:
        return

    prices1 = [10**18] + INITIAL_PRICES
    amount = amount * 10**18 // prices1[i]
    coins[i]._mint_for_testing(user, amount)

    out = coins[j].balanceOf(user)
    crypto_swap_with_deposit.exchange(i, j, amount, 0, {'from': user})
    out = coins[j].balanceOf(user) - out

    price_scale_1 = [crypto_swap_with_deposit.price_scale(i) for i in range(2)]

    prices2 = [crypto_swap_with_deposit.last_prices(k) for k in [0, 1]]
    if i == 0:
        out_price = amount * 10**18 // out
        ix = j
    elif j == 0:
        out_price = out * 10**18 // amount
        ix = i
    else:
        ix = j
        out_price = amount * prices1[i] // out

    assert out_price == prices2[ix-1]
    chain.sleep(t)

    coins[0]._mint_for_testing(user, 10**18)
    crypto_swap_with_deposit.exchange(0, 1, 10**18, 0, {'from': user})
    price_scale_2 = [crypto_swap_with_deposit.price_scale(i) for i in range(2)]

    price_diff = abs(log(price_scale_2[ix-1] / price_scale_1[ix-1]))
    assert abs(log(price_diff / (crypto_swap_with_deposit.adjustment_step() / 1e18))) < 1e-2
