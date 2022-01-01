import pytest
import brownie
from brownie.test import given, strategy


@pytest.fixture(scope="module", autouse=True)
def zap(CallbackTestZap, crypto_swap_with_deposit, coins, accounts):
    user = accounts[0]
    zap = CallbackTestZap.deploy(crypto_swap_with_deposit, {'from': user})
    coins[0].approve(zap, 2**256 - 1, {'from': user})
    coins[1].approve(zap, 2**256 - 1, {'from': user})
    return zap


@given(i=strategy('uint8', max_value=1))
@given(amount=strategy('uint256', min_value=1000 * 10**6, max_value=100 * 10**18))
def test_good(crypto_swap_with_deposit, zap, coins, accounts, i, amount):
    user = accounts[0]

    dy = crypto_swap_with_deposit.get_dy(i, 1-i, amount)

    coins[i]._mint_for_testing(user, amount // 2)
    with brownie.reverts():
        zap.good_exchange(i, 1-i, amount, 0, {'from': user})

    coins[i]._mint_for_testing(user, amount - amount // 2)

    in_0 = coins[i].balanceOf(user)
    out_0 = coins[1-i].balanceOf(user)
    zap.good_exchange(i, 1-i, amount, 0, {'from': user})
    in_1 = coins[i].balanceOf(user)
    out_1 = coins[1-i].balanceOf(user)

    assert in_0 - in_1 == amount
    assert out_1 - out_0 == dy
    assert zap.input_amount() == amount
    assert zap.output_amount() == dy


@given(i=strategy('uint8', max_value=1))
@given(amount=strategy('uint256', min_value=1000 * 10**6, max_value=100 * 10**18))
def test_evil(crypto_swap_with_deposit, zap, coins, accounts, i, amount):
    user = accounts[0]

    coins[i]._mint_for_testing(user, amount * 2)
    zap.set_evil_input_amount(amount * 2)
    with brownie.reverts():
        zap.evil_exchange(i, 1-i, amount, 0, {'from': user})
    zap.set_evil_input_amount(amount // 2)
    with brownie.reverts():
        zap.evil_exchange(i, 1-i, amount, 0, {'from': user})

    zap.set_evil_input_amount(amount)
    zap.evil_exchange(i, 1-i, amount, 0, {'from': user})
