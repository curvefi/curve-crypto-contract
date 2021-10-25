import pytest
from brownie_tokens import MintableForkToken
# from brownie import interface


BASE_COINS = [
    "",  # DAI
    "",  # USDC
    ""   # USDT
]
COINS = [
    "",  # EUR
    ""   # 3crv*
]
BASE_SWAP = ""
SWAP = ""
TOKEN = ""


@pytest.fixture(scope="session")
def alice(accounts):
    return accounts[0]


@pytest.fixture(scope="session")
def bob(accounts):
    return accounts[1]


@pytest.fixture(scope="session")
def charlie(accounts):
    return accounts[2]


@pytest.fixture(scope="module")
def coins():
    return [MintableForkToken(addr) for addr in COINS]


@pytest.fixture(scope="module")
def base_coins():
    return [MintableForkToken(addr) for addr in BASE_COINS]


@pytest.fixture(scope="module")
def decimals():
    return [18, 18]


@pytest.fixture(scope="module")
def base_decimals():
    return [18, 6, 6]


@pytest.fixture(scope="module")
def crypto_swap(CurveCryptoSwap2):
    return CurveCryptoSwap2.at(SWAP)


@pytest.fixture(scope="module")
def crypto_zap(alice, ZapTwoArbi):
    return ZapTwoArbi.deploy(
        SWAP, BASE_SWAP, {"from": alice}
    )


@pytest.fixture(scope="module")
def crypto_lp_token(CurveTokenV4):
    return CurveTokenV4.at(TOKEN)


@pytest.fixture(scope="module", autouse=True)
def pre_mining(alice, crypto_zap, coins, decimals, base_coins, base_decimals):
    """Mint a bunch of test tokens"""
    for c, d in zip(base_coins, base_decimals):
        c._mint_for_testing(alice, 100_000 * 10**d)
        c.approve(crypto_zap, 2**256 - 1, {'from': alice})

    coins[0]._mint_for_testing(alice, 100_000 * 10**decimals[0])
    coins[0].approve(crypto_zap, 2**256 - 1, {'from': alice})
