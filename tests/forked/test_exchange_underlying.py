import itertools as it

import brownie
import pytest


@pytest.mark.parametrize("idx,jdx", it.product(range(5), repeat=2))
def test_exchange_underlying_coins(
    alice, crypto_zap, deposit_amounts, underlying_coins, idx, jdx
):
    dx = deposit_amounts[idx] * 0.05
    # exchanging wbtc <> wbtc or weth <> weth
    revert_cases = [(3, 3), (4, 4)]
    if (idx, jdx) in revert_cases:
        with brownie.reverts():
            crypto_zap.exchange_underlying(idx, jdx, dx, 0, {"from": alice})
        return

    start_bal_i = underlying_coins[idx].balanceOf(alice)
    start_bal_j = underlying_coins[jdx].balanceOf(alice)

    crypto_zap.exchange_underlying(idx, jdx, dx, 0, {"from": alice})

    if (idx, jdx) in zip(range(3), range(3)):
        assert underlying_coins[idx].balanceOf(alice) < start_bal_i
    else:
        assert underlying_coins[idx].balanceOf(alice) < start_bal_i
        assert underlying_coins[jdx].balanceOf(alice) > start_bal_j


@pytest.mark.parametrize("idx,jdx", it.product(range(5), repeat=2))
def test_alternate_receiver(
    alice, bob, crypto_zap, deposit_amounts, underlying_coins, idx, jdx
):
    dx = deposit_amounts[idx] * 0.05
    # exchanging wbtc <> wbtc or weth <> weth
    revert_cases = [(3, 3), (4, 4)]
    if (idx, jdx) in revert_cases:
        with brownie.reverts():
            crypto_zap.exchange_underlying(idx, jdx, dx, 0, bob, {"from": alice})
        return

    start_bal_i = underlying_coins[idx].balanceOf(alice)

    crypto_zap.exchange_underlying(idx, jdx, dx, 0, bob, {"from": alice})

    assert underlying_coins[idx].balanceOf(alice) < start_bal_i
    assert underlying_coins[jdx].balanceOf(bob) > 0


def test_min_dy_revert(alice, crypto_zap):
    with brownie.reverts():
        crypto_zap.exchange_underlying(
            0, 4, 250 * 10 ** 18, 2 * 10 ** 18, {"from": alice}
        )
