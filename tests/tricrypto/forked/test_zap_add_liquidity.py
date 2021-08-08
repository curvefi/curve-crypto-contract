import pytest
import brownie


INITIAL_AMOUNTS = [40_000 * 10 ** 6, 1.1 * 10 ** 8, 15 * 10 ** 18]


@pytest.mark.parametrize("idx", range(3))
def test_add_single_coins(alice, crypto_zap, idx, crypto_lp_token):
    amounts = [0, 0, 0]
    amounts[idx] = INITIAL_AMOUNTS[idx]
    if idx == 2:
        crypto_zap.add_liquidity(
            amounts, 0, {"from": alice, "value": INITIAL_AMOUNTS[idx]}
        )
    else:
        crypto_zap.add_liquidity(amounts, 0, {"from": alice})
    assert crypto_lp_token.balanceOf(alice) > 0


def test_add_multiple_coins(alice, crypto_zap, crypto_lp_token):
    crypto_zap.add_liquidity(
        INITIAL_AMOUNTS, 0, {"from": alice, "value": INITIAL_AMOUNTS[2]}
    )

    assert crypto_lp_token.balanceOf(alice) > 0


def test_add_no_coins(alice, crypto_zap):
    # No coins added, revert in crypto_swap
    with brownie.reverts():
        crypto_zap.add_liquidity([0] * 3, 0, {"from": alice, "value": 0})


@pytest.mark.parametrize("idx", range(4))
def test_alternate_receiver(alice, bob, crypto_zap, idx, crypto_lp_token):
    if idx == 3:
        crypto_zap.add_liquidity(
            INITIAL_AMOUNTS, 0, bob, {"from": alice, "value": INITIAL_AMOUNTS[2]}
        )
        assert crypto_lp_token.balanceOf(bob) > 0
        return

    amounts = [0, 0, 0]
    amounts[idx] = INITIAL_AMOUNTS[idx]
    if idx == 2:
        crypto_zap.add_liquidity(
            amounts, 0, bob, {"from": alice, "value": INITIAL_AMOUNTS[idx]}
        )
    else:
        crypto_zap.add_liquidity(amounts, 0, bob, {"from": alice})
    assert crypto_lp_token.balanceOf(bob) > 0


@pytest.mark.parametrize("scale", [0.5, 0.75, 1.02, 1.25])
def test_invalid_eth_amount_specified_revert(alice, crypto_zap, scale):
    with brownie.reverts():
        crypto_zap.add_liquidity(
            INITIAL_AMOUNTS, 0, {"from": alice, "value": INITIAL_AMOUNTS[2] * scale}
        )


def test_min_amount_revert(alice, crypto_zap):
    with brownie.reverts():
        crypto_zap.add_liquidity(
            INITIAL_AMOUNTS, 2 ** 256 - 1, {"from": alice, "value": INITIAL_AMOUNTS[2]}
        )

