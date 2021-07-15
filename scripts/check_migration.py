from brownie import network
from brownie import PoolMigrator
from brownie import Contract


FROM = "0x7a16fF8270133F063aAb6C9977183D9e72835428"
DEPLOYER = "0xbabe61887f1de2713c6f97e567623453d3C79f67"

OLD_TOKEN = "0xcA3d75aC011BF5aD07a98d02f18225F9bD9A6BDF"
OLD_GAUGE = "0x6955a55416a06839309018A8B0cB72c4DDC11f15"

NEW_TOKEN = "0xc4AD29ba4B3c580e6D59105FFf484999997675Ff"
NEW_GAUGE = "0xDeFd8FdD20e0f34115C7018CCfb655796F6B2168"


def main():
    assert network.show_active() != 'mainnet'

    migrator = PoolMigrator.deploy({'from': DEPLOYER})

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
