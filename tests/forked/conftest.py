from functools import cached_property

import pytest
from brownie.convert import to_bytes
from brownie_tokens import MintableForkToken


class PolygonChildERC20(MintableForkToken):
    @cached_property
    def _depositor(self):
        return self.getRoleMember(self.DEPOSITOR_ROLE(), 0)

    def _mint_for_testing(self, target: str, amount, tx=None) -> None:
        self.deposit(target, to_bytes(amount), {"from": self._depositor})


@pytest.fixture(scope="module")
def DAI(interface):
    return PolygonChildERC20.from_abi(
        "Token", "0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063", interface.UChildERC20.abi
    )


@pytest.fixture(scope="module")
def USDC(interface):
    return PolygonChildERC20.from_abi(
        "Token", "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174", interface.UChildERC20.abi
    )


@pytest.fixture(scope="module")
def USDT(interface):
    return PolygonChildERC20.from_abi(
        "Token", "0xc2132D05D31c914a87C6611C10748AEb04B58e8F", interface.UChildERC20.abi
    )


@pytest.fixture(scope="module")
def WBTC(interface):
    return PolygonChildERC20.from_abi(
        "Token", "0x1BFD67037B42Cf73acF2047067bd4F2C47D9BfD6", interface.UChildERC20.abi
    )


@pytest.fixture(scope="module")
def WETH(interface):
    return PolygonChildERC20.from_abi(
        "Token", "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619", interface.UChildERC20.abi
    )


@pytest.fixture(scope="module")
def crypto_zap(ZapAave):
    return ZapAave.at("0x7e13d3b4845dB1508Cc5f311e067925e3CF77b64")


@pytest.fixture(scope="module")
def crypto_lp_token(CurveTokenV4):
    return CurveTokenV4.at("0x939986418baFb4E2d82A76E320767Ff02d250203")


@pytest.fixture(scope="module")
def underlying_coins(DAI, USDC, USDT, WBTC, WETH):
    return [DAI, USDC, USDT, WBTC, WETH]


@pytest.fixture(scope="module")
def decimals(underlying_coins):
    return [coin.decimals() for coin in underlying_coins]


@pytest.fixture(scope="module", autouse=True)
def setup(alice, crypto_zap, underlying_coins, decimals):
    """Mint a bunch of test tokens"""
    amount = 1_000

    for coin, decimal in zip(underlying_coins, decimals):
        coin._mint_for_testing(alice, amount * 10 ** decimal)
        coin.approve(crypto_zap, 2 ** 256 - 1, {"from": alice})


@pytest.fixture(scope="module")
def deposit_amounts(decimals):
    amounts = [500, 500, 500, 0.01, 0.1]
    return [amount * 10 ** decimals[i] for i, amount in enumerate(amounts)]
