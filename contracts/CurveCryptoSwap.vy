# @version 0.2.12
# (c) Curve.Fi, 2020
# Pool for 3Crv(USD)/BTC/ETH or similar
from vyper.interfaces import ERC20

interface CurveToken:
    def totalSupply() -> uint256: view
    def mint(_to: address, _value: uint256) -> bool: nonpayable
    def mint_relative(_to: address, frac: uint256) -> uint256: nonpayable
    def burnFrom(_to: address, _value: uint256) -> bool: nonpayable


interface Math:
    def geometric_mean(unsorted_x: uint256[N_COINS]) -> uint256: view
    def reduction_coefficient(x: uint256[N_COINS], fee_gamma: uint256) -> uint256: view
    def newton_D(ANN: uint256, gamma: uint256, x_unsorted: uint256[N_COINS]) -> uint256: view
    def newton_y(ANN: uint256, gamma: uint256, x: uint256[N_COINS], D: uint256, i: uint256) -> uint256: view
    def halfpow(power: uint256, precision: uint256) -> uint256: view
    def sqrt_int(x: uint256) -> uint256: view


interface Views:
    def get_dy(i: uint256, j: uint256, dx: uint256) -> uint256: view
    def calc_token_amount(amounts: uint256[N_COINS], deposit: bool) -> uint256: view


# Events
event TokenExchange:
    buyer: indexed(address)
    sold_id: uint256
    tokens_sold: uint256
    bought_id: uint256
    tokens_bought: uint256

event AddLiquidity:
    provider: indexed(address)
    token_amounts: uint256[N_COINS]
    fee: uint256
    token_supply: uint256

event RemoveLiquidity:
    provider: indexed(address)
    token_amounts: uint256[N_COINS]
    token_supply: uint256

event RemoveLiquidityOne:
    provider: indexed(address)
    token_amount: uint256
    coin_index: uint256
    coin_amount: uint256

event CommitNewAdmin:
    deadline: indexed(uint256)
    admin: indexed(address)

event NewAdmin:
    admin: indexed(address)

event CommitNewParameters:
    deadline: indexed(uint256)
    admin_fee: uint256
    mid_fee: uint256
    out_fee: uint256
    fee_gamma: uint256
    price_threshold: uint256
    adjustment_step: uint256
    ma_half_time: uint256

event NewParameters:
    admin_fee: uint256
    mid_fee: uint256
    out_fee: uint256
    fee_gamma: uint256
    price_threshold: uint256
    adjustment_step: uint256
    ma_half_time: uint256

event RampAgamma:
    initial_A: uint256
    future_A: uint256
    initial_time: uint256
    future_time: uint256

event StopRampA:
    current_A: uint256
    current_gamma: uint256
    time: uint256

event ClaimAdminFee:
    admin: indexed(address)
    tokens: uint256


N_COINS: constant(int128) = 3  # <- change
FEE_DENOMINATOR: constant(uint256) = 10 ** 10
PRECISION: constant(uint256) = 10 ** 18  # The precision to convert to
A_MULTIPLIER: constant(uint256) = 100

# These addresses are replaced by the deployer
math: constant(address) = 0x0000000000000000000000000000000000000000
token: constant(address) = 0x0000000000000000000000000000000000000001
views: constant(address) = 0x0000000000000000000000000000000000000002
coins: constant(address[N_COINS]) = [
    0x0000000000000000000000000000000000000010,
    0x0000000000000000000000000000000000000011,
    0x0000000000000000000000000000000000000012,
]

price_scale_packed: uint256   # Internal price scale
price_oracle_packed: uint256  # Price target given by MA

last_prices_packed: uint256
last_prices_timestamp: public(uint256)

initial_A_gamma: public(uint256)
future_A_gamma: public(uint256)
initial_A_gamma_time: public(uint256)
future_A_gamma_time: public(uint256)

price_threshold: public(uint256)
future_price_threshoold: public(uint256)

fee_gamma: public(uint256)
future_fee_gamma: public(uint256)

adjustment_step: public(uint256)
future_adjustment_step: public(uint256)

ma_half_time: public(uint256)
future_ma_half_time: public(uint256)

mid_fee: public(uint256)
out_fee: public(uint256)
admin_fee: public(uint256)
future_mid_fee: public(uint256)
future_out_fee: public(uint256)
future_admin_fee: public(uint256)

balances: public(uint256[N_COINS])
D: public(uint256)

owner: public(address)
future_owner: public(address)

xcp_profit: public(uint256)
xcp_profit_a: public(uint256)  # Full profit at last claim of admin fees
virtual_price: public(uint256)  # Cached (fast to read) virtual price also used internally

is_killed: public(bool)
kill_deadline: public(uint256)
transfer_ownership_deadline: public(uint256)
admin_actions_deadline: public(uint256)

reward_receiver: public(address)

KILL_DEADLINE_DT: constant(uint256) = 2 * 30 * 86400
ADMIN_ACTIONS_DELAY: constant(uint256) = 3 * 86400
MIN_RAMP_TIME: constant(uint256) = 86400

