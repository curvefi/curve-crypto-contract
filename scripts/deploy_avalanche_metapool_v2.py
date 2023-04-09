import requests
from brownie import (
    accounts,
    CurveCryptoMath3,
    CurveTokenV4,
    CurveCryptoViews3,
    CurveCryptoSwapAvalancheV2,
    ERC20Mock,
    ZapAvalanche,
    compile_source,
)
from brownie import interface
import json

# Addresses are taken for Avalanche
COINS = [
    "0x0974D9d3bc463Fa17497aAFc3a87535553298FbE",  # 2CRV
    "0x152b9d0FdC40C096757F570A51E494bd4b943E50",  # BTC.b
    "0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7"   # wAVAX
]
SWAP = "0x0974D9d3bc463Fa17497aAFc3a87535553298FbE"
FEE_RECEIVER = "0x06534b0BF7Ff378F162d4F348390BDA53b15fA35"


def main():
    accounts.load('dev')

    p = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin-avalanche-bridged-btc-b,avalanche-2&vs_currencies=usd").json()
    INITIAL_PRICES = [int(p[cur]['usd'] * 1e18) for cur in ['bitcoin-avalanche-bridged-btc-b', 'avalanche-2']]
    txparams = {"from": accounts[0], 'required_confs': 5}

    crypto_math = CurveCryptoMath3.deploy(txparams)
    token = CurveTokenV4.deploy("Curve USD-BTC-AVAX", "crvUSDBTCAVAX", txparams)

    if COINS:
        coins = [interface.ERC20(addr) for addr in COINS]
        vprice = interface.Swap(SWAP).get_virtual_price()
        INITIAL_PRICES = [p * 10**18 // vprice for p in INITIAL_PRICES]
    else:
        coins = [
            ERC20Mock.deploy(name, name, 18, txparams) for name in ["USD", "BTC", "AVAX"]
        ]

    source = CurveCryptoViews3._build["source"]
    source = source.replace("1,#0", str(10 ** (18 - coins[0].decimals())) + ',')
    source = source.replace("1,#1", str(10 ** (18 - coins[1].decimals())) + ',')
    source = source.replace("1,#2", str(10 ** (18 - coins[2].decimals())) + ',')
    with open("CryptoViews.vy", "w") as f:
        f.write(source)
    deployer = compile_source(source, vyper_version="0.3.1").Vyper
    crypto_views = deployer.deploy(crypto_math, txparams)

    source = CurveCryptoSwapAvalancheV2._build["source"]
    source = source.replace("0x0000000000000000000000000000000000000000", crypto_math.address)
    source = source.replace("0x0000000000000000000000000000000000000001", token.address)
    source = source.replace("0x0000000000000000000000000000000000000002", crypto_views.address)
    source = source.replace("0x0000000000000000000000000000000000000010", coins[0].address)
    source = source.replace("0x0000000000000000000000000000000000000011", coins[1].address)
    source = source.replace("0x0000000000000000000000000000000000000012", coins[2].address)
    source = source.replace("1,#0", str(10 ** (18 - coins[0].decimals())) + ',')
    source = source.replace("1,#1", str(10 ** (18 - coins[1].decimals())) + ',')
    source = source.replace("1,#2", str(10 ** (18 - coins[2].decimals())) + ',')
    with open("CryptoSwap.vy", "w") as f:
        f.write(source)
    deployer = compile_source(source, vyper_version="0.3.7").Vyper

    swap = deployer.deploy(
        "0xB055EbbAcc8Eefc166c169e9Ce2886D0406aB49b",  # avax admin
        FEE_RECEIVER,
        int(6.32 * 3 ** 3 * 10000),  # A
        int(1.18e-5 * 1e18),  # gamma
        int(0.5e-3 * 1e10),  # mid_fee
        int(3e-3 * 1e10),  # out_fee
        2 * 10**12,  # allowed_extra_profit
        int(5e-4 * 1e18),  # fee_gamma
        int(0.001 * 1e18),  # adjustment_step
        5 * 10**9,  # admin_fee
        600,  # ma_half_time
        INITIAL_PRICES,
        txparams,
    )
    token.set_minter(swap, txparams)

    zap = ZapAvalanche.deploy(swap.address, SWAP, txparams)

    print("Math address:", crypto_math.address)
    print("Views address:", crypto_views.address)

    print("Swap address:", swap.address)
    print("Token address:", token.address)
    print("Zap address:", zap.address)

    with open("swap.json", "w") as f:
        json.dump(swap.abi, f)

    with open("token.json", "w") as f:
        json.dump(token.abi, f)

    with open("zap.json", "w") as f:
        json.dump(zap.abi, f)

    return swap, token, zap
