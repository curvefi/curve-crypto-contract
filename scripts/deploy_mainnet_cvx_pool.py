import requests
from brownie import (
    accounts,
    network,
    CurveTokenV4,
    CurveCryptoSwap2ETH,
)

# Addresses are taken for Polygon
COINS = [
    "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",  # WETH
    "0x4e3FBD56CD56c3e72c1403e103b45Db9da5B9D2B"   # CVX
]
FEE_RECEIVER = "0xeCb456EA5365865EbAb8a2661B0c503410e9B347"


def main():
    accounts.load('babe')

    p = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=convex-finance&vs_currencies=eth").json()
    INITIAL_PRICE = int(p['convex-finance']['eth'] * 1e18)
    txparams = {"from": accounts[0]}
    if network.show_active() == 'mainnet':
        txparams.update({'required_confs': 5, 'priority_fee': '2 gwei'})
    print('CVX price:', INITIAL_PRICE / 1e18, 'ETH')

    token = CurveTokenV4.deploy("Curve CVX-ETH", "crvCVXETH", txparams)

    swap = CurveCryptoSwap2ETH.deploy(
        accounts[0],
        FEE_RECEIVER,
        10 * 2**2 * 10000,  # A
        int(1.45e-4 * 1e18),  # gamma
        int(2.6e-3 * 1e10),  # mid_fee
        int(4.5e-3 * 1e10),  # out_fee
        2 * 10**12,  # allowed_extra_profit - same as tricrypto2
        int(2.3e-4 * 1e18),  # fee_gamma
        int(1.46e-4 * 1e18),  # adjustment_step
        5 * 10**9,  # admin_fee
        600,  # ma_half_time
        INITIAL_PRICE,  # price
        token,
        COINS,
        txparams
    )
    token.set_minter(swap, txparams)

    print("Swap address:", swap.address)
    print("Token address:", token.address)

    return swap, token