MAX_ADMIN_FEE: constant(uint256) = 10 * 10 ** 9
MIN_FEE: constant(uint256) = 5 * 10 ** 5  # 0.5 bps
MAX_FEE: constant(uint256) = 5 * 10 ** 9
MAX_A: constant(uint256) = 10000 * A_MULTIPLIER
MAX_A_CHANGE: constant(uint256) = 10
MIN_GAMMA: constant(uint256) = 10**10
MAX_GAMMA: constant(uint256) = 10**16
NOISE_FEE: constant(uint256) = 10**5  # 0.1 bps

PRICE_SIZE: constant(int128) = 256 / (N_COINS-1)
PRICE_MASK: constant(uint256) = 2**PRICE_SIZE - 1

# This must be changed for different N_COINS
# For example:
# N_COINS = 3 -> 1  (10**18 -> 10**18)
# N_COINS = 4 -> 10**8  (10**18 -> 10**10)
PRICE_PRECISION_MUL: constant(uint256) = 1
PRECISIONS: constant(uint256[N_COINS]) = [
    1,#0
    1,#1
    1,#2
]


# Matic extras. Not needed on Ethereum!
MATIC_REWARDS: constant(address) = 0x357D51124f59836DeD84c8a1730D72B749d8BC23
WMATIC: constant(address) = 0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270


@external
def __init__(
    owner: address,
    A: uint256,
    gamma: uint256,
    mid_fee: uint256,
    out_fee: uint256,
    price_threshold: uint256,
    fee_gamma: uint256,
    adjustment_step: uint256,
    admin_fee: uint256,
    ma_half_time: uint256,
    initial_prices: uint256[N_COINS-1]
):
    self.owner = owner

    # Pack A and gamma:
    # shifted A + gamma
    A_gamma: uint256 = shift(A * A_MULTIPLIER, 128)
    A_gamma = bitwise_or(A_gamma, gamma)
    self.initial_A_gamma = A_gamma
    self.future_A_gamma = A_gamma

    self.mid_fee = mid_fee
    self.out_fee = out_fee
    self.price_threshold = price_threshold
    self.fee_gamma = fee_gamma
    self.adjustment_step = adjustment_step
    self.admin_fee = admin_fee

    # Packing prices
    packed_prices: uint256 = 0
    for k in range(N_COINS-1):
        packed_prices = shift(packed_prices, PRICE_SIZE)
        p: uint256 = initial_prices[N_COINS-2 - k] / PRICE_PRECISION_MUL
        assert p < PRICE_MASK
        packed_prices = bitwise_or(p, packed_prices)

    self.price_scale_packed = packed_prices
    self.price_oracle_packed = packed_prices
    self.last_prices_packed = packed_prices
    self.last_prices_timestamp = block.timestamp
    self.ma_half_time = ma_half_time

    self.xcp_profit_a = 10**18

    self.kill_deadline = block.timestamp + KILL_DEADLINE_DT


@external
@view
def price_oracle(k: uint256) -> uint256:
    assert k < N_COINS-1
    return bitwise_and(
        shift(self.price_oracle_packed, -PRICE_SIZE * convert(k, int128)),
        PRICE_MASK
    ) * PRICE_PRECISION_MUL


@external
@view
def price_scale(k: uint256) -> uint256:
    assert k < N_COINS-1
    return bitwise_and(
        shift(self.price_scale_packed, -PRICE_SIZE * convert(k, int128)),
        PRICE_MASK
    ) * PRICE_PRECISION_MUL


@external
@view
def last_prices(k: uint256) -> uint256:
    assert k < N_COINS-1
    return bitwise_and(
        shift(self.last_prices_packed, -PRICE_SIZE * convert(k, int128)),
        PRICE_MASK
    ) * PRICE_PRECISION_MUL


@external
@view
def token() -> address:
    return token


@external
@view
def coins(i: uint256) -> address:
    _coins: address[N_COINS] = coins
    return _coins[i]


@internal
@view
def xp() -> uint256[N_COINS]:
    result: uint256[N_COINS] = self.balances
    packed_prices: uint256 = self.price_scale_packed

    precisions: uint256[N_COINS] = PRECISIONS

    result[0] *= precisions[0]
    for i in range(1, N_COINS):
        p: uint256 = bitwise_and(packed_prices, PRICE_MASK) * PRICE_PRECISION_MUL * precisions[i]
        result[i] = result[i] * p / PRECISION
        packed_prices = shift(packed_prices, -PRICE_SIZE)

    return result


@view
@internal
def _A_gamma() -> (uint256, uint256):
    t1: uint256 = self.future_A_gamma_time

    A_gamma_1: uint256 = self.future_A_gamma
    gamma1: uint256 = bitwise_and(A_gamma_1, 2**128-1)
    A1: uint256 = shift(A_gamma_1, -128)

    if block.timestamp < t1:
        # handle ramping up and down of A
        A_gamma_0: uint256 = self.initial_A_gamma
        t0: uint256 = self.initial_A_gamma_time

        # Less readable but more compact way of writing and converting to uint256
        # gamma0: uint256 = bitwise_and(A_gamma_0, 2**128-1)
        # A0: uint256 = shift(A_gamma_0, -128)
        # A1 = A0 + (A1 - A0) * (block.timestamp - t0) / (t1 - t0)
        # gamma1 = gamma0 + (gamma1 - gamma0) * (block.timestamp - t0) / (t1 - t0)

        t1 -= t0
        t0 = block.timestamp - t0

        A1 = (shift(A_gamma_0, -128) * (t1 - t0) + A1 * t0) / t1
        gamma1 = (bitwise_and(A_gamma_0, 2**128-1) * (t1 - t0) + gamma1 * t0) / t1

    return A1, gamma1


