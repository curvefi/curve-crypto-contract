import requests
from brownie import (
    accounts,
    CurveTokenV4,
    CurveCryptoSwap2,
    ZapTwoArbiEurs,
    compile_source,
)
from brownie import interface
import json

# Addresses are taken for Arbitrum
COINS = [
    "0xD22a58f79e9481D1a88e00c343885A588b34b68B",  # EURS
    "0x7f90122BF0700F9E7e1F688fe926940E8839F353"   # 2Crv
]
SWAP = "0x7f90122BF0700F9E7e1F688fe926940E8839F353"
FEE_RECEIVER = "0x0000000000000000000000000000000000000000"


def main():
    accounts.load('babe')

    virtual_price = interface.StableSwap2Pool(SWAP).get_virtual_price()
    p = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=stasis-eurs&vs_currencies=usd").json()
    INITIAL_PRICE = int(virtual_price / p['stasis-eurs']['usd'])
    txparams = {"from": accounts[0], 'required_confs': 5, 'gasPrice': '2 gwei', 'gas': 200 * 10**6}
    print('Euro price:', 1e18 / INITIAL_PRICE, '2crv')

    token = CurveTokenV4.deploy("Curve EURS-2Crv", "crvEURSUSD", txparams)
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

    zap = ZapTwoArbiEurs.deploy(swap.address, SWAP, txparams)

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
