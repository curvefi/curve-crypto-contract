import pytest
from brownie.convert import to_bytes
from brownie_tokens import MintableForkToken


class PolygonChildERC20(MintableForkToken):
    @property
    def _depositor(self):
        return self.getRoleMember(self.DEPOSITOR_ROLE(), 0)

    def _mint_for_testing(self, target: str, amount, tx=None) -> None:
        self.deposit(target, to_bytes(amount), {"from": self._depositor})


@pytest.fixture(scope="session")
def DAI():
    return PolygonChildERC20("0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063")


@pytest.fixture(scope="session")
def USDC():
    return PolygonChildERC20("0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174")


@pytest.fixture(scope="session")
def USDT():
    return PolygonChildERC20("0xc2132D05D31c914a87C6611C10748AEb04B58e8F")


@pytest.fixture(scope="session")
def WBTC():
    return PolygonChildERC20("0x4F6649E445A7ccb6Ec4868a63418552027610A0b")


@pytest.fixture(scope="session")
def WETH():
    return PolygonChildERC20("0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619")


@pytest.fixture(scope="session")
def amDAI(Contract, interface):
    return Contract.from_abi(
        "AToken", "0x27F8D03b3a2196956ED754baDc28D73be8830A6e", interface.AToken.abi
    )


@pytest.fixture(scope="session")
def amUSDC(Contract, interface):
    return Contract.from_abi(
        "AToken", "0x1a13F4Ca1d028320A707D99520AbFefca3998b7F", interface.AToken.abi
    )


@pytest.fixture(scope="session")
def amUSDT(Contract, interface):
    return Contract.from_abi(
        "AToken", "0x60D55F02A771d515e077c9C2403a1ef324885CeC", interface.AToken.abi
    )


@pytest.fixture(scope="session")
def amWBTC(Contract, interface):
    return Contract.from_abi(
        "AToken", "0x5c2ed810328349100A66B82b78a1791B101C9D61", interface.AToken.abi
    )


@pytest.fixture(scope="session")
def amWETH(Contract, interface):
    return Contract.from_abi(
        "AToken", "0x28424507fefb6f7f8E9D3860F56504E4e5f5f390", interface.AToken.abi
    )


@pytest.fixture(scope="session")
def am3crv(Contract, interface):
    Contract.from_abi(
        "am3CRV",
        "0xE7a24EF0C5e95Ffb0f6684b813A78F2a3AD7D171",
        interface.CurveTokenV3.abi,
    )


@pytest.fixture(scope="session")
def am3crv_pool(Contract, interface):
    return Contract.from_abi(
        "am3CRVSwap",
        "0x445FE580eF8d70FF569aB36e80c647af338db351",
        interface.StableSwapAave.json,
    )


@pytest.fixture(scope="session")
def aave_lending_pool(Contract, interface):
    return Contract.from_abi(
        "AAVELendingPool",
        "0x8dFf5E27EA6b7AC08EbFdf9eB090F32ee9a30fcf",
        interface.AaveLendingPoolMock.abi,
    )


@pytest.fixture(scope="session")
def crypto_swap_matic(CurveCryptoSwapMatic):
    return CurveCryptoSwapMatic.at("0x4643A6600eae4851677A1f16d5e40Ef868c71717")


@pytest.fixture(scope="session")
def crypto_zap(ZapAave):
    return ZapAave.at("0x7e13d3b4845dB1508Cc5f311e067925e3CF77b64")


@pytest.fixture(scope="session")
def setup(alice, aave_lending_pool, DAI, USDC, USDT, WBTC, WETH):
    """Mint a bunch of test tokens"""
    amount = 1_000 * 10 ** 18

    for token in [DAI, USDC, USDT, WBTC, WETH]:
        token._mint_for_testing(amount, alice)
        aave_lending_pool.deposit(token, amount // 2, alice, 0, {"from": alice})