@view
@external
def A() -> uint256:
    return self._A_gamma()[0] / A_MULTIPLIER


@view
@external
def gamma() -> uint256:
    return self._A_gamma()[1]


@view
@external
def A_precise() -> uint256:
    return self._A_gamma()[0]


@internal
@view
def _fee(xp: uint256[N_COINS]) -> uint256:
    f: uint256 = Math(math).reduction_coefficient(xp, self.fee_gamma)
    return (self.mid_fee * f + self.out_fee * (10**18 - f)) / 10**18


@external
@view
def fee() -> uint256:
    return self._fee(self.xp())


@external
@view
def fee_calc(xp: uint256[N_COINS]) -> uint256:
    return self._fee(xp)


@internal
@view
def get_xcp(_D: uint256 = 0) -> uint256:
    x: uint256[N_COINS] = empty(uint256[N_COINS])
    D: uint256 = _D
    if D == 0:
        D = self.D
    x[0] = D / N_COINS
    packed_prices: uint256 = self.price_scale_packed
    # No precisions here because we don't switch to "real" units

    for i in range(1, N_COINS):
        x[i] = D * 10**18 / (N_COINS * bitwise_and(packed_prices, PRICE_MASK) * PRICE_PRECISION_MUL)
        packed_prices = shift(packed_prices, -PRICE_SIZE)

    return Math(math).geometric_mean(x)


@external
@view
def get_virtual_price() -> uint256:
    return 10**18 * self.get_xcp() / CurveToken(token).totalSupply()


@internal
def tweak_price(A: uint256, gamma: uint256,
                _xp: uint256[N_COINS], i: uint256, p_i: uint256,
                new_D: uint256 = 0):
    # Update MA if needed
    price_oracle: uint256[N_COINS-1] = empty(uint256[N_COINS-1])
    packed_prices: uint256 = self.price_oracle_packed
    for k in range(N_COINS-1):
        price_oracle[k] = bitwise_and(packed_prices, PRICE_MASK) * PRICE_PRECISION_MUL
        packed_prices = shift(packed_prices, -PRICE_SIZE)

    last_prices_timestamp: uint256 = self.last_prices_timestamp
    last_prices: uint256[N_COINS-1] = empty(uint256[N_COINS-1])
    packed_prices = self.last_prices_packed
    for k in range(N_COINS-1):
        last_prices[k] = bitwise_and(packed_prices, PRICE_MASK) * PRICE_PRECISION_MUL
        packed_prices = shift(packed_prices, -PRICE_SIZE)

    if last_prices_timestamp < block.timestamp:
        # MA update required
        ma_half_time: uint256 = self.ma_half_time
        alpha: uint256 = Math(math).halfpow((block.timestamp - last_prices_timestamp) * 10**18 / ma_half_time, 10**10)
        packed_prices = 0
        for k in range(N_COINS-1):
            price_oracle[k] = (last_prices[k] * (10**18 - alpha) + price_oracle[k] * alpha) / 10**18
        for k in range(N_COINS-1):
            packed_prices = shift(packed_prices, PRICE_SIZE)
            p: uint256 = price_oracle[N_COINS-2 - k] / PRICE_PRECISION_MUL
            assert p < PRICE_MASK
            packed_prices = bitwise_or(p, packed_prices)
        self.price_oracle_packed = packed_prices
        self.last_prices_timestamp = block.timestamp

    D_unadjusted: uint256 = new_D  # Withdrawal methods know new D already
    if new_D == 0:
        # We will need this a few times (35k gas)
        D_unadjusted = Math(math).newton_D(A, gamma, _xp)
    packed_prices = self.price_scale_packed
    price_scale: uint256[N_COINS-1] = empty(uint256[N_COINS-1])
    for k in range(N_COINS-1):
        price_scale[k] = bitwise_and(packed_prices, PRICE_MASK) * PRICE_PRECISION_MUL
        packed_prices = shift(packed_prices, -PRICE_SIZE)

    if p_i > 0:
        # Save the last price
        if i > 0:
            last_prices[i-1] = p_i
        else:
            # If 0th price changed - change all prices instead
            for k in range(N_COINS-1):
                last_prices[k] = last_prices[k] * 10**18 / p_i
    else:
        # calculate real prices
        # it would cost 70k gas for a 3-token pool. Sad. How do we do better?
        __xp: uint256[N_COINS] = _xp
        dx_price: uint256 = __xp[0] / 10**6
        __xp[0] += dx_price
        for k in range(N_COINS-1):
            last_prices[k] = price_scale[k] * dx_price / (_xp[k+1] - Math(math).newton_y(A, gamma, __xp, D_unadjusted, k+1))

    packed_prices = 0
    for k in range(N_COINS-1):
        packed_prices = shift(packed_prices, PRICE_SIZE)
        p: uint256 = last_prices[N_COINS-2 - k] / PRICE_PRECISION_MUL
        assert p < PRICE_MASK
        packed_prices = bitwise_or(p, packed_prices)
    self.last_prices_packed = packed_prices

    norm: uint256 = 0
    total_supply: uint256 = CurveToken(token).totalSupply()
    old_xcp_profit: uint256 = self.xcp_profit
    old_virtual_price: uint256 = self.virtual_price
    for k in range(N_COINS-1):
        ratio: uint256 = price_oracle[k] * 10**18 / price_scale[k]
        if ratio > 10**18:
            ratio -= 10**18
        else:
            ratio = 10**18 - ratio
        norm += ratio**2


    # Update profit numbers without price adjustment first
    xp: uint256[N_COINS] = empty(uint256[N_COINS])
    xp[0] = D_unadjusted / N_COINS
    for k in range(N_COINS-1):
        xp[k+1] = D_unadjusted * 10**18 / (N_COINS * price_scale[k])
    xcp_profit: uint256 = 10**18
    virtual_price: uint256 = 10**18

    if old_virtual_price > 0:
        xcp: uint256 = Math(math).geometric_mean(xp)
        virtual_price = 10**18 * xcp / total_supply
        xcp_profit = old_xcp_profit * virtual_price / old_virtual_price

        if virtual_price < old_virtual_price:
            raise "Loss"

    self.xcp_profit = xcp_profit

    # self.price_threshold must be > self.adjustment_step
    # should we pause for a bit if profit wasn't enough to not spend this gas every time?
    if norm > self.price_threshold ** 2 and old_virtual_price > 0:
        norm = Math(math).sqrt_int(norm / 10**18)  # Need to convert to 1e18 units!
        adjustment_step: uint256 = self.adjustment_step

        p_new: uint256[N_COINS-1] = empty(uint256[N_COINS-1])
        for k in range(N_COINS-1):
            p_new[k] = (price_scale[k] * (norm - adjustment_step) + adjustment_step * price_oracle[k]) / norm

        # Calculate balances*prices
        xp = _xp
        for k in range(N_COINS-1):
            xp[k+1] = _xp[k+1] * p_new[k] / price_scale[k]

        # Calculate "extended constant product" invariant xCP and virtual price
        D: uint256 = Math(math).newton_D(A, gamma, xp)
        xp[0] = D / N_COINS
        for k in range(N_COINS-1):
            xp[k+1] = D * 10**18 / (N_COINS * p_new[k])
        # We reuse old_virtual_price here but it's not old anymore
        old_virtual_price = 10**18 * Math(math).geometric_mean(xp) / total_supply

        # Proceed if we've got enough profit
        if (old_virtual_price > 10**18) and (2 * (old_virtual_price - 10**18) > xcp_profit - 10**18):
            packed_prices = 0
            for k in range(N_COINS-1):
                packed_prices = shift(packed_prices, PRICE_SIZE)
                p: uint256 = p_new[N_COINS-2 - k] / PRICE_PRECISION_MUL
                assert p < PRICE_MASK
                packed_prices = bitwise_or(p, packed_prices)
            self.price_scale_packed = packed_prices
            self.D = D
            self.virtual_price = old_virtual_price
            return

        # else - make a delay?

    # If we are here, the price_scale adjustment did not happen
    # Still need to update the profit counter and D
    self.D = D_unadjusted
    self.virtual_price = virtual_price


