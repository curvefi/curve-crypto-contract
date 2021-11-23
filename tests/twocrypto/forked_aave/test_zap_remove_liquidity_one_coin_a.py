import pytest
import brownie
import itertools as it

INITIAL_AMOUNTS = [24000 * 10**6, 10000 * 10**18, 10000 * 10**6, 10000 * 10**6]


@pytest.fixture(scope="module")
def lp_token_amount(alice, crypto_zap, token):
    crypto_zap.add_liquidity(INITIAL_AMOUNTS, 0, {"from": alice})
    token.approve(crypto_zap, 2 ** 256 - 1, {"from": alice})
    return token.balanceOf(alice)


@pytest.mark.parametrize("idx", range(4))
def test_remove_one_coin(alice, crypto_zap, underlying_coins, lp_token_amount, idx):
    calc_amount = crypto_zap.calc_withdraw_one_coin(lp_token_amount, idx)
    amount = underlying_coins[idx].balanceOf(alice)
    crypto_zap.remove_liquidity_one_coin(lp_token_amount, idx, 0, {"from": alice})
    amount = underlying_coins[idx].balanceOf(alice) - amount

    assert amount > INITIAL_AMOUNTS[idx]
    assert abs(amount - calc_amount) / amount < 0.01


@pytest.mark.parametrize("idx,scale", it.product(range(4), [0.3, 0.6, 0.9]))
def test_remove_one_coin_percentage(
    alice, crypto_zap, underlying_coins, lp_token_amount, idx, scale
):
    calc_amount = crypto_zap.calc_withdraw_one_coin(int(lp_token_amount * scale), idx)
    amount = underlying_coins[idx].balanceOf(alice)
    crypto_zap.remove_liquidity_one_coin(
        int(lp_token_amount * scale), idx, 0, {"from": alice}
    )
    amount = underlying_coins[idx].balanceOf(alice) - amount

    assert amount > INITIAL_AMOUNTS[idx] * scale / 5
    assert abs(amount - calc_amount) / amount < 0.01


@pytest.mark.parametrize("idx", range(4))
def test_remove_one_coin_min_amount(alice, crypto_zap, underlying_coins, lp_token_amount, idx):
    crypto_zap.remove_liquidity_one_coin(
        lp_token_amount, idx, INITIAL_AMOUNTS[idx], {"from": alice}
    )

    assert underlying_coins[idx].balanceOf(alice) > INITIAL_AMOUNTS[idx]


@pytest.mark.parametrize("idx", range(4))
def test_remove_one_coin_alt_receiver(
    alice, bob, crypto_zap, underlying_coins, lp_token_amount, idx
):
    crypto_zap.remove_liquidity_one_coin(lp_token_amount, idx, 0, bob, {"from": alice})

    assert underlying_coins[idx].balanceOf(bob) > INITIAL_AMOUNTS[idx]


@pytest.mark.parametrize("idx", range(4))
def test_remove_one_coin_min_amount_revert(alice, crypto_zap, lp_token_amount, idx):
    with brownie.reverts():
        crypto_zap.remove_liquidity_one_coin(
            lp_token_amount, idx, 2 ** 256 - 1, {"from": alice}
        )
