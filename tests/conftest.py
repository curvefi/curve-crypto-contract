import pytest
from brownie import compile_source


@pytest.fixture(scope="module")
def crypto_math(CurveCryptoMath3, accounts):
    yield CurveCryptoMath3.deploy({'from': accounts[0]})


@pytest.fixture(scope="module")
def token(CurveTokenV4, accounts):
    yield CurveTokenV4.deploy("Curve USD-BTC-ETH", "crvUSDBTCETH", {"from": accounts[0]})


@pytest.fixture(scope="module")
def coins(ERC20Mock, accounts):
    yield [ERC20Mock.deploy(name, name, 18, {"from": accounts[0]})
           for name in ['USD', 'BTC', 'ETH']]


@pytest.fixture(scope="module")
def crypto_swap(crypto_math, token, coins, accounts):
    from brownie import CurveCryptoSwap
    path = CurveCryptoSwap._sources.get_source_path('CurveCryptoSwap')
    with open(path, 'r') as f:
        source = f.read()
        source = source.replace("0x0000000000000000000000000000000000000000", crypto_math.address)
    contract = compile_source(source, vyper_version='0.2.11').Vyper  # XXX remove version once brownie supports new Vyper

    return contract.deploy(
            accounts[0],
            coins,
            token,
            135,  # A
            int(7e-5 * 1e18),  # gamma
            int(4e-4 * 1e10),  # mid_fee
            int(4e-3 * 1e10),  # out_fee
            int(0.0028 * 1e18),  # price_threshold
            int(0.01 * 1e18),  # fee_gamma
            int(0.0015 * 1e18),  # adjustment_step
            0,  # admin_fee
            600,  # ma_half_time
            [47500 * 10**18, 1500 * 10**18],  # initial_prices
            {'from': accounts[0]})