@external
@nonreentrant('lock')
def exchange(i: uint256, j: uint256, dx: uint256, min_dy: uint256,
             _for: address = msg.sender):
    assert not self.is_killed  # dev: the pool is killed
    assert i != j and i < N_COINS and j < N_COINS  # dev: coin index out of range
    assert dx > 0  # dev: do not exchange 0 coins

    A: uint256 = 0
    gamma: uint256 = 0
    A, gamma = self._A_gamma()

    _coins: address[N_COINS] = coins

    # assert might be needed for some tokens - removed one to save bytespace
    ERC20(_coins[i]).transferFrom(msg.sender, self, dx)

    price_scale: uint256[N_COINS-1] = empty(uint256[N_COINS-1])
    if True:  # scope to clear packed_prices
        packed_prices: uint256 = self.price_scale_packed
        for k in range(N_COINS-1):
            price_scale[k] = bitwise_and(packed_prices, PRICE_MASK) * PRICE_PRECISION_MUL
            packed_prices = shift(packed_prices, -PRICE_SIZE)

    xp: uint256[N_COINS] = self.balances
    y: uint256 = xp[j]
    xp[i] += dx
    self.balances[i] = xp[i]
    precisions: uint256[N_COINS] = PRECISIONS
    xp[0] *= precisions[0]
    for k in range(1, N_COINS):
        xp[k] = xp[k] * price_scale[k-1] * precisions[k] / PRECISION

    dy: uint256 = xp[j] - Math(math).newton_y(A, gamma, xp, self.D, j)
    # Not defining new "y" here to have less variables / make subsequent calls cheaper
    xp[j] -= dy
    dy -= 1

    if j > 0:
        dy = dy * PRECISION / price_scale[j-1]
    dy /= precisions[j]
    dy -= self._fee(xp) * dy / 10**10
    assert dy >= min_dy, "Slippage"
    y -= dy

    self.balances[j] = y
    # assert might be needed for some tokens - removed one to save bytespace
    ERC20(_coins[j]).transfer(_for, dy)

    xp[j] = y * precisions[j]
    if j > 0:
        xp[j] = xp[j] * price_scale[j-1] / PRECISION

    # Calculate price
    p: uint256 = 0
    ix: uint256 = j
    if dx > 10**5 and dy > 10**5:
        if i != 0 and j != 0:
            p = bitwise_and(
                shift(self.last_prices_packed, -PRICE_SIZE * convert(i-1, int128)),
                PRICE_MASK
            ) * PRICE_PRECISION_MUL * (dx * precisions[i]) / (dy * precisions[j])
        elif i == 0:
            p = (dx * precisions[i]) * 10**18 / (dy * precisions[j])
        else:  # j == 0
            p = (dy * precisions[j]) * 10**18 / (dx * precisions[i])
            ix = i

    self.tweak_price(A, gamma, xp, ix, p)

    log TokenExchange(_for, i, dx, j, dy)


