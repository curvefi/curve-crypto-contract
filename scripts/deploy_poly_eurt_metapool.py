import requests
from brownie import (
    accounts,
    CurveTokenV4,
    CurveCryptoSwap2,
    ZapTwoAave,
    compile_source,
)
from brownie import interface
import json

# Addresses are taken for Polygon
COINS = [
    "0x7BDF330f423Ea880FF95fC41A280fD5eCFD3D09f",  # EURT
    "0xE7a24EF0C5e95Ffb0f6684b813A78F2a3AD7D171"   # 3Crv
]
SWAP = "0x445FE580eF8d70FF569aB36e80c647af338db351"
FEE_RECEIVER = "0x0000000000000000000000000000000000000000"


def main():
    accounts.load('babe')

    virtual_price = interface.StableSwap2Pool(SWAP).get_virtual_price()
    p = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=tether-eurt&vs_currencies=usd").json()
    INITIAL_PRICE = int(virtual_price / p['tether-eurt']['usd'])
    txparams = {"from": accounts[0], 'required_confs': 20, 'gasPrice': '30 gwei'}
    print('Euro price:', 1e18 / INITIAL_PRICE, '3crv')

    token = CurveTokenV4.deploy("Curve EURT-3Crv", "crvEURTUSD", txparams)
    coins = [interface.ERC20(addr) for addr in COINS]

    source = CurveCryptoSwap2._build["source"]
    source = source.replace("0x0000000000000000000000000000000000000001", token.address)
    source = source.replace("0x0000000000000000000000000000000000000010", coins[0].address)
    source = source.replace("0x0000000000000000000000000000000000000011", coins[1].address)
    source = source.replace("1,#0", str(10 ** (18 - coins[0].decimals())) + ',')
    source = source.replace("1,#1", str(10 ** (18 - coins[1].decimals())) + ',')
    with open("CryptoSwap.vy", "w") as f:
        f.write(source)
    deployer = compile_source(source, vyper_version="0.3.0").Vyper

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

    zap = ZapTwoAave.deploy(swap.address, SWAP, txparams)

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
