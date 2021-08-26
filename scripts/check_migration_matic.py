from brownie import accounts
from brownie import PoolMigratorMatic23 as PoolMigratorMatic
from brownie import Contract


OLD_TOKEN = "0xbece5d20A8a104c54183CC316C8286E3F00ffC71"
OLD_GAUGE = "0x9bd996Db02b3f271c6533235D452a56bc2Cd195a"

NEW_TOKEN = "0xdAD97F7713Ae9437fa9249920eC8507e5FbB23d3"
NEW_GAUGE = "0x3B6B158A76fd8ccc297538F454ce7B4787778c7C"


def main():
    accounts.load('babe')
    FROM = DEPLOYER = accounts[0]

    migrator = PoolMigratorMatic.deploy({'from': DEPLOYER})

    old_gauge_token = Contract.from_explorer(OLD_GAUGE)
    old_lp_token = Contract.from_explorer(OLD_TOKEN)
    new_gauge_token = Contract.from_explorer(NEW_GAUGE)
    new_lp_token = Contract.from_explorer(NEW_TOKEN)

    print('Old Gauge:', old_gauge_token.balanceOf(FROM)/1e18)
    print('Old LP:', old_lp_token.balanceOf(FROM)/1e18)
    print('New Gauge:', new_gauge_token.balanceOf(FROM)/1e18)
    print('New LP:', new_lp_token.balanceOf(FROM)/1e18)

    old_gauge_token.approve(migrator, 2**256-1, {'from': FROM})
    old_lp_token.approve(migrator, 2**256-1, {'from': FROM})

    migrator.migrate_to_new_pool({'from': FROM})

    print('Old Gauge:', old_gauge_token.balanceOf(FROM)/1e18)
    print('Old LP:', old_lp_token.balanceOf(FROM)/1e18)
    print('New Gauge:', new_gauge_token.balanceOf(FROM)/1e18)
    print('New LP:', new_lp_token.balanceOf(FROM)/1e18)

    print('Migrator:', migrator.address)
