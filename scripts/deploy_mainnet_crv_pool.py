import requests
from brownie import (
    accounts,
    network,
    CurveTokenV4,
    CurveCryptoSwap2ETH,
    compile_source,
)
from brownie import interface
import json

VYPER_VERSION = "0.3.0"  # Forced version, use None when brownie supports the new version

# Addresses are taken for Polygon
COINS = [
    "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",  # WETH
    "0xD533a949740bb3306d119CC777fa900bA034cd52"   # CRV
]
FEE_RECEIVER = "0xeCb456EA5365865EbAb8a2661B0c503410e9B347"


def main():
    accounts.load('babe')

    p = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=curve-dao-token&vs_currencies=eth").json()
    INITIAL_PRICE = int(p['curve-dao-token']['eth'] * 1e18)
    txparams = {"from": accounts[0]}
    if network.show_active() == 'mainnet':
        txparams.update({'required_confs': 5, 'priority_fee': '2 gwei'})
    print('CRV price:', INITIAL_PRICE / 1e18, 'ETH')

    token = CurveTokenV4.deploy("Curve CRV-ETH", "crvCRVETH", txparams)
    coins = [interface.ERC20(addr) for addr in COINS]

    source = CurveCryptoSwap2ETH._build["source"]
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
