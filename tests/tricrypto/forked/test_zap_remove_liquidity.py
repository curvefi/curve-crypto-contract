import pytest
import brownie


@pytest.fixture(scope="module")
def initial_amounts(crypto_swap):
    usd = 40_000
    usdt = usd * 10**6
    wbtc = usd * 10**18 * 10**8 // crypto_swap.price_oracle(0)
    weth = usd * (10**18)**2 // crypto_swap.price_oracle(1)
    return [usdt, wbtc, weth]


@pytest.fixture(scope="module")
def lp_token_amount(alice, crypto_zap, crypto_lp_token, initial_amounts):
    crypto_zap.add_liquidity(
        initial_amounts, 0, {"from": alice, "value": initial_amounts[2]}
    )
    crypto_lp_token.approve(crypto_zap, 2 ** 256 - 1, {"from": alice})
    return crypto_lp_token.balanceOf(alice)


def test_remove_all_coins(alice, crypto_zap, coins, lp_token_amount, initial_amounts):
    balances = [c.balanceOf(alice) for c in coins[:-1]] + [alice.balance()]

    crypto_zap.remove_liquidity(lp_token_amount, [0] * 3, {"from": alice})

    for i in range(len(coins) - 1):
        assert coins[i].balanceOf(alice) >= balances[i] + 0.99 * initial_amounts[i]
    # balanced withdrawal
    assert alice.balance() > balances[-1] + 0.99 * initial_amounts[-1]


def test_remove_all_coins_min_amount(
    alice, crypto_zap, coins, lp_token_amount, decimals, initial_amounts
):
    balances = [c.balanceOf(alice) for c in coins[:-1]] + [alice.balance()]

    amounts = [int(amt * 0.5) for amt in initial_amounts]
    crypto_zap.remove_liquidity(lp_token_amount, amounts, {"from": alice})

    for i in range(len(coins) - 1):
        assert coins[i].balanceOf(alice) >= balances[i] + 0.99 * initial_amounts[i]
    # balanced withdrawal
    assert alice.balance() > balances[-1] + 0.99 * initial_amounts[-1]


def test_alternate_receiver(alice, bob, crypto_zap, coins, lp_token_amount, decimals):
    crypto_zap.remove_liquidity(lp_token_amount, [0] * 3, bob, {"from": alice})

    for coin in coins[:-1]:
        assert coin.balanceOf(bob) >= 0
    assert bob.balance() / 10 ** 18 >= 100


@pytest.mark.parametrize("scale", [0.2, 0.4, 0.6, 0.8])
def test_remove_percentage_of_coins_min_amount_revert(
    alice, crypto_zap, lp_token_amount, scale, initial_amounts
):
    with brownie.reverts():
        crypto_zap.remove_liquidity(
            lp_token_amount * scale, initial_amounts, {"from": alice}
        )


def test_remove_all_coins_min_amount_revert(alice, crypto_zap, lp_token_amount):
    with brownie.reverts():
        crypto_zap.remove_liquidity(
            lp_token_amount, [2 ** 256 - 1] * 3, {"from": alice}
        )
