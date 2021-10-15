import requests
from brownie import (
    accounts,
    CurveCryptoMath3,
    CurveTokenV4,
    CurveCryptoViews3,
    CurveCryptoSwapHarmony,
    ZapHarmony,
    compile_source,
)
from brownie import interface
import json

COINS = [
    "0xC5cfaDA84E902aD92DD40194f0883ad49639b023",  # h3Crv
    "0x3095c7557bcb296ccc6e363de01b760ba031f2d9",  # hWBTC
    "0x6983d1e6def3690c4d616b13597a09e6193ea013"   # hWETH
]
SWAP = "0xC5cfaDA84E902aD92DD40194f0883ad49639b023"
FEE_RECEIVER = "0x00000000000000000000000000000000000000"


def main():
    accounts.load('babe')

    p = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd").json()
    INITIAL_PRICES = [int(p[cur]['usd'] * 1e18) for cur in ['bitcoin', 'ethereum']]
    txparams = {"from": accounts[0], 'required_confs': 5}

    crypto_math = CurveCryptoMath3.deploy(txparams)
    token = CurveTokenV4.deploy("Curve USD-BTC-ETH", "crvUSDBTCETH", txparams)

    coins = [interface.ERC20(addr) for addr in COINS]
    vprice = interface.Swap(SWAP).get_virtual_price()
    INITIAL_PRICES = [p * 10**18 // vprice for p in INITIAL_PRICES]

    source = CurveCryptoViews3._build["source"]
    source = source.replace("1,#0", str(10 ** (18 - coins[0].decimals())) + ',')
    source = source.replace("1,#1", str(10 ** (18 - coins[1].decimals())) + ',')
    source = source.replace("1,#2", str(10 ** (18 - coins[2].decimals())) + ',')
    with open("CryptoViews.vy", "w") as f:
        f.write(source)
    deployer = compile_source(source, vyper_version="0.2.15").Vyper
    crypto_views = deployer.deploy(crypto_math, txparams)

    source = CurveCryptoSwapHarmony._build["source"]
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
    deployer = compile_source(source, vyper_version="0.2.15").Vyper

    swap = deployer.deploy(
        accounts[0],
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

    zap = ZapHarmony.deploy(swap.address, SWAP, txparams)

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
