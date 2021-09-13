import requests
from brownie import (
    accounts,
    CurveCryptoMath3,
    CurveTokenV4,
    CurveCryptoViews3,
    CurveCryptoSwap,
    DepositZapArbitrum,
    ERC20Mock,
    compile_source,
)
from brownie import interface, network
import json


COINS = [
    "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9",  # USDT
    "0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f",  # WBTC
    "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1"   # WETH
]
FEE_RECEIVER = "0x0000000000000000000000000000000000000000"

if network.show_active() == 'arbitrum':
    print('Deploying on mainnet')
    accounts.load('babe')
    txparams = {"from": accounts[0], 'required_confs': 5, 'gasPrice': '1 gwei', 'gas': 200 * 10**6}

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

    zap = DepositZapArbitrum.deploy(swap, txparams)

    print("Deployed at:")
    print("Swap:", swap.address)
    print("Token:", token.address)
    print("Math:", crypto_math.address)
    print("Views:", crypto_views.address)
    print("Zap:", zap.address)

    with open("swap.json", "w") as f:
        json.dump(swap.abi, f)

    with open("token.json", "w") as f:
        json.dump(token.abi, f)

    with open("zap.json", "w") as f:
        json.dump(zap.abi, f)

    return swap, token
