import pytest
import brownie
import itertools as it

INITIAL_AMOUNTS = [24000 * 10**6, 10000 * 10**18, 10000 * 10**6, 10000 * 10**6]


@pytest.fixture(scope="module")
def lp_token_amount(alice, crypto_zap, token):
    crypto_zap.add_liquidity(INITIAL_AMOUNTS, 0, {"from": alice})
    token.approve(crypto_zap, 2 ** 256 - 1, {"from": alice})
    return token.balanceOf(alice)


@pytest.mark.parametrize("i,j,scale", it.product(range(4), range(4), [0.3, 0.6, 0.9]))
def test_exchange_underlying(alice, crypto_zap, lp_token_amount, underlying_coins, i, j, scale):
    dx = int(scale * INITIAL_AMOUNTS[i])

    dx_taken = underlying_coins[i].balanceOf(alice)
    dy = underlying_coins[j].balanceOf(alice)

    if i == j:
        with brownie.reverts():
            crypto_zap.exchange_underlying(i, j, dx, 0, {'from': alice})
        return

    min_dy = crypto_zap.get_dy_underlying(i, j, dx)

    with brownie.reverts():
        crypto_zap.exchange_underlying(i, j, dx, int(1.1 * min_dy), {'from': alice})

    crypto_zap.exchange_underlying(i, j, dx, int(0.9 * min_dy), {'from': alice})

    dy = underlying_coins[j].balanceOf(alice) - dy
    dx_taken -= underlying_coins[i].balanceOf(alice)

    assert dx == dx_taken
    assert dy > 0
