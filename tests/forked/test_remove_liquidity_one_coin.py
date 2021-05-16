import brownie
import numpy as np
import pytest


@pytest.fixture(scope="module")
def lp_balance(alice, crypto_zap, deposit_amounts, crypto_lp_token):
    crypto_zap.add_liquidity(deposit_amounts, 0, {"from": alice})
    crypto_lp_token.approve(crypto_zap, 2 ** 256 - 1, {"from": alice})
    return crypto_lp_token.balanceOf(alice)


@pytest.mark.parametrize("percentage", np.linspace(1, 0.01, 6))
def test_burn_varying_lp_amount(
    alice, bob, crypto_zap, DAI, percentage, lp_balance, crypto_lp_token
):
    amount = int(lp_balance * percentage) if percentage != 1 else lp_balance
    crypto_zap.remove_liquidity_one_coin(amount, 0, 0, bob, {"from": alice})
    assert crypto_lp_token.balanceOf(alice) == lp_balance - amount
    assert DAI.balanceOf(bob) > 0


@pytest.mark.parametrize("idx", range(8))
def test_different_idx(alice, idx, underlying_coins, crypto_zap, lp_balance, decimals):
    if idx > 4:
        with brownie.reverts():
            crypto_zap.remove_liquidity_one_coin(lp_balance, idx, 0, {"from": alice})
        return

    crypto_zap.remove_liquidity_one_coin(lp_balance, idx, 0, {"from": alice})

    assert underlying_coins[idx].balanceOf(alice) > 1_000 * 10 ** decimals[idx]


@pytest.mark.parametrize("idx", range(8))
def test_alternate_receiver(alice, bob, idx, underlying_coins, crypto_zap, lp_balance):
    if idx > 4:
        with brownie.reverts():
            crypto_zap.remove_liquidity_one_coin(
                lp_balance, idx, 0, bob, {"from": alice}
            )
        return

    crypto_zap.remove_liquidity_one_coin(lp_balance, idx, 0, bob, {"from": alice})

    assert underlying_coins[idx].balanceOf(bob) > 0


@pytest.mark.parametrize("idx", range(5))
def test_revert_min_amount(alice, idx, crypto_zap, lp_balance):
    with brownie.reverts():
        crypto_zap.remove_liquidity_one_coin(
            lp_balance, idx, 2 ** 256 - 1, {"from": alice}
        )

    min_amt = crypto_zap.calc_withdraw_one_coin(lp_balance, idx)

    crypto_zap.remove_liquidity_one_coin(lp_balance, idx, min_amt, {"from": alice})
