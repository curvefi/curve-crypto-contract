# @version 0.2.8
# (c) Curve.Fi, 2020
# Pool for 3Crv(USD)/BTC/ETH or similar
from vyper.interfaces import ERC20

interface CurveToken:
    def totalSupply() -> uint256: view
    def mint(_to: address, _value: uint256) -> bool: nonpayable
    def mint_relative(_to: address, frac: uint256) -> bool: nonpayable
    def burnFrom(_to: address, _value: uint256) -> bool: nonpayable

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


N_COINS: constant(int128) = 3  # <- change
PRECISION_MUL: constant(uint256[N_COINS]) = [1, 1, 1]  # 3usd, renpool, eth
FEE_DENOMINATOR: constant(uint256) = 10 ** 10
PRECISION: constant(uint256) = 10 ** 18  # The precision to convert to
A_MULTIPLIER: constant(uint256) = 100

price_scale: public(uint256[N_COINS-1])   # Internal price scale
price_oracle: public(uint256[N_COINS-1])  # Price target given by MA

last_prices: public(uint256[N_COINS-1])
last_prices_timestamp: public(uint256)

A_precise: public(uint256)
gamma: public(uint256)
mid_fee: public(uint256)
out_fee: public(uint256)
price_threshold: public(uint256)
fee_gamma: public(uint256)
adjustment_step: public(uint256)
ma_half_time: public(uint256)

balances: public(uint256[N_COINS])
coins: public(address[N_COINS])
D: public(uint256)

token: public(address)
owner: public(address)

admin_fee: public(uint256)

xcp_profit_real: public(uint256)  # xcp_profit_real in simulation
xcp_profit: uint256
xcp: uint256

is_killed: public(bool)


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
    ma_half_time: uint256,
    initial_prices: uint256[N_COINS-1]
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
    new_initial_prices: uint256[N_COINS-1] = initial_prices
    precisions: uint256[N_COINS] = PRECISION_MUL
    new_initial_prices[0] = precisions[0] * PRECISION  # First price is always 1e18
    self.price_scale = new_initial_prices
    self.price_oracle = new_initial_prices
    self.last_prices = new_initial_prices
    self.last_prices_timestamp = block.timestamp
    self.ma_half_time = ma_half_time


@internal
@view
def xp() -> uint256[N_COINS]:
    result: uint256[N_COINS] = self.balances
    # PRECISION_MUL is already contained in self.price_scale
    for i in range(N_COINS-1):
        result[i+1] = result[i+1] * self.price_scale[i] / PRECISION
    return result


####################################
# Necessary mathematical functions #
####################################
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
def geometric_mean(unsorted_x: uint256[N_COINS], sort: bool = True) -> uint256:
    """
    (x[0] * x[1] * ...) ** (1/N)
    """
    x: uint256[N_COINS] = unsorted_x
    if sort:
        x = self.sort(x)
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


@internal
@pure
def reduction_coefficient(x: uint256[N_COINS], gamma: uint256) -> uint256:
    """
    gamma / (gamma + (1 - K))
    where
    K = prod(x) / (sum(x) / N)**N
    (all normalized to 1e18)
    """
    # XXX check limits of applicability
    K: uint256 = 10**18
    S: uint256 = 0
    for x_i in x:
        S += x_i
    # Could be good to pre-sort x, but it is used only for dynamic fee,
    # so that is not so important
    for x_i in x:
        K = K * N_COINS * x_i / S
    if gamma > 0:
        K = gamma * 10**18 / (gamma + 10**18 - K)
    return K


