import pytest
import brownie


INITIAL_AMOUNTS = [40_000 * 10 ** 6, 1.1 * 10 ** 8, 15 * 10 ** 18]


@pytest.fixture(scope="module")
def lp_token_amount(alice, crypto_zap, crypto_lp_token):
    crypto_zap.add_liquidity(
        INITIAL_AMOUNTS, 0, {"from": alice, "value": INITIAL_AMOUNTS[2]}
    )
    crypto_lp_token.approve(crypto_zap, 2 ** 256 - 1, {"from": alice})
    return crypto_lp_token.balanceOf(alice)


def test_remove_all_coins(alice, crypto_zap, coins, lp_token_amount, decimals):
    crypto_zap.remove_liquidity(lp_token_amount, [0] * 3, {"from": alice})

    for idx, coin in enumerate(coins[:-1]):
        assert coin.balanceOf(alice) >= 100_000 * 10 ** decimals[idx]
    # balanced withdrawl
    assert 99 < alice.balance() / 10 ** 18 <= 100


def test_remove_all_coins_min_amount(
    alice, crypto_zap, coins, lp_token_amount, decimals
):
    amounts = [int(amt * 0.5) for amt in INITIAL_AMOUNTS]
    crypto_zap.remove_liquidity(lp_token_amount, amounts, {"from": alice})

    for idx, coin in enumerate(coins[:-1]):
        assert coin.balanceOf(alice) >= 100_000 * 10 ** decimals[idx]
    # balanced withdrawl
    assert 99 < alice.balance() / 10 ** 18 <= 100


def test_alternate_receiver(alice, bob, crypto_zap, coins, lp_token_amount, decimals):
    crypto_zap.remove_liquidity(lp_token_amount, [0] * 3, bob, {"from": alice})

    for coin in coins[:-1]:
        assert coin.balanceOf(bob) >= 0
    assert bob.balance() / 10 ** 18 >= 100


@pytest.mark.parametrize("scale", [0.2, 0.4, 0.6, 0.8])
def test_remove_percentage_of_coins_min_amount_revert(
    alice, crypto_zap, lp_token_amount, scale
):
    with brownie.reverts():
        crypto_zap.remove_liquidity(
            lp_token_amount * scale, INITIAL_AMOUNTS, {"from": alice}
        )


def test_remove_all_coins_min_amount_revert(alice, crypto_zap, lp_token_amount):
    with brownie.reverts():
        crypto_zap.remove_liquidity(
            lp_token_amount, [2 ** 256 - 1] * 3, {"from": alice}
        )
