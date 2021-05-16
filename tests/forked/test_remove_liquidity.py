import brownie
import numpy as np
import pytest

np.random.seed(42)


@pytest.fixture(scope="module")
def lp_balance(alice, chain, crypto_zap, deposit_amounts, crypto_lp_token):
    crypto_zap.add_liquidity(deposit_amounts, 0, {"from": alice})
    crypto_lp_token.approve(crypto_zap, 2 ** 256 - 1, {"from": alice})
    chain.mine(timedelta=86400 * 31)
    return crypto_lp_token.balanceOf(alice)


def test_retrieve_deposits_back(
    alice,
    bob,
    crypto_zap,
    underlying_coins,
    deposit_amounts,
    crypto_lp_token,
    lp_balance,
):
    crypto_zap.remove_liquidity(lp_balance, [0] * 5, bob, {"from": alice})

    assert crypto_lp_token.balanceOf(alice) == 0
    for coin, amount in zip(underlying_coins, deposit_amounts):
        coin.balanceOf(bob) == amount


def test_remove_min(
    alice,
    bob,
    crypto_zap,
    underlying_coins,
    deposit_amounts,
    crypto_lp_token,
    lp_balance,
):
    scaler = np.linspace(0, 1, 5)
    amounts = (deposit_amounts * scaler).tolist()
    amounts = [int(amt) for amt in amounts]

    crypto_zap.remove_liquidity(lp_balance, amounts, bob, {"from": alice})

    assert crypto_lp_token.balanceOf(alice) == 0
    for coin, amount in zip(underlying_coins, deposit_amounts):
        coin.balanceOf(bob) == amount


def test_revert_invalid_min_amounts(alice, crypto_zap, lp_balance):
    with brownie.reverts():
        crypto_zap.remove_liquidity(lp_balance, [2 ** 256 - 1] * 5, {"from": alice})