@internal
@view
def newton_D(ANN: uint256, gamma: uint256, x_unsorted: uint256[N_COINS]) -> uint256:
    """
    Finding the invariant using Newton method.
    ANN is higher by the factor A_MULTIPLIER
    ANN is already A * N**N

    Currently uses 60k gas
    """
    # Safety checks
    assert ANN > N_COINS**N_COINS * A_MULTIPLIER - 1 and ANN < 10000 * N_COINS**N_COINS * A_MULTIPLIER + 1  # dev: unsafe values A
    assert gamma > 10**10-1 and gamma < 10**16+1  # dev: unsafe values gamma
    assert x_unsorted[0] > 10**9 - 1 and x_unsorted[0] < 10**15 * 10**18 + 1  # dev: unsafe values x[0]
    for i in range(1, N_COINS):
        frac: uint256 = x_unsorted[i] * 10**18 / x_unsorted[0]
        assert (frac > 10**13-1) and (frac < 10**23+1)  # dev: unsafe values x[i]

    # Initial value of invariant D is that for constant-product invariant
    x: uint256[N_COINS] = self.sort(x_unsorted)

    D: uint256 = N_COINS * self.geometric_mean(x, False)
    S: uint256 = 0
    for x_i in x:
        S += x_i

    for i in range(255):
        D_prev: uint256 = D

        K0: uint256 = 10**18
        for _x in x:
            K0 = K0 * _x * N_COINS / D

        _g1k0: uint256 = gamma + 10**18
        if _g1k0 > K0:
            _g1k0 -= K0
        else:
            _g1k0 = K0 - _g1k0

        # D / (A * N**N) * _g1k0**2 / gamma**2
        mul1: uint256 = 10**18 * D / gamma * _g1k0 / gamma * _g1k0 * A_MULTIPLIER / ANN

        # 2*N*K0 / _g1k0
        mul2: uint256 = (2 * 10**18) * N_COINS * K0 / _g1k0

        neg_fprime: uint256 = (S + S * mul2 / 10**18) + mul1 * N_COINS / K0 - mul2 * D / 10**18

        # D -= f / fprime
        D_plus: uint256 = D * (neg_fprime + S) / neg_fprime
        D_minus: uint256 = D*D / neg_fprime
        if 10**18 > K0:
            D_minus += D * (mul1 / neg_fprime) / 10**18 * (10**18 - K0) / K0
        else:
            D_minus -= D * (mul1 / neg_fprime) / 10**18 * (K0 - 10**18) / K0

        if D_plus > D_minus:
            D = D_plus - D_minus
        else:
            D = (D_minus - D_plus) / 2

        diff: uint256 = 0
        if D > D_prev:
            diff = D - D_prev
        else:
            diff = D_prev - D
        if diff * 10**14 < max(10**16, D):  # Could reduce precision for gas efficiency here
            return D

    raise "Did not converge"


@internal
@view
def newton_y(ANN: uint256, gamma: uint256, x: uint256[N_COINS], D: uint256, i: uint256) -> uint256:
    """
    Calculating x[i] given other balances x[0..N_COINS-1] and invariant D
    ANN = A * N**N
    """
    # Safety checks
    assert ANN > N_COINS**N_COINS * A_MULTIPLIER - 1 and ANN < 10000 * N_COINS**N_COINS * A_MULTIPLIER + 1  # dev: unsafe values A
    assert gamma > 10**10-1 and gamma < 10**16+1  # dev: unsafe values gamma
    assert D > 10**17 - 1 and D < 10**15 * 10**18 + 1 # dev: unsafe values D
    for _x in x:
        frac: uint256 = _x * 10**18 / D
        assert (frac > 5 * 10**15 - 1) and (frac < 2 * 10**20 + 1)  # dev: unsafe values x[i]

    y: uint256 = D / N_COINS
    K0_i: uint256 = 10**18
    S_i: uint256 = 0

    x_sorted: uint256[N_COINS] = x
    x_sorted[i] = 0
    x_sorted = self.sort(x_sorted)  # From high to low

    convergence_limit: uint256 = max(max(x_sorted[0] / 10**14, D / 10**14), 100)
    for j in range(2, N_COINS+1):
        _x: uint256 = x_sorted[N_COINS-j]
        y = y * D / (_x * N_COINS)  # Small _x first
        S_i += _x
    for j in range(N_COINS-1):
        K0_i = K0_i * x_sorted[j] * N_COINS / D  # Large _x first

    for j in range(255):
        y_prev: uint256 = y

        K0: uint256 = K0_i * y * N_COINS / D
        S: uint256 = S_i + y

        _g1k0: uint256 = gamma + 10**18
        if _g1k0 > K0:
            _g1k0 -= K0
        else:
            _g1k0 = K0 - _g1k0

        # D / (A * N**N) * _g1k0**2 / gamma**2
        mul1: uint256 = 10**18 * D / gamma * _g1k0 / gamma * _g1k0 * A_MULTIPLIER / ANN

        # 2*K0 / _g1k0
        mul2: uint256 = 10**18 + (2 * 10**18) * K0 / _g1k0

        yfprime: uint256 = 10**18 * y + S * mul2 + mul1
        _dyfprime: uint256 = D * mul2
        if yfprime < _dyfprime:
            y = y_prev / 2
            continue
        else:
            yfprime -= _dyfprime
        fprime: uint256 = yfprime / y

        # y -= f / f_prime;  y = (y * fprime - f) / fprime
        # y = (yfprime + 10**18 * D - 10**18 * S) // fprime + mul1 // fprime * (10**18 - K0) // K0
        y_minus: uint256 = mul1 / fprime
        y_plus: uint256 = (yfprime + 10**18 * D) / fprime + y_minus * 10**18 / K0
        y_minus += 10**18 * S / fprime

        if y_plus < y_minus:
            y = y_prev / 2
        else:
            y = y_plus - y_minus

        diff: uint256 = 0
        if y > y_prev:
            diff = y - y_prev
        else:
            diff = y_prev - y
        if diff < max(convergence_limit, y / 10**14):
            return y

    raise "Did not converge"


