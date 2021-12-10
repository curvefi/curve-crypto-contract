import pytest
import brownie

INITIAL_AMOUNTS = [24000 * 10**6, 10000 * 10**18, 10000 * 10**6, 10000 * 10**6]


@pytest.fixture(scope="module")
def lp_token_amount(alice, crypto_zap, token):
    crypto_zap.add_liquidity(INITIAL_AMOUNTS, 0, {"from": alice})
    token.approve(crypto_zap, 2 ** 256 - 1, {"from": alice})
    return token.balanceOf(alice)


def test_remove_all_coins(alice, crypto_zap, underlying_coins, lp_token_amount, base_decimals):
    balances = [c.balanceOf(alice) for c in underlying_coins]

    crypto_zap.remove_liquidity(lp_token_amount, [0] * 4, {"from": alice})

    assert underlying_coins[0].balanceOf(alice) >= balances[0] + 0.97 * INITIAL_AMOUNTS[0]

    usd = sum((underlying_coins[i].balanceOf(alice) - balances[i]) * 10**(18 - base_decimals[i - 1]) for i in range(1, 4))
    assert usd >= 0.97 * sum(INITIAL_AMOUNTS[i] * 10**(18 - base_decimals[i - 1]) for i in range(1, 4))


def test_remove_all_coins_min_amount(
    alice, crypto_zap, underlying_coins, lp_token_amount, decimals, base_decimals, stable_swap
):
    balances = [c.balanceOf(alice) for c in underlying_coins]

    stable_precisions = [1, 10**12, 10**12]
    total = sum(stable_swap.balances(i) * stable_precisions[i] for i in range(3))
    frac = [stable_swap.balances(i) * stable_precisions[i] / total for i in range(3)]
    total = sum(INITIAL_AMOUNTS[i+1] * stable_precisions[i] for i in range(3))

    amounts = [int(0.9 * INITIAL_AMOUNTS[0])] + [int(0.9 * frac[i] * total / stable_precisions[i]) for i in range(3)]
    crypto_zap.remove_liquidity(lp_token_amount, amounts, {"from": alice})

    assert underlying_coins[0].balanceOf(alice) >= balances[0] + 0.97 * INITIAL_AMOUNTS[0]

    usd = sum((underlying_coins[i].balanceOf(alice) - balances[i]) * 10**(18 - base_decimals[i - 1]) for i in range(1, 4))
    assert usd >= 0.97 * sum(INITIAL_AMOUNTS[i] * 10**(18 - base_decimals[i - 1]) for i in range(1, 4))


def test_alternate_receiver(alice, bob, crypto_zap, underlying_coins, lp_token_amount, decimals):
    crypto_zap.remove_liquidity(lp_token_amount, [0] * 4, bob, {"from": alice})

    for coin in underlying_coins:
        assert coin.balanceOf(bob) >= 0


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
            lp_token_amount, [2 ** 256 - 1] * 4, {"from": alice}
        )
