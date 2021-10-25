import pytest
from brownie import compile_source

VYPER_VERSION = "0.3.0"  # Forced version, use None when brownie supports the new version
INITIAL_PRICES = [int(0.8 * 10**18)]  # 1/eur


@pytest.fixture(scope="module", autouse=True)
def coins(ERC20Mock, accounts):
    yield [ERC20Mock.deploy(name, name, 18, {"from": accounts[0]})
           for name in ['USD', 'EUR']]


@pytest.fixture(scope="module", autouse=True)
def token(CurveTokenV4, accounts):
    yield CurveTokenV4.deploy("Curve EUR-USD", "crvEURUSD", {"from": accounts[0]})


def _compiled_swap(token, coins, CurveCryptoSwap2):
    path = CurveCryptoSwap2._sources.get_source_path('CurveCryptoSwap2')
    with open(path, 'r') as f:
        source = f.read()
        source = source.replace("0x0000000000000000000000000000000000000001", token.address)

        source = source.replace("0x0000000000000000000000000000000000000010", coins[0].address)
        source = source.replace("0x0000000000000000000000000000000000000011", coins[1].address)

        source = source.replace("1,#0", str(10 ** (18 - coins[0].decimals())) + ',')
        source = source.replace("1,#1", str(10 ** (18 - coins[1].decimals())) + ',')

    return compile_source(source, vyper_version=VYPER_VERSION).Vyper


@pytest.fixture(scope="module", autouse=True)
def compiled_swap(token, coins, CurveCryptoSwap2):
    return _compiled_swap(token, coins, CurveCryptoSwap2)


def _crypto_swap(compiled_swap, token, accounts):
    swap = compiled_swap.deploy(
            accounts[0],
            accounts[0],
            90 * 2**2 * 10000,  # A
            int(2.8e-4 * 1e18),  # gamma
            int(8.5e-5 * 1e10),  # mid_fee
            int(1.3e-3 * 1e10),  # out_fee
            10**10,  # allowed_extra_profit
            int(0.012 * 1e18),  # fee_gamma
            int(0.55e-5 * 1e18),  # adjustment_step
            0,  # admin_fee
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
    quantities = [10**6 * 10**36 // p for p in [10**18] + INITIAL_PRICES]  # $3M worth
    for coin, q in zip(coins, quantities):
        coin._mint_for_testing(user, q)
        coin.approve(crypto_swap, 2**256-1, {'from': user})

    # Very first deposit
    crypto_swap.add_liquidity(quantities, 0, {'from': user})

    return crypto_swap


@pytest.fixture(scope="module")
def crypto_swap_with_deposit(crypto_swap, coins, accounts):
    return _crypto_swap_with_deposit(crypto_swap, coins, accounts)


@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass
