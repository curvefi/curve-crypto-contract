import pytest
import brownie


INITIAL_AMOUNTS = [24000 * 10**6, 10000 * 10**18, 10000 * 10**6, 10000 * 10**6]


@pytest.mark.parametrize("idx", range(4))
def test_add_single_coins(alice, crypto_zap, idx, token):
    amounts = [0] * 4
    amounts[idx] = INITIAL_AMOUNTS[idx]

    calc_amount = crypto_zap.calc_token_amount(amounts)
    amount = token.balanceOf(alice)
    crypto_zap.add_liquidity(amounts, 0, {"from": alice})
    amount = token.balanceOf(alice) - amount

    assert amount > 0
    assert abs(amount - calc_amount) / amount < 0.01


def test_add_multiple_coins(alice, crypto_zap, token):
    calc_amount = crypto_zap.calc_token_amount(INITIAL_AMOUNTS)
    crypto_zap.add_liquidity(
        INITIAL_AMOUNTS, 0, {"from": alice}
    )
    amount = token.balanceOf(alice)

    assert amount > 0
    assert abs(amount - calc_amount) / amount < 0.01


def test_add_no_coins(alice, crypto_zap):
    # No coins added, revert in crypto_swap
    with brownie.reverts():
        crypto_zap.add_liquidity([0] * 4, 0, {"from": alice})


@pytest.mark.parametrize("idx", range(4))
def test_alternate_receiver(alice, bob, crypto_zap, idx, token):
    amounts = [0] * 4
    amounts[idx] = INITIAL_AMOUNTS[idx]
    crypto_zap.add_liquidity(amounts, 0, bob, {"from": alice})
    assert token.balanceOf(bob) > 0


def test_min_amount_revert(alice, crypto_zap):
    with brownie.reverts():
        crypto_zap.add_liquidity(
            INITIAL_AMOUNTS, 2 ** 256 - 1, {"from": alice}
        )
