import requests
from brownie import (
    accounts,
    CurveCryptoMath3,
    CurveTokenV4,
    CurveCryptoViews3,
    CurveCryptoSwap,
    ERC20Mock,
    compile_source,
)
from brownie import interface

COINS = [
    "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",  # USDC
    "0x1BFD67037B42Cf73acF2047067bd4F2C47D9BfD6",  # WBTC
    "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619"   # WETH
]


def main():
    p = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd").json()
    INITIAL_PRICES = [int(p[cur]['usd'] * 1e18) for cur in ['bitcoin', 'ethereum']]

    crypto_math = CurveCryptoMath3.deploy({"from": accounts[0]})
    token = CurveTokenV4.deploy("Curve.fi USD-BTC-ETH", "crvUSDBTCETH", {"from": accounts[0]})

    if COINS:
        coins = [interface.ERC20(addr) for addr in COINS]
    else:
        coins = [
            ERC20Mock.deploy(name, name, 18, {"from": accounts[0]}) for name in ["USD", "BTC", "ETH"]
        ]

    source = CurveCryptoViews3._build["source"]
    source = source.replace("1,#0", str(10 ** (18 - coins[0].decimals())) + ',')
    source = source.replace("1,#1", str(10 ** (18 - coins[1].decimals())) + ',')
    source = source.replace("1,#2", str(10 ** (18 - coins[2].decimals())) + ',')
    deployer = compile_source(source, vyper_version="0.2.12").Vyper
    crypto_views = deployer.deploy(crypto_math, {"from": accounts[0]})

    source = CurveCryptoSwap._build["source"]
    source = source.replace("0x0000000000000000000000000000000000000000", crypto_math.address)
    source = source.replace("0x0000000000000000000000000000000000000001", token.address)
    source = source.replace("0x0000000000000000000000000000000000000002", crypto_views.address)
    source = source.replace("0x0000000000000000000000000000000000000010", coins[0].address)
    source = source.replace("0x0000000000000000000000000000000000000011", coins[1].address)
    source = source.replace("0x0000000000000000000000000000000000000012", coins[2].address)
    source = source.replace("1,#0", str(10 ** (18 - coins[0].decimals())) + ',')
    source = source.replace("1,#1", str(10 ** (18 - coins[1].decimals())) + ',')
    source = source.replace("1,#2", str(10 ** (18 - coins[2].decimals())) + ',')
    deployer = compile_source(source, vyper_version="0.2.12").Vyper

    swap = deployer.deploy(
        accounts[0],
        135 * 3 ** 3,  # A
        int(7e-5 * 1e18),  # gamma
        int(4e-4 * 1e10),  # mid_fee
        int(4e-3 * 1e10),  # out_fee
        int(0.0028 * 1e18),  # price_threshold
        int(0.01 * 1e18),  # fee_gamma
        int(0.0015 * 1e18),  # adjustment_step
        0,  # admin_fee
        600,  # ma_half_time
        INITIAL_PRICES,
        {"from": accounts[0]},
    )
    token.set_minter(swap, {"from": accounts[0]})

    print("Deployed at:")
    print("Swap:", swap.address)
    print("Token:", token.address)

    return swap, token