@internal
@pure
def halfpow(power: uint256, precision: uint256) -> uint256:
    """
    1e18 * 0.5 ** (power/1e18)
    """
    intpow: uint256 = power / 10**18
    otherpow: uint256 = power - intpow * 10**18
    if intpow > 59:
        return 0
    result: uint256 = 10**18 / (2**intpow)

    term: uint256 = 10**18
    x: uint256 = 5 * 10**17
    S: uint256 = 10**18
    neg: bool = False

    for i in range(1, 256):
        K: uint256 = i * 10**18
        c: uint256 = K - 10**18
        if otherpow > c:
            c = otherpow - c
            neg = not neg
        else:
            c -= otherpow
        term = term * (c * x / 10**18) / K
        if neg:
            S -= term
        else:
            S += term
        if term < precision:
            return result * S / 10**18

    raise "Did not converge"


@internal
@pure
def sqrt_int(x: uint256) -> uint256:
    if x == 0:
        return 0

    z: uint256 = (x + 10**18) / 2
    y: uint256 = x

    for i in range(256):
        if z == y:
            return y
        y = z
        z = (x * 10**18 / z + z) / 2

    raise "Did not converge"

###################################
#           Actual logic          #
###################################
@internal
@view
def _fee(xp: uint256[N_COINS]) -> uint256:
    f: uint256 = self.reduction_coefficient(xp, self.fee_gamma)
    return (self.mid_fee * f + self.out_fee * (10**18 - f)) / 10**18


@external
@view
def fee() -> uint256:
    return self._fee(self.xp())


@internal
@view
def get_xcp(_D: uint256 = 0) -> uint256:
    D: uint256 = _D
    if D == 0:
        D = self.D
    x: uint256[N_COINS] = empty(uint256[N_COINS])
    x[0] = D / N_COINS
    for i in range(N_COINS-1):
        x[i+1] = D * 10**18 / (N_COINS * self.price_oracle[i])
    return self.geometric_mean(x)


@external
@view
def get_virtual_price() -> uint256:
    # XXX save virtual price at the very first liquidity deposit
    # and divide by it here to have virtual_price starting from 1.0
    return self.get_xcp() * 10**18 / CurveToken(self.token).totalSupply()


@internal
def update_xcp(only_real: bool = False):
    xcp: uint256 = self.get_xcp()
    old_xcp: uint256 = self.xcp
    self.xcp_profit_real = self.xcp_profit_real * xcp / old_xcp
    if not only_real:
        self.xcp_profit = self.xcp_profit * xcp / old_xcp
    self.xcp = xcp


