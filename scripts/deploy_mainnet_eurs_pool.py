import requests
from brownie import (
    accounts,
    CurveTokenV4,
    CurveCryptoSwap2,
    compile_source,
)
from brownie import interface
import json

VYPER_VERSION = "0.3.0"  # Forced version, use None when brownie supports the new version

# Addresses are taken for Polygon
COINS = [
    "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",  # USDC
    "0xdB25f211AB05b1c97D595516F45794528a807ad8"   # EURS
]
FEE_RECEIVER = "0xeCb456EA5365865EbAb8a2661B0c503410e9B347"


def main():
    accounts.load('babe')

    p = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=stasis-eurs&vs_currencies=usd").json()
    INITIAL_PRICE = int(p['stasis-eurs']['usd'] * 1e18)
    txparams = {"from": accounts[0], 'required_confs': 5, 'priority_fee': '2 gwei'}
    print('Euro price:', INITIAL_PRICE / 1e18, 'USDC')

    token = CurveTokenV4.deploy("Curve EURS-USDC", "crvEURSUSDC", txparams)
    coins = [interface.ERC20(addr) for addr in COINS]

    source = CurveCryptoSwap2._build["source"]
    source = source.replace("0x0000000000000000000000000000000000000001", token.address)
    source = source.replace("0x0000000000000000000000000000000000000010", coins[0].address)
    source = source.replace("0x0000000000000000000000000000000000000011", coins[1].address)
    source = source.replace("1,#0", str(10 ** (18 - coins[0].decimals())) + ',')
    source = source.replace("1,#1", str(10 ** (18 - coins[1].decimals())) + ',')
    with open("CryptoSwap.vy", "w") as f:
        f.write(source)
    deployer = compile_source(source, vyper_version=VYPER_VERSION).Vyper

    swap = deployer.deploy(
        accounts[0],
        FEE_RECEIVER,
        5000 * 2**2 * 10000,  # A
        int(1e-4 * 1e18),  # gamma
        int(5e-4 * 1e10),  # mid_fee
        int(45e-4 * 1e10),  # out_fee
        10**10,  # allowed_extra_profit
        int(5e-3 * 1e18),  # fee_gamma
        int(0.55e-5 * 1e18),  # adjustment_step ?
        5 * 10**9,  # admin_fee
        600,  # ma_half_time
        INITIAL_PRICE,  # price
        txparams
    )
    token.set_minter(swap, txparams)

    print("Swap address:", swap.address)
    print("Token address:", token.address)

    with open("swap.json", "w") as f:
        json.dump(swap.abi, f)

    with open("token.json", "w") as f:
        json.dump(token.abi, f)

    return swap, token
