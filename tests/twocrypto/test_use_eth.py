import pytest
from brownie import compile_source
from brownie.test import given, strategy

VYPER_VERSION = "0.3.0"  # Forced version, use None when brownie supports the new version
INITIAL_PRICES = [int(0.001 * 10**18)]  # CRV/EUR


# Fixtures
@pytest.fixture(scope="module")
def weth(WETH, accounts):
    yield WETH.deploy({'from': accounts[-1], 'value': accounts[-1].balance()})


@pytest.fixture(scope="module", autouse=True)
def coins(ERC20Mock, accounts, weth):
    yield [weth] + [ERC20Mock.deploy('CRV', 'CRV', 18, {"from": accounts[0]})]


@pytest.fixture(scope="module", autouse=True)
def token(CurveTokenV4, accounts):
    yield CurveTokenV4.deploy("Curve CRV-ETH", "crvCRVETH", {"from": accounts[0]})


def _compiled_swap(token, coins, CurveCryptoSwap2ETH):
    path = CurveCryptoSwap2ETH._sources.get_source_path('CurveCryptoSwap2ETH')
    with open(path, 'r') as f:
        source = f.read()
        source = source.replace("0x0000000000000000000000000000000000000001", token.address)

        source = source.replace("0x0000000000000000000000000000000000000010", coins[0].address)
        source = source.replace("0x0000000000000000000000000000000000000011", coins[1].address)

        source = source.replace("1,#0", str(10 ** (18 - coins[0].decimals())) + ',')
        source = source.replace("1,#1", str(10 ** (18 - coins[1].decimals())) + ',')

    return compile_source(source, vyper_version=VYPER_VERSION).Vyper


@pytest.fixture(scope="module", autouse=True)
def compiled_swap(token, coins, CurveCryptoSwap2ETH):
    return _compiled_swap(token, coins, CurveCryptoSwap2ETH)


def _crypto_swap(compiled_swap, token, accounts):
    swap = compiled_swap.deploy(
            accounts[0],
            accounts[0],
            10 * 2**2 * 10000,  # A
            int(1.45e-4 * 1e18),  # gamma
            int(0.26e-2 * 1e10),  # mid_fee
            int(0.45e-2 * 1e10),  # out_fee
            10**10,  # allowed_extra_profit
            int(2.3e-4 * 1e18),  # fee_gamma
            int(1.46e-4 * 1e18),  # adjustment_step
            5 * 10**9,  # admin_fee
            600,  # ma_half_time
            INITIAL_PRICES[0],
            {'from': accounts[0]})
    token.set_minter(swap, {"from": accounts[0]})

    return swap


@pytest.fixture(scope="module", autouse=True)
def crypto_swap(compiled_swap, token, accounts):
    return _crypto_swap(compiled_swap, token, accounts)


def _crypto_swap_with_deposit(crypto_swap, coins, accounts):
    user = accounts[1]
    quantities = [10**6 * 10**36 // p for p in [10**18] + INITIAL_PRICES]  # $2M worth
    for coin, q in zip(coins, quantities):
        coin._mint_for_testing(user, q)
        coin.approve(crypto_swap, 2**256 - 1, {'from': user})

    # Very first deposit
    crypto_swap.add_liquidity(quantities, 0, {'from': user})

    return crypto_swap


@pytest.fixture(scope="module")
def swap(crypto_swap, coins, accounts):
    return _crypto_swap_with_deposit(crypto_swap, coins, accounts)
# End fixtures


@given(amount=strategy('uint256', min_value=10**6, max_value=10**18))
def test_exchange_eth_in(swap, amount, coins, accounts):
    user = accounts[1]

    assert coins[1].balanceOf(user) == 0
    b0 = swap.balances(0)
    swap.exchange(0, 1, amount, 0, True, {'value': amount, 'from': user})
    assert coins[1].balanceOf(user) > 0
    assert swap.balances(0) - b0 == amount

    b0 = swap.balances(0)
    b1 = swap.balances(1)
    old_balance = coins[1].balanceOf(user)
    swap.exchange_underlying(0, 1, amount, 0, {'value': amount, 'from': user})
    assert swap.balances(0) - b0  == amount
    assert b1 - swap.balances(1) > 0
    assert b1 - swap.balances(1) == coins[1].balanceOf(user) - old_balance


@given(amount=strategy('uint256', min_value=1000 * 10**6, max_value=1000 * 10**18))
def test_exchange_eth_out(swap, amount, coins, accounts):
    user = accounts[1]

    old_balance = accounts[1].balance()
    b0 = swap.balances(0)
    b1 = swap.balances(1)
    coins[1]._mint_for_testing(user, amount)
    swap.exchange(1, 0, amount, 0, True, {'from': user})
    assert accounts[1].balance() - old_balance > 0
    assert accounts[1].balance() - old_balance == b0 - swap.balances(0)
    assert swap.balances(1) - b1 == amount

    old_balance = accounts[1].balance()
    b0 = swap.balances(0)
    b1 = swap.balances(1)
    coins[1]._mint_for_testing(user, amount)
    swap.exchange_underlying(1, 0, amount, 0, {'from': user})
    assert accounts[1].balance() - old_balance > 0
    assert accounts[1].balance() - old_balance == b0 - swap.balances(0)
    assert swap.balances(1) - b1 == amount


@given(
        amount=strategy('uint256', min_value=1000 * 10**6, max_value=1000 * 10**18),
        i=strategy('int8', min_value=0, max_value=1))
def test_exchange_weth(swap, coins, accounts, amount, i):
    user = accounts[1]

    old_balance = accounts[1 - i].balance()
    b0 = swap.balances(i)
    b1 = swap.balances(1 - i)
    coins[i]._mint_for_testing(user, amount)
    swap.exchange(i, 1 - i, amount, 0, {'from': user})
    assert accounts[1 - i].balance() - old_balance > 0
    assert accounts[1 - i].balance() - old_balance == b1 - swap.balances(1 - i)
    assert swap.balances(i) - b0 == amount


def test_exchange_fail_eth():
    pass
