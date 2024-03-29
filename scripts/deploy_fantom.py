import requests
from brownie import (
    accounts,
    CurveCryptoMath3,
    CurveTokenV4,
    CurveCryptoViews3,
    CurveCryptoSwapC,
    ERC20Mock,
    compile_source,
)
from brownie import interface, network
import json


COINS = [
    "0x049d68029688eAbF473097a2fC38ef61633A3C7A",  # fUSDT
    "0x321162Cd933E2Be498Cd2267a90534A804051b11",  # WBTC
    "0x74b23882a30290451A17c44f4F05243b6b58C76d"   # WETH
]
FEE_RECEIVER = "0x0000000000000000000000000000000000000000"

if network.show_active() == 'ftm-main':
    print('Deploying on mainnet')
    accounts.load('babe')
    txparams = {"from": accounts[0], 'required_confs': 5}

else:
    txparams = {"from": accounts[0]}


def main():
    p = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd").json()
    INITIAL_PRICES = [int(p[cur]['usd'] * 1e18) for cur in ['bitcoin', 'ethereum']]

    crypto_math = CurveCryptoMath3.deploy(txparams)
    token = CurveTokenV4.deploy("Curve.fi USD-BTC-ETH", "crv3crypto", txparams)

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
    with open("CryptoViews.vy", "w") as f:
        f.write(source)
    deployer = compile_source(source, vyper_version="0.2.15").Vyper
    crypto_views = deployer.deploy(crypto_math, txparams)

    source = CurveCryptoSwapC._build["source"]
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
        int(2 * 3 ** 3 * 10000),  # A
        int(2.1e-5 * 1e18),  # gamma
        int(1.1e-3 * 1e10),  # mid_fee
        int(4.5e-3 * 1e10),  # out_fee
        2 * 10**12,  # allowed_extra_profit
        int(5e-4 * 1e18),  # fee_gamma
        int(0.00049 * 1e18),  # adjustment_step
        5 * 10**9,  # admin_fee
        600,  # ma_half_time
        INITIAL_PRICES,
        txparams,
    )
    token.set_minter(swap, txparams)

    print("Deployed at:")
    print("Swap:", swap.address)
    print("Token:", token.address)
    print("Math:", crypto_math.address)
    print("Views:", crypto_views.address)

    with open("swap.json", "w") as f:
        json.dump(swap.abi, f)

    with open("token.json", "w") as f:
        json.dump(token.abi, f)

    return swap, token
