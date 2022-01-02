import requests
from brownie import (
    accounts,
    network,
    CurveTokenV5,
    CurveCryptoSwap2ETH,
)

# Addresses are taken for Polygon
COINS = [
    "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",  # WETH
    "0xCdF7028ceAB81fA0C6971208e83fa7872994beE5"   # T
]
FEE_RECEIVER = "0xeCb456EA5365865EbAb8a2661B0c503410e9B347"


def main():
    accounts.load('babe')

    p_nu = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=nucypher&vs_currencies=eth").json()
    p_nu = p_nu['nucypher']['eth'] * 1e18
    p_keep = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=keep-network&vs_currencies=eth").json()
    p_keep = p_keep['keep-network']['eth'] * 1e18
    INITIAL_PRICE = int((p_nu * p_keep) ** 0.5)  # Geometric mean
    txparams = {"from": accounts[0]}
    if network.show_active() == 'mainnet':
        txparams.update({'required_confs': 5, 'priority_fee': '2 gwei'})
    print('CVX price:', INITIAL_PRICE / 1e18, 'ETH')

    token = CurveTokenV5.deploy("Curve T-ETH", "crvTETH", txparams)

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