@external
@view
def get_dy(i: uint256, j: uint256, dx: uint256) -> uint256:
    return Views(views).get_dy(i, j, dx)


@view
@internal
def _calc_token_fee(amounts: uint256[N_COINS], xp: uint256[N_COINS]) -> uint256:
    # fee = sum(amounts_i - avg(amounts)) * fee' / sum(amounts)
    fee: uint256 = self._fee(xp) * N_COINS / (4 * (N_COINS-1))
    S: uint256 = 0
    for _x in amounts:
        S += _x
    avg: uint256 = S / N_COINS
    Sdiff: uint256 = 0
    for _x in amounts:
        if _x > avg:
            Sdiff += _x - avg
        else:
            Sdiff += avg - _x
    return fee * Sdiff / S + NOISE_FEE


@external
@view
def calc_token_fee(amounts: uint256[N_COINS], xp: uint256[N_COINS]) -> uint256:
    return self._calc_token_fee(amounts, xp)


@external
@nonreentrant('lock')
def add_liquidity(amounts: uint256[N_COINS], min_mint_amount: uint256,
                  _for: address = msg.sender):
    assert not self.is_killed  # dev: the pool is killed

    A: uint256 = 0
    gamma: uint256 = 0
    A, gamma = self._A_gamma()

    _coins: address[N_COINS] = coins

    xp: uint256[N_COINS] = self.balances
    amountsp: uint256[N_COINS] = amounts
    xx: uint256[N_COINS] = empty(uint256[N_COINS])

    if True:  # Scope to avoid having extra variables in memory later
        n_coins_added: uint256 = 0
        for i in range(N_COINS):
            if amounts[i] > 0:
                # assert might be needed for some tokens - removed one to save bytespace
                ERC20(_coins[i]).transferFrom(msg.sender, self, amounts[i])
                n_coins_added += 1
        assert n_coins_added > 0  # dev: no coins to add

        for i in range(N_COINS):
            bal: uint256 = xp[i] + amounts[i]
            xp[i] = bal
            self.balances[i] = bal
        xx = xp

        precisions: uint256[N_COINS] = PRECISIONS
        packed_prices: uint256 = self.price_scale_packed
        xp[0] *= precisions[0]
        for i in range(1, N_COINS):
            price_scale: uint256 = bitwise_and(packed_prices, PRICE_MASK) * PRICE_PRECISION_MUL * precisions[i]
            xp[i] = xp[i] * price_scale / PRECISION
            amountsp[i] = amountsp[i] * price_scale / PRECISION
            packed_prices = shift(packed_prices, -PRICE_SIZE)

    D: uint256 = Math(math).newton_D(A, gamma, xp)

    token_supply: uint256 = CurveToken(token).totalSupply()
    old_D: uint256 = self.D
    d_token: uint256 = 0
    if old_D > 0:
        d_token = token_supply * D / old_D - token_supply
    else:
        d_token = self.get_xcp(D)  # making initial virtual price equal to 1
    assert d_token > 0  # dev: nothing minted

    d_token_fee: uint256 = 0
    if old_D > 0:
        d_token_fee = self._calc_token_fee(amountsp, xp) * d_token / 10**10 + 1
        d_token -= d_token_fee
        token_supply += d_token
        assert CurveToken(token).mint(_for, d_token)

        # Calculate price
        # p_i * (dx_i - dtoken / token_supply * xx_i) = sum{k!=i}(p_k * (dtoken / token_supply * xx_k - dx_k))
        # Only ix is nonzero
        p: uint256 = 0
        ix: uint256 = 0
        if d_token > 10**5:
            n_zeros: uint256 = 0
            for i in range(N_COINS):
                if amounts[i] == 0:
                    n_zeros += 1
                else:
                    ix = i
            if n_zeros == N_COINS-1:
                S: uint256 = 0
                last_prices: uint256[N_COINS-1] = empty(uint256[N_COINS-1])
                packed_prices: uint256 = self.last_prices_packed
                precisions: uint256[N_COINS] = PRECISIONS
                for k in range(N_COINS-1):
                    last_prices[k] = bitwise_and(packed_prices, PRICE_MASK) * PRICE_PRECISION_MUL
                    packed_prices = shift(packed_prices, -PRICE_SIZE)
                for i in range(N_COINS):
                    if i != ix:
                        if i == 0:
                            S += xx[0] * precisions[0]
                        else:
                            S += xx[i] * last_prices[i-1] * precisions[i] / PRECISION
                S = S * d_token / token_supply
                p = S * PRECISION / (amounts[ix] * precisions[ix] - d_token * xx[ix] * precisions[ix] / token_supply)

        self.tweak_price(A, gamma, xp, ix, p, D)

    else:
        self.D = D
        self.virtual_price = 10**18
        self.xcp_profit = 10**18
        assert CurveToken(token).mint(_for, d_token)

    assert d_token >= min_mint_amount, "Slippage"

    log AddLiquidity(_for, amounts, d_token_fee, token_supply)


