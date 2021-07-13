import requests
from brownie.network.gas.strategies import GasNowScalingStrategy
from brownie import (
    accounts,
    CurveCryptoMath3,
    CurveTokenV4,
    CurveCryptoViews3,
    CurveCryptoSwap,
    ERC20Mock,
    compile_source,
)
from brownie import interface, network
import json


COINS = [
    "0xdAC17F958D2ee523a2206206994597C13D831ec7",  # USDT
    "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",  # WBTC
    "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"   # WETH
]
FEE_RECEIVER = "0xeCb456EA5365865EbAb8a2661B0c503410e9B347"

if network.show_active() == 'mainnet':
    print('Deploying on mainnet')
    accounts.load('babe')
    txparams = {"from": accounts[0], 'required_confs': 5}
    try:
        network.gas_price(GasNowScalingStrategy("slow", "fast"))
    except ConnectionError:
        pass

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
    deployer = compile_source(source, vyper_version="0.2.12").Vyper
    crypto_views = deployer.deploy(crypto_math, txparams)

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
        FEE_RECEIVER,
        int(0.2 * 3 ** 3 * 10000),  # A
        int(3.5e-3 * 1e18),  # gamma
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
