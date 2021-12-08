from math import log2, log
from brownie.test import strategy, given
from hypothesis import settings
from .conftest import INITIAL_PRICES

MAX_SAMPLES = 50


def approx(x1, x2, precision):
    return abs(log(x1 / x2)) <= precision


def test_initial(crypto_swap_with_deposit):
    assert crypto_swap_with_deposit.price_scale() == INITIAL_PRICES[0]
    assert crypto_swap_with_deposit.price_oracle() == INITIAL_PRICES[0]


@given(
    amount=strategy('uint256', min_value=10**6, max_value=2 * 10**6 * 10**18),  # Can be more than we have
    i=strategy('uint8', min_value=0, max_value=1))
@settings(max_examples=MAX_SAMPLES)
def test_last_price_exchange(crypto_swap_with_deposit, token, coins, accounts, amount, i):
    user = accounts[1]
    j = 1 - i

    prices = [10**18] + INITIAL_PRICES
    amount = amount * 10**18 // prices[i]
    coins[i]._mint_for_testing(user, amount)

    out = coins[j].balanceOf(user)
    crypto_swap_with_deposit.exchange(i, j, amount, 0, {'from': user})
    out = coins[j].balanceOf(user) - out

    if amount <= 10**5 or out <= 10**5:
        # A very rough sanity check
        oracle_price = crypto_swap_with_deposit.last_prices()
        assert abs(log2(oracle_price / prices[1])) < 1
        return

    if i == 0:
        price_j = amount * 10**18 // out
        assert approx(price_j, crypto_swap_with_deposit.last_prices(), 2e-10)
    else:  # j == 0
        price_i = out * 10**18 // amount
        assert approx(price_i, crypto_swap_with_deposit.last_prices(), 2e-10)


@given(
    token_frac=strategy('uint256', min_value=10**6, max_value=10**16),
    i=strategy('uint8', min_value=0, max_value=1))
@settings(max_examples=MAX_SAMPLES)
def test_last_price_remove_liq(crypto_swap_with_deposit, token, coins, accounts, token_frac, i):
    user = accounts[1]

    prices = [10**18] + INITIAL_PRICES
    token_amount = token_frac * token.totalSupply() // 10**18

    crypto_swap_with_deposit.remove_liquidity_one_coin(token_amount, i, 0, {'from': user})

    oracle_price = crypto_swap_with_deposit.last_prices()
    assert abs(log2(oracle_price / prices[1])) < 0.1


@given(
    amount=strategy('uint256', min_value=10**6, max_value=2 * 10**6 * 10**18),  # Can be more than we have
    i=strategy('uint8', min_value=0, max_value=1),
    t=strategy('uint256', min_value=10, max_value=10 * 86400))
@settings(max_examples=MAX_SAMPLES)
def test_ma(chain, crypto_swap_with_deposit, token, coins, accounts, amount, i, t):
    user = accounts[1]
    j = 1 - i

    prices1 = [10**18] + INITIAL_PRICES
    amount = amount * 10**18 // prices1[i]
    coins[i]._mint_for_testing(user, amount)

    half_time = crypto_swap_with_deposit.ma_half_time()

    crypto_swap_with_deposit.exchange(i, j, amount, 0, {'from': user})

    p2 = crypto_swap_with_deposit.last_prices()

    chain.sleep(t)
    crypto_swap_with_deposit.remove_liquidity_one_coin(10**15, 0, 0, {'from': user})

    p3 = crypto_swap_with_deposit.price_oracle()

    p1 = INITIAL_PRICES[0]
    alpha = 0.5 ** (t / half_time)
    theory = p1 * alpha + p2 * (1 - alpha)
    assert abs(log2(theory / p3)) < 1e-3


# Sanity check for price scale
@given(
    amount=strategy('uint256', min_value=10**6, max_value=2 * 10**6 * 10**18),  # Can be more than we have
    i=strategy('uint8', min_value=0, max_value=1),
    t=strategy('uint256', max_value=10 * 86400))
@settings(max_examples=MAX_SAMPLES)
def test_price_scale_range(chain, crypto_swap_with_deposit, coins, accounts, amount, i, t):
    user = accounts[1]
    j = 1 - i

    prices1 = [10**18] + INITIAL_PRICES
    amount = amount * 10**18 // prices1[i]
    coins[i]._mint_for_testing(user, amount)

    crypto_swap_with_deposit.exchange(i, j, amount, 0, {'from': user})

    p2 = crypto_swap_with_deposit.last_prices()

    chain.sleep(t)
    crypto_swap_with_deposit.remove_liquidity_one_coin(10**15, 0, 0, {'from': user})

    p3 = crypto_swap_with_deposit.price_scale()

    p1 = INITIAL_PRICES[0]
    if p1 > p2:
        assert p3 <= p1 and p3 >= p2
    else:
        assert p3 >= p1 and p3 <= p2


@given(
    i=strategy('uint8', min_value=0, max_value=1))
def test_price_scale_change(chain, crypto_swap_with_deposit, i, coins, accounts):
    j = 1 - i
    amount = 10**5 * 10**18
    t = 86400

    user = accounts[1]

    prices1 = [10**18] + INITIAL_PRICES
    amount = amount * 10**18 // prices1[i]
    coins[i]._mint_for_testing(user, amount)

    out = coins[j].balanceOf(user)
    crypto_swap_with_deposit.exchange(i, j, amount, 0, {'from': user})
    out = coins[j].balanceOf(user) - out

    prices2 = crypto_swap_with_deposit.last_prices()
    if i == 0:
        out_price = amount * 10**18 // out
    else:
        out_price = out * 10**18 // amount

    assert approx(out_price, prices2, 2e-10)

    crypto_swap_with_deposit.exchange(j, i, int(out * 0.95), 0, {'from': user})

    price_scale_1 = crypto_swap_with_deposit.price_scale()

    chain.sleep(t)

    coins[0]._mint_for_testing(user, 10**18)
    crypto_swap_with_deposit.exchange(0, 1, 10**18, 0, {'from': user})
    step = max(crypto_swap_with_deposit.adjustment_step() / 1e18,
               abs(log(crypto_swap_with_deposit.price_oracle() / crypto_swap_with_deposit.price_scale())) / 10)
    price_scale_2 = crypto_swap_with_deposit.price_scale()

    price_diff = abs(log(price_scale_2 / price_scale_1))
    assert price_diff > 0 and abs(log(price_diff / step)) < 2e-1

    assert approx(crypto_swap_with_deposit.virtual_price(), crypto_swap_with_deposit.get_virtual_price(), 1e-10)