@external
@nonreentrant('lock')
def remove_liquidity(_amount: uint256, min_amounts: uint256[N_COINS],
                     _for: address = msg.sender):
    """
    This withdrawal method is very safe, does no complex math
    """
    _coins: address[N_COINS] = coins
    total_supply: uint256 = CurveToken(token).totalSupply()
    assert CurveToken(token).burnFrom(msg.sender, _amount)
    balances: uint256[N_COINS] = self.balances
    amount: uint256 = _amount - 1  # Make rounding errors favoring other LPs a tiny bit

    for i in range(N_COINS):
        d_balance: uint256 = balances[i] * amount / total_supply
        assert d_balance >= min_amounts[i]
        self.balances[i] = balances[i] - d_balance
        balances[i] = d_balance  # now it's the amounts going out
        # assert might be needed for some tokens - removed one to save bytespace
        ERC20(_coins[i]).transfer(_for, d_balance)

    D: uint256 = self.D
    self.D = D - D * amount / total_supply

    log RemoveLiquidity(msg.sender, balances, total_supply - _amount)


@view
@external
def calc_token_amount(amounts: uint256[N_COINS], deposit: bool) -> uint256:
    return Views(views).calc_token_amount(amounts, deposit)


@internal
@view
def _calc_withdraw_one_coin(A: uint256, gamma: uint256, token_amount: uint256, i: uint256,
                            calc_only: bool = False) -> (uint256, uint256, uint256, uint256[N_COINS]):
    D: uint256 = self.D
    D0: uint256 = D
    token_supply: uint256 = CurveToken(token).totalSupply()
    assert token_amount <= token_supply  # dev: token amount more than supply
    assert i < N_COINS  # dev: coin out of range

    xx: uint256[N_COINS] = self.balances
    xp: uint256[N_COINS] = PRECISIONS

    price_scale_i: uint256 = PRECISION * xp[0]
    if True:  # To remove oacked_prices from memory
        packed_prices: uint256 = self.price_scale_packed
        xp[0] *= xx[0]
        for k in range(1, N_COINS):
            p: uint256 = bitwise_and(packed_prices, PRICE_MASK) * PRICE_PRECISION_MUL
            if i == k:
                price_scale_i = p * xp[i]
            xp[k] = xp[k] * xx[k] * p / PRECISION
            packed_prices = shift(packed_prices, -PRICE_SIZE)

    # Charge the fee on D, not on y, e.g. reducing invariant LESS than charging the user
    fee: uint256 = self._fee(xp)
    dD: uint256 = token_amount * D / token_supply
    D -= (dD - (fee * dD / (2 * 10**10) + 1))
    y: uint256 = Math(math).newton_y(A, gamma, xp, D, i)
    dy: uint256 = y * PRECISION / price_scale_i
    dy = xx[i] - dy
    xp[i] = y

    # Price calc
    p: uint256 = 0
    if (not calc_only) and dy > 10**5 and token_amount > 10**5:
        # p_i = dD / D0 * sum'(p_k * x_k) / (dy - dD / D0 * y0)
        S: uint256 = 0
        precisions: uint256[N_COINS] = PRECISIONS
        last_prices: uint256[N_COINS-1] = empty(uint256[N_COINS-1])
        packed_prices: uint256 = self.last_prices_packed
        for k in range(N_COINS-1):
            last_prices[k] = bitwise_and(packed_prices, PRICE_MASK) * PRICE_PRECISION_MUL
            packed_prices = shift(packed_prices, -PRICE_SIZE)
        for k in range(N_COINS):
            if k != i:
                if k == 0:
                    S += xx[0] * precisions[0]
                else:
                    S += xx[k] * last_prices[k-1] * precisions[k] / PRECISION
        S = S * dD / D0
        p = S * PRECISION / (dy * precisions[i] - dD * xx[i] * precisions[i] / D0)

    return dy, p, D, xp


@view
@external
def calc_withdraw_one_coin(token_amount: uint256, i: uint256) -> uint256:
    A: uint256 = 0
    gamma: uint256 = 0
    A, gamma = self._A_gamma()
    return self._calc_withdraw_one_coin(A, gamma, token_amount, i, True)[0]


@external
@nonreentrant('lock')
def remove_liquidity_one_coin(token_amount: uint256, i: uint256, min_amount: uint256,
                              _for: address = msg.sender):
    assert not self.is_killed  # dev: the pool is killed

    A: uint256 = 0
    gamma: uint256 = 0
    A, gamma = self._A_gamma()

    dy: uint256 = 0
    D: uint256 = 0
    p: uint256 = 0
    xp: uint256[N_COINS] = empty(uint256[N_COINS])
    dy, p, D, xp = self._calc_withdraw_one_coin(A, gamma, token_amount, i)
    assert dy >= min_amount, "Slippage"

    self.balances[i] -= dy
    assert CurveToken(token).burnFrom(msg.sender, token_amount)
    if True:  # Remove _coins from the scope
        _coins: address[N_COINS] = coins
        # assert might be needed for some tokens - removed one to save bytespace
        ERC20(_coins[i]).transfer(_for, dy)

    self.tweak_price(A, gamma, xp, i, p, D)

    log RemoveLiquidityOne(msg.sender, token_amount, i, dy)


