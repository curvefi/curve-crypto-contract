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
    new_initial_prices: uint256[N_COINS] = initial_prices
    precisions: uint256[N_COINS] = PRECISION_MUL
    new_initial_prices[0] = precisions[0] * PRECISION  # First price is always 1e18
    self.price_scale = new_initial_prices
    self.price_oracle = new_initial_prices


@internal
@view
def xp() -> uint256[N_COINS]:
    result: uint256[N_COINS] = self.balances
    # PRECISION_MUL is already contained in self.price_scale
    for i in range(N_COINS):
        result[i] = result[i] * self.price_scale[i] / PRECISION
    return result


@internal
@pure
def sort(A0: uint256[N_COINS]) -> uint256[N_COINS]:
    """
    Insertion sort from high to low
    """
    A: uint256[N_COINS] = A0
    for i in range(1, N_COINS):
        x: uint256 = A[i]
        cur: uint256 = i
        for j in range(N_COINS):
            y: uint256 = A[cur-1]
            if y > x:
                break
            A[cur] = y
            cur -= 1
            if cur == 0:
                break
        A[cur] = x
    return A


@internal
@view
def geometric_mean(unsorted_x: uint256[N_COINS]) -> uint256:
    """
    (x[0] * x[1] * ...) ** (1/N)
    """
    x: uint256[N_COINS] = self.sort(unsorted_x)
    D: uint256 = x[0]
    diff: uint256 = 0
    for i in range(255):
        D_prev: uint256 = D
        tmp: uint256 = 10**18
        for _x in x:
            tmp = tmp * _x / D
        D = D * ((N_COINS - 1) * 10**18 + tmp) / (N_COINS * 10**18)
        if D > D_prev:
            diff = D - D_prev
        else:
            diff = D_prev - D
        if diff <= 1 or diff * 10**18 < D:
            return D
    raise "Did not converge"
