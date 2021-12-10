import pytest
from brownie import interface
from brownie_tokens import MintableForkToken

VYPER_VERSION = "0.3.1"  # Forced version, use None when brownie supports the new version


BASE_COINS = [
    "0x6B175474E89094C44Da98b954EedeAC495271d0F",  # DAI
    "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",  # USDC
    "0xdAC17F958D2ee523a2206206994597C13D831ec7"   # USDT
]
COINS = [
    "0xC581b735A1688071A1746c968e0798D642EDE491",  # EUR
    "0xFd2a8fA60Abd58Efe3EeE34dd494cD491dC14900"   # a3crv*
]
BASE_SWAP = "0xDeBF20617708857ebe4F679508E7b7863a8A8EeE"


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
def underlying_coins(coins, base_coins):
    return [coins[0]] + base_coins


@pytest.fixture(scope="module")
def decimals():
    return [6, 18]


@pytest.fixture(scope="module")
def base_decimals():
    return [18, 6, 6]


@pytest.fixture(scope="module", autouse=True)
def crypto_swap(CurveCryptoSwap2, token, coins, alice):
    swap = CurveCryptoSwap2.deploy(
            alice,
            alice,
            90 * 2**2 * 10000,  # A
            int(2.8e-4 * 1e18),  # gamma
            int(8.5e-5 * 1e10),  # mid_fee
            int(1.3e-3 * 1e10),  # out_fee
            10**10,  # allowed_extra_profit
            int(0.012 * 1e18),  # fee_gamma
            int(0.55e-5 * 1e18),  # adjustment_step
            0,  # admin_fee
            600,  # ma_half_time
            int(0.8 * 1e18),  # price
            token,
            coins,
            {'from': alice})
    token.set_minter(swap, {"from": alice})

    return swap


@pytest.fixture(scope="module", autouse=True)
def stable_swap():
    return interface.StableSwap3Pool(BASE_SWAP)


@pytest.fixture(scope="module")
def crypto_zap(alice, ZapTwoAave, crypto_swap):
    return ZapTwoAave.deploy(
        crypto_swap, BASE_SWAP, {"from": alice}
    )


@pytest.fixture(scope="module", autouse=True)
def pre_mining(alice, crypto_zap, crypto_swap, coins, decimals, base_coins, base_decimals, charlie):
    """Mint a bunch of test tokens"""
    for c, d in zip(base_coins, base_decimals):
        c._mint_for_testing(alice, 100_000 * 10**d)
        c.approve(crypto_zap, 2**256 - 1, {'from': alice})
        c._mint_for_testing(charlie, 100_000 * 10**d)
        c.approve(crypto_zap, 2**256 - 1, {'from': charlie})

    coins[0]._mint_for_testing(alice, 300_000 * 10**decimals[0])
    coins[0].approve(crypto_zap, 2**256 - 1, {'from': alice})

    coins[0]._mint_for_testing(charlie, 300_000 * 10**decimals[0])
    coins[0].approve(crypto_zap, 2**256 - 1, {'from': charlie})

    crypto_zap.add_liquidity([
        240000 * 10**6, 100000 * 10**18, 100000 * 10**6, 100000 * 10**6
    ], 0, {'from': charlie})
