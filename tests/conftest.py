import pytest
from brownie import compile_source

INITIAL_PRICES = [47500 * 10**18, 1500 * 10**18]


@pytest.fixture(scope="module", autouse=True)
def crypto_math(CurveCryptoMath3, accounts):
    yield CurveCryptoMath3.deploy({'from': accounts[0]})


@pytest.fixture(scope="module", autouse=True)
def crypto_views(CurveCryptoViews3, crypto_math, accounts):
    yield CurveCryptoViews3.deploy(crypto_math, {'from': accounts[0]})


@pytest.fixture(scope="module", autouse=True)
def token(CurveTokenV4, accounts):
    yield CurveTokenV4.deploy("Curve USD-BTC-ETH", "crvUSDBTCETH", {"from": accounts[0]})


@pytest.fixture(scope="module", autouse=True)
def coins(ERC20Mock, accounts):
    yield [ERC20Mock.deploy(name, name, 18, {"from": accounts[0]})
           for name in ['USD', 'BTC', 'ETH']]


@pytest.fixture(scope="module", autouse=True)
def compiled_swap(crypto_math, token, crypto_views, coins):
    from brownie import CurveCryptoSwap
    path = CurveCryptoSwap._sources.get_source_path('CurveCryptoSwap')
    with open(path, 'r') as f:
        source = f.read()
        source = source.replace("0x0000000000000000000000000000000000000000", crypto_math.address)
        source = source.replace("0x0000000000000000000000000000000000000001", token.address)
        source = source.replace("0x0000000000000000000000000000000000000002", crypto_views.address)
        source = source.replace("0x0000000000000000000000000000000000000010", coins[0].address)
        source = source.replace("0x0000000000000000000000000000000000000011", coins[1].address)
        source = source.replace("0x0000000000000000000000000000000000000012", coins[2].address)
    return compile_source(source, vyper_version='0.2.12').Vyper


@pytest.fixture(scope="module", autouse=True)
def crypto_swap(compiled_swap, token, accounts):
    swap = compiled_swap.deploy(
            accounts[0],
            135 * 3**3,  # A
            int(7e-5 * 1e18),  # gamma
            int(4e-4 * 1e10),  # mid_fee
            int(4e-3 * 1e10),  # out_fee
            int(0.0028 * 1e18),  # price_threshold
            int(0.01 * 1e18),  # fee_gamma
            int(0.0015 * 1e18),  # adjustment_step
            0,  # admin_fee
            600,  # ma_half_time
            INITIAL_PRICES,
            {'from': accounts[0]})
    token.set_minter(swap, {"from": accounts[0]})

    return swap


@pytest.fixture(scope="module")
def crypto_swap_with_deposit(crypto_swap, coins, accounts):
    user = accounts[1]
    quantities = [10**6 * 10**36 // p for p in [10**18] + INITIAL_PRICES]  # $3M worth
    for coin, q in zip(coins, quantities):
        coin._mint_for_testing(user, q)
        coin.approve(crypto_swap, 2**256-1, {'from': user})

    # Very first deposit
    crypto_swap.add_liquidity(quantities, 0, {'from': user})

    return crypto_swap


@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass
