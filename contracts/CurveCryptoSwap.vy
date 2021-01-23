# @version 0.2.8
# (c) Curve.Fi, 2020
# Pool for 3Crv(USD)/BTC/ETH or similar
from vyper.interfaces import ERC20

interface CurveToken:
    def totalSupply() -> uint256: view
    def mint(_to: address, _value: uint256) -> bool: nonpayable
    def burnFrom(_to: address, _value: uint256) -> bool: nonpayable


N_COINS: constant(int128) = 3  # <- change
PRECISION_MUL: constant(uint256[N_COINS]) = [1, 1, 1]  # 3usd, renpool, eth
FEE_DENOMINATOR: constant(uint256) = 10 ** 10
PRECISION: constant(uint256) = 10 ** 18  # The precision to convert to
A_MULTIPLIER: constant(uint256) = 100

price_scale: public(uint256[N_COINS])
price_oracle: public(uint256[N_COINS])  # Given by MA

A_precise: public(uint256)
gamma: public(uint256)
mid_fee: public(uint256)
out_fee: public(uint256)
price_threshold: public(uint256)
fee_gamma: public(uint256)
adjustment_step: public(uint256)
# MA parameters are needed, too

balances: public(uint256[N_COINS])
coins: public(address[N_COINS])
# XXX should we store the invariant?

token: public(address)
owner: public(address)

admin_fee: public(uint256)
# XXX admin fee charging requires work


@external
def __init__(
    owner: address,
    coins: address[N_COINS],
    pool_token: address,
    A: uint256,
    gamma: uint256,
    mid_fee: uint256,
    out_fee: uint256,
    price_threshold: uint256,
    fee_gamma: uint256,
    adjustment_step: uint256,
    admin_fee: uint256,
    initial_prices: uint256[N_COINS]
):
    self.owner = owner
    self.coins = coins
    self.token = pool_token
    self.A_precise = A * A_MULTIPLIER
    self.gamma = gamma
    self.mid_fee = mid_fee
    self.out_fee = out_fee
    self.price_threshold = price_threshold
    self.fee_gamma = fee_gamma
    self.adjustment_step = adjustment_step
    self.admin_fee = admin_fee
    self.price_scale = initial_prices
    self.price_oracle = initial_prices
