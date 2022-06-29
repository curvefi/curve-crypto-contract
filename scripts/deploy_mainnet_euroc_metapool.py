import requests
from brownie import (
    accounts,
    CurveTokenV5,
    CurveCryptoSwap2,
    ZapTwo
)
from brownie import interface
import json

COINS = [
    "0x1aBaEA1f7C830bD89Acc67eC4af516284b1bC33c",  # EUROC
    "0x6c3F90f043a72FA612cbac8115EE7e52BDe6E490"   # 3crv
]
STABLESWAP = "0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7"
FEE_RECEIVER = "0xeCb456EA5365865EbAb8a2661B0c503410e9B347"


def main():
    accounts.load('babe')

    virtual_price = interface.StableSwap3Pool(STABLESWAP).get_virtual_price()
    p = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=tether-eurt&vs_currencies=usd").json()
    INITIAL_PRICE = int(virtual_price / p['tether-eurt']['usd'])
    txparams = {"from": accounts[0]}
    # txparams = {"from": accounts[0], 'required_confs': 5, 'priority_fee': '2 gwei'}
    print('EUR price:', 1e18 / INITIAL_PRICE, '3crv')

    token = CurveTokenV5.deploy("Curve EUROC-3Crv", "EUROC3CRV", txparams)

    swap = CurveCryptoSwap2.deploy(
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
        1200,  # ma_half_time
        INITIAL_PRICE,  # price
        token,
        COINS,
        txparams
    )
    token.set_minter(swap, txparams)

    zap = ZapTwo.deploy(swap, STABLESWAP, txparams)

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
