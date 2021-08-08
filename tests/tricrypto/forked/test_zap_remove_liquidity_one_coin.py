import pytest
import brownie
import itertools as it


INITIAL_AMOUNTS = [40_000 * 10 ** 6, 1.1 * 10 ** 8, 15 * 10 ** 18]


@pytest.fixture(scope="module")
def lp_token_amount(alice, crypto_zap, crypto_lp_token):
    crypto_zap.add_liquidity(
        INITIAL_AMOUNTS, 0, {"from": alice, "value": INITIAL_AMOUNTS[2]}
    )
    crypto_lp_token.approve(crypto_zap, 2 ** 256 - 1, {"from": alice})
    return crypto_lp_token.balanceOf(alice)


@pytest.mark.parametrize("idx", range(3))
def test_remove_one_coin(alice, crypto_zap, coins, lp_token_amount, idx):
    crypto_zap.remove_liquidity_one_coin(lp_token_amount, idx, 0, {"from": alice})

    if idx == 2:
        assert alice.balance() / 10 ** 18 > 100
        return

    assert coins[idx].balanceOf(alice) > INITIAL_AMOUNTS[idx]


@pytest.mark.parametrize("idx,scale", it.product(range(3), [0.3, 0.6, 0.9]))
def test_remove_one_coin_percentage(
    alice, crypto_zap, coins, lp_token_amount, idx, scale
):
    crypto_zap.remove_liquidity_one_coin(
        lp_token_amount * scale, idx, 0, {"from": alice}
    )

    if idx == 2:
        assert alice.balance() / 10 ** 18 > 85 + 15 * scale
        return

    assert coins[idx].balanceOf(alice) > INITIAL_AMOUNTS[idx]


@pytest.mark.parametrize("idx", range(3))
def test_remove_one_coin_min_amount(alice, crypto_zap, coins, lp_token_amount, idx):
    crypto_zap.remove_liquidity_one_coin(
        lp_token_amount, idx, INITIAL_AMOUNTS[idx], {"from": alice}
    )

    if idx == 2:
        assert alice.balance() / 10 ** 18 > 100
        return

    assert coins[idx].balanceOf(alice) > INITIAL_AMOUNTS[idx]


@pytest.mark.parametrize("idx", range(3))
def test_remove_one_coin_alt_receiver(
    alice, bob, crypto_zap, coins, lp_token_amount, idx
):
    crypto_zap.remove_liquidity_one_coin(lp_token_amount, idx, 0, bob, {"from": alice})

    if idx == 2:
        assert bob.balance() / 10 ** 18 > 100
        return

    assert coins[idx].balanceOf(bob) > INITIAL_AMOUNTS[idx]


@pytest.mark.parametrize("idx", range(3))
def test_remove_one_coin_min_amount_revert(alice, crypto_zap, lp_token_amount, idx):
    with brownie.reverts():
        crypto_zap.remove_liquidity_one_coin(
            lp_token_amount, idx, 2 ** 256 - 1, {"from": alice}
        )