@internal
def tweak_price(A: uint256, gamma: uint256, _xp: uint256[N_COINS], i: uint256, dx: uint256, j: uint256, dy: uint256):
    """
    dx of coin i -> dy of coin j

    TODO: this can be compressed by having each number being 128 bits
    """
    # Update MA if needed
    price_oracle: uint256[N_COINS-1] = self.price_oracle
    last_prices_timestamp: uint256 = self.last_prices_timestamp
    last_prices: uint256[N_COINS-1] = self.last_prices
    if last_prices_timestamp < block.timestamp:
        # MA update required
        ma_half_time: uint256 = self.ma_half_time
        alpha: uint256 = self.halfpow((block.timestamp - last_prices_timestamp) * 10**18 / ma_half_time, 10**10)
        for k in range(N_COINS-1):
            price_oracle[k] = (last_prices[k] * (10**18 - alpha) + price_oracle[k] * alpha) / 10**18
        self.price_oracle = price_oracle
        self.last_prices_timestamp = block.timestamp

    # We will need this a few times (35k gas)
    D_unadjusted: uint256 = self.newton_D(A, gamma, _xp)
    price_scale: uint256[N_COINS-1] = self.price_scale

    if i > 0 or j > 0:
        # Save the last price
        p: uint256 = 0
        ix: uint256 = j
        if i != 0 and j != 0:
            p = last_prices[i-1] * dx / dy
        elif i == 0:
            p = dx * 10**18 / dy
        else:  # j == 0
            p = dy * 10**18 / dx
            ix = i
        self.last_prices[ix-1] = p
    else:
        # calculate real prices
        # it would cost 70k gas for a 3-token pool. Sad. How do we do better?
        __xp: uint256[N_COINS] = _xp
        __xp[0] += 10**18
        for k in range(N_COINS-1):
            self.last_prices[k] = price_scale[k] * 10**18 / (_xp[k+1] - self.newton_y(A, gamma, __xp, D_unadjusted, k+1))

    norm: uint256 = 0
    old_xcp_profit: uint256 = self.xcp_profit
    old_xcp_profit_real: uint256 = self.xcp_profit_real
    for k in range(N_COINS-1):
        ratio: uint256 = price_oracle[k] * 10**18 / price_scale[k]
        if ratio > 10**18:
            ratio -= 10**18
        else:
            ratio = 10**18 - ratio
        norm += ratio**2


    # Update profit numbers without price adjustment first
    # XXX should we leave it like this or call get_xcp?
    xp: uint256[N_COINS] = empty(uint256[N_COINS])
    xp[0] = D_unadjusted / N_COINS
    for k in range(N_COINS-1):
        xp[k+1] = D_unadjusted * 10**18 / (N_COINS * price_scale[k])
    old_xcp: uint256 = self.xcp
    xcp: uint256 = self.geometric_mean(xp)
    xcp_profit_real: uint256 = old_xcp_profit_real * xcp / old_xcp
    xcp_profit: uint256 = old_xcp_profit * xcp / old_xcp
    self.xcp_profit = xcp_profit

    # Mint admin fees
    frac: uint256 = (10**18 * xcp / old_xcp - 10**18) * self.admin_fee / (2 * 10**10)
    # /2 here is because half of the fee usually goes for retargeting the price
    if frac > 0:
        assert CurveToken(self.token).mint_relative(self.owner, frac)

    # self.price_threshold must be > self.adjustment_step
    # should we pause for a bit if profit wasn't enough to not spend this gas every time?
    if norm > self.price_threshold ** 2:
        norm = self.sqrt_int(norm)
        adjustment_step: uint256 = self.adjustment_step

        p_new: uint256[N_COINS-1] = empty(uint256[N_COINS-1])
        for k in range(N_COINS-1):
            p_new[k] = (price_scale[k] * (norm - adjustment_step) + adjustment_step * price_oracle[k]) / norm

        # Calculate balances*prices
        xp = _xp
        for k in range(N_COINS-1):
            xp[k+1] = _xp[k+1] * p_new[k] / price_scale[k]

        # Calculate "extended constant product" invariant xCP
        D: uint256 = self.newton_D(A, gamma, xp)
        xp[0] = D / N_COINS
        for k in range(N_COINS-1):
            xp[k+1] = D * 10**18 / (N_COINS * p_new[k])
        xcp = self.geometric_mean(xp)
        old_xcp_profit_real = old_xcp_profit_real * xcp / old_xcp  # Just reusing a variable here: it's not old anymore

        # Proceed if we've got enough profit
        if 2 * (old_xcp_profit_real - 10**18) > xcp_profit - 10**18:
            self.price_scale = p_new
            self.D = D
            self.xcp_profit_real = old_xcp_profit_real
            return

        # else - make a delay?

    # If we are here, the price_scale adjustment did not happen
    # Still need to update the profit counter and D
    self.D = D_unadjusted
    self.xcp_profit_real = xcp_profit_real