@internal
def _claim_admin_fees():
    owner: address = self.owner

    xcp_profit: uint256 = self.xcp_profit
    vprice: uint256 = self.virtual_price
    fees: uint256 = (xcp_profit - self.xcp_profit_a) * self.admin_fee / (2 * 10**10)

    if fees > 0:
        # Would be nice to recalc D, but we have no bytespace left

        frac: uint256 = vprice * 10**18 / (vprice - fees) - 10**18
        claimed: uint256 = CurveToken(token).mint_relative(owner, frac)
        total_supply: uint256 = CurveToken(token).totalSupply()

        # Gulp here
        _coins: address[N_COINS] = coins
        for i in range(N_COINS):
            self.balances[i] = ERC20(_coins[i]).balanceOf(self)

        # Recalculate D b/c we gulped
        A: uint256 = 0
        gamma: uint256 = 0
        A, gamma = self._A_gamma()
        xp: uint256[N_COINS] = self.xp()
        D: uint256 = Math(math).newton_D(A, gamma, xp)

        new_vprice: uint256 = 10**18 * self.get_xcp(D) / total_supply
        self.virtual_price = new_vprice

        xcp_profit = new_vprice + xcp_profit - vprice - fees
        self.xcp_profit_a = xcp_profit
        self.xcp_profit = xcp_profit

        log ClaimAdminFee(owner, claimed)

    # push wMatic rewards into the reward receiver
    reward_receiver: address = self.reward_receiver
    if reward_receiver != ZERO_ADDRESS:
        response: Bytes[32] = raw_call(
            MATIC_REWARDS,
            concat(
                method_id("claimRewards(address[],uint256,address)"),
                convert(32 * 3, bytes32),
                convert(MAX_UINT256, bytes32),
                convert(self, bytes32),
                convert(2, bytes32),
                convert(coins[1], bytes32),
                convert(coins[2], bytes32),
            ),
            max_outsize=32
        )
        # can do if amount > 0, but here we try to save space rather than anything else
        # assert might be needed for some tokens - removed one to save bytespace
        ERC20(WMATIC).transfer(reward_receiver, convert(response, uint256))


@external
@nonreentrant('lock')
def claim_admin_fees():
    self._claim_admin_fees()


# Admin parameters
@external
def ramp_A_gamma(future_A: uint256, future_gamma: uint256, future_time: uint256):
    assert msg.sender == self.owner  # dev: only owner
    assert block.timestamp >= self.initial_A_gamma_time + MIN_RAMP_TIME
    assert future_time >= block.timestamp + MIN_RAMP_TIME  # dev: insufficient time

    initial_A: uint256 = 0
    initial_gamma: uint256 = 0
    initial_A, initial_gamma = self._A_gamma()
    initial_A_gamma: uint256 = shift(initial_A, 128)
    initial_A_gamma = bitwise_or(initial_A_gamma, initial_gamma)

    future_A_p: uint256 = future_A * A_MULTIPLIER

    assert future_A > 0 and future_A < MAX_A
    assert future_gamma >= MIN_GAMMA and future_gamma <= MAX_GAMMA
    if future_A_p < initial_A:
        assert future_A_p * MAX_A_CHANGE >= initial_A
    else:
        assert future_A_p <= initial_A * MAX_A_CHANGE

    self.initial_A_gamma = initial_A_gamma
    self.initial_A_gamma_time = block.timestamp

    future_A_gamma: uint256 = shift(future_A_p, 128)
    future_A_gamma = bitwise_or(future_A_gamma, future_gamma)
    self.future_A_gamma_time = future_time
    self.future_A_gamma = future_A_gamma

    log RampAgamma(initial_A, future_A_p, block.timestamp, future_time)


@external
def stop_ramp_A_gamma():
    assert msg.sender == self.owner  # dev: only owner

    current_A: uint256 = 0
    current_gamma: uint256 = 0
    current_A, current_gamma = self._A_gamma()
    current_A_gamma: uint256 = shift(current_A, 128)
    current_A_gamma = bitwise_or(current_A_gamma, current_gamma)
    self.initial_A_gamma = current_A_gamma
    self.future_A_gamma = current_A_gamma
    self.initial_A_gamma_time = block.timestamp
    self.future_A_gamma_time = block.timestamp
    # now (block.timestamp < t1) is always False, so we return saved A

    log StopRampA(current_A, current_gamma, block.timestamp)