@external
@nonreentrant('lock')
def exchange(i: uint256, j: uint256, dx: uint256, min_dy: uint256):
    assert not self.is_killed  # dev: the pool is killed
    assert i != j and i < N_COINS and j < N_COINS

    input_coin: address = self.coins[i]
    assert ERC20(input_coin).transferFrom(msg.sender, self, dx)

    price_scale: uint256[N_COINS-1] = self.price_scale
    xp: uint256[N_COINS] = self.balances
    y0: uint256 = xp[j]
    xp[i] += dx
    for k in range(N_COINS-1):
        xp[k+1] = xp[k+1] * price_scale[k] / PRECISION

    A: uint256 = self.A_precise
    gamma: uint256 = self.gamma

    y: uint256 = self.newton_y(A, gamma, xp, self.D, j)
    dy: uint256 = xp[j] - y - 1
    xp[j] = y
    if j > 0:
        dy = dy * PRECISION / price_scale[j-1]
    dy -= self._fee(xp) * dy / 10**10
    assert dy >= min_dy, "Exchange resulted in fewer coins than expected"

    self.balances[j] = y0 - dy
    output_coin: address = self.coins[j]
    assert ERC20(output_coin).transfer(msg.sender, dy)

    if j == 0:
        xp[0] = y0 - dy
    else:
        xp[j] = (y0 - dy) * price_scale[j-1] / PRECISION
    self.tweak_price(A, gamma, xp, i, dx, j, dy)

    log TokenExchange(msg.sender, i, dx, j, dy)


@external
@view
def get_dy(i: uint256, j: uint256, dx: uint256) -> uint256:
    assert i != j and i < N_COINS and j < N_COINS

    price_scale: uint256[N_COINS-1] = self.price_scale
    xp: uint256[N_COINS] = self.balances
    y0: uint256 = xp[j]
    xp[i] += dx
    for k in range(N_COINS-1):
        xp[k+1] = xp[k+1] * price_scale[k] / PRECISION

    A: uint256 = self.A_precise
    gamma: uint256 = self.gamma

    y: uint256 = self.newton_y(A, gamma, xp, self.D, j)
    dy: uint256 = xp[j] - y - 1
    xp[j] = y
    if j > 0:
        dy = dy * PRECISION / price_scale[j-1]
    dy -= self._fee(xp) * dy / 10**10

    return dy


@external
@nonreentrant('lock')
def add_liquidity(amounts: uint256[N_COINS], min_mint_amount: uint256):
    assert not self.is_killed  # dev: the pool is killed

    for i in range(N_COINS):
        assert ERC20(self.coins[i]).transferFrom(msg.sender, self, amounts[i])

    price_scale: uint256[N_COINS-1] = self.price_scale
    xp: uint256[N_COINS] = self.balances
    xp[0] += amounts[0]
    for i in range(N_COINS-1):
        xp[i+1] = (xp[i+1] + amounts[i+1]) * price_scale[i] / PRECISION
    A: uint256 = self.A_precise
    gamma: uint256 = self.gamma
    token: address = self.token

    xcp_0: uint256 = self.get_xcp()
    D: uint256 = self.newton_D(A, gamma, xp)
    xcp: uint256 = self.get_xcp(D)

    token_supply: uint256 = CurveToken(token).totalSupply()
    d_token: uint256 = token_supply * xcp / xcp_0
    assert d_token > 0  # dev: nothing minted
    d_token_fee: uint256 = self._fee(xp) * d_token / (2 * 10**10) + 1  # /2 because it's half a trade
    d_token -= d_token_fee
    assert d_token >= min_mint_amount, "Slippage screwed you"

    assert CurveToken(token).mint(msg.sender, d_token)
    assert CurveToken(token).mint(self.owner, d_token_fee * self.admin_fee / (2 * 10**10))  # /2 b/c price retarget

    self.tweak_price(A, gamma, xp, 0, 0, 0, 0)

    log AddLiquidity(msg.sender, amounts, d_token_fee, token_supply)

@external
@nonreentrant('lock')
def remove_liquidity(_amount: uint256, min_amounts: uint256[N_COINS]):
    pass


@view
@external
def calc_token_amount(amounts: uint256[N_COINS], deposit: bool) -> uint256:
    return 0


@view
@external
def calc_withdraw_one_coin(_token_amount: uint256, i: int128) -> uint256:
    return 0


@external
@nonreentrant('lock')
def remove_liquidity_one_coin(_token_amount: uint256, i: int128, min_amount: uint256):
    pass