@external
def commit_new_parameters(
    _new_mid_fee: uint256,
    _new_out_fee: uint256,
    _new_admin_fee: uint256,
    _new_fee_gamma: uint256,
    _new_price_threshold: uint256,
    _new_adjustment_step: uint256,
    _new_ma_half_time: uint256,
    ):
    assert msg.sender == self.owner  # dev: only owner
    assert self.admin_actions_deadline == 0  # dev: active action

    new_mid_fee: uint256 = _new_mid_fee
    new_out_fee: uint256 = _new_out_fee
    new_admin_fee: uint256 = _new_admin_fee
    new_fee_gamma: uint256 = _new_fee_gamma
    new_price_threshold: uint256 = _new_price_threshold
    new_adjustment_step: uint256 = _new_adjustment_step
    new_ma_half_time: uint256 = _new_ma_half_time

    # Fees
    if new_out_fee != MAX_UINT256:
        assert new_out_fee <= MAX_FEE  and new_out_fee >= MIN_FEE  # dev: fee is out of range
    else:
        new_out_fee = self.out_fee
    if new_mid_fee == MAX_UINT256:
        new_mid_fee = self.mid_fee
    assert new_mid_fee <= new_out_fee  # dev: mid-fee is too high
    if new_admin_fee != MAX_UINT256:
        assert new_admin_fee <= MAX_ADMIN_FEE  # dev: admin fee exceeds maximum
    else:
        new_admin_fee = self.admin_fee

    # AMM parameters
    if new_fee_gamma != MAX_UINT256:
        assert new_fee_gamma > 0 and new_fee_gamma < 2**100  # dev: fee_gamma out of range [1 .. 2**100]
    else:
        new_fee_gamma = self.fee_gamma
    if new_price_threshold != MAX_UINT256:
        assert new_price_threshold > new_mid_fee  # dev: price threshold should be higher than the fee
    else:
        new_price_threshold = self.price_threshold
    if new_adjustment_step == MAX_UINT256:
        new_adjustment_step = self.adjustment_step
    assert new_adjustment_step <= new_price_threshold  # dev: adjustment step should be smaller than price threshold

    # MA
    if new_ma_half_time != MAX_UINT256:
        assert new_ma_half_time > 0 and new_ma_half_time < 7*86400  # dev: MA time should be shorter than 1 week
    else:
        new_ma_half_time = self.ma_half_time

    _deadline: uint256 = block.timestamp + ADMIN_ACTIONS_DELAY
    self.admin_actions_deadline = _deadline

    self.future_admin_fee = new_admin_fee
    self.future_mid_fee = new_mid_fee
    self.future_out_fee = new_out_fee
    self.future_fee_gamma = new_fee_gamma
    self.future_price_threshoold = new_price_threshold
    self.future_adjustment_step = new_adjustment_step
    self.future_ma_half_time = new_ma_half_time

    log CommitNewParameters(_deadline, new_admin_fee, new_mid_fee, new_out_fee,
                            new_fee_gamma,
                            new_price_threshold, new_adjustment_step,
                            new_ma_half_time)


@external
@nonreentrant('lock')
def apply_new_parameters():
    assert msg.sender == self.owner  # dev: only owner
    assert block.timestamp >= self.admin_actions_deadline  # dev: insufficient time
    assert self.admin_actions_deadline != 0  # dev: no active action

    self.admin_actions_deadline = 0

    admin_fee: uint256 = self.future_admin_fee
    if self.admin_fee != admin_fee:
        self._claim_admin_fees()
        self.admin_fee = admin_fee

    mid_fee: uint256 = self.future_mid_fee
    self.mid_fee = mid_fee
    out_fee: uint256 = self.future_out_fee
    self.out_fee = out_fee
    fee_gamma: uint256 = self.future_fee_gamma
    self.fee_gamma = fee_gamma
    price_threshold: uint256 = self.future_price_threshoold
    self.price_threshold = price_threshold
    adjustment_step: uint256 = self.future_adjustment_step
    self.adjustment_step = adjustment_step
    ma_half_time: uint256 = self.future_ma_half_time
    self.ma_half_time = ma_half_time

    log NewParameters(admin_fee, mid_fee, out_fee,
                      fee_gamma,
                      price_threshold, adjustment_step,
                      ma_half_time)


@external
def revert_new_parameters():
    assert msg.sender == self.owner  # dev: only owner

    self.admin_actions_deadline = 0


@external
def commit_transfer_ownership(_owner: address):
    assert msg.sender == self.owner  # dev: only owner
    assert self.transfer_ownership_deadline == 0  # dev: active transfer

    _deadline: uint256 = block.timestamp + ADMIN_ACTIONS_DELAY
    self.transfer_ownership_deadline = _deadline
    self.future_owner = _owner

    log CommitNewAdmin(_deadline, _owner)


@external
def apply_transfer_ownership():
    assert msg.sender == self.owner  # dev: only owner
    assert block.timestamp >= self.transfer_ownership_deadline  # dev: insufficient time
    assert self.transfer_ownership_deadline != 0  # dev: no active transfer

    self.transfer_ownership_deadline = 0
    _owner: address = self.future_owner
    self.owner = _owner

    log NewAdmin(_owner)


@external
def revert_transfer_ownership():
    assert msg.sender == self.owner  # dev: only owner

    self.transfer_ownership_deadline = 0


@external
def kill_me():
    assert msg.sender == self.owner  # dev: only owner
    assert self.kill_deadline > block.timestamp  # dev: deadline has passed
    self.is_killed = True


@external
def unkill_me():
    assert msg.sender == self.owner  # dev: only owner
    self.is_killed = False


@external
def set_reward_receiver(_reward_receiver: address):
    assert msg.sender == self.owner
    self.reward_receiver = _reward_receiver
