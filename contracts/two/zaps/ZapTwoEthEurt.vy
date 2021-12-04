# @version 0.3.1
# EUR/3crv pool where 3crv is _second_, not first

from vyper.interfaces import ERC20

interface CurveCryptoSwap:
    def token() -> address: view
    def coins(i: uint256) -> address: view
    def get_dy(i: uint256, j: uint256, dx: uint256) -> uint256: view
    def calc_token_amount(amounts: uint256[N_COINS]) -> uint256: view
    def calc_withdraw_one_coin(token_amount: uint256, i: uint256) -> uint256: view
    def add_liquidity(amounts: uint256[N_COINS], min_mint_amount: uint256) -> uint256: nonpayable
    def exchange(i: uint256, j: uint256, dx: uint256, min_dy: uint256) -> uint256: nonpayable
    def remove_liquidity(amount: uint256, min_amounts: uint256[N_COINS]): nonpayable
    def remove_liquidity_one_coin(token_amount: uint256, i: uint256, min_amount: uint256) -> uint256: nonpayable
    def price_oracle() -> uint256: view
    def price_scale() -> uint256: view

interface StableSwap:
    def coins(i: uint256) -> address: view
    def get_dy(i: int128, j: int128, dx: uint256) -> uint256: view
    def calc_token_amount(amounts: uint256[N_STABLECOINS], is_deposit: bool) -> uint256: view
    def calc_withdraw_one_coin(token_amount: uint256, i: int128) -> uint256: view
    def add_liquidity(amounts: uint256[N_STABLECOINS], min_mint_amount: uint256): nonpayable
    def remove_liquidity_one_coin(token_amount: uint256, i: int128, min_amount: uint256): nonpayable
    def remove_liquidity(amount: uint256, min_amounts: uint256[N_STABLECOINS]): nonpayable
    def get_virtual_price() -> uint256: view


N_COINS: constant(int128) = 2
N_STABLECOINS: constant(int128) = 3
N_UL_COINS: constant(int128) = N_COINS + N_STABLECOINS - 1

# All the following properties can be replaced with constants for gas efficiency

COINS: constant(address[N_COINS]) = [
    0xC581b735A1688071A1746c968e0798D642EDE491,  # EURT
    0x6c3F90f043a72FA612cbac8115EE7e52BDe6E490   # 3crv
]
UNDERLYING_COINS: constant(address[N_UL_COINS]) = [
    0xC581b735A1688071A1746c968e0798D642EDE491,  # EURT
    0x6B175474E89094C44Da98b954EedeAC495271d0F,  # DAI
    0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48,  # USDC
    0xdAC17F958D2ee523a2206206994597C13D831ec7   # USDT
]
POOL: constant(address) = 0x0000000000000000000000000000000000000000  # To replace
BASE_POOL: constant(address) = 0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7
TOKEN: constant(address) = 0x0000000000000000000000000000000000000001  # To replace


@external
def __init__():
    for coin in UNDERLYING_COINS:
        response: Bytes[32] = raw_call(
            coin,
            concat(
                method_id("approve(address,uint256)"),
                convert(BASE_POOL, bytes32),
                convert(MAX_UINT256, bytes32)
            ),
            max_outsize=32
        )
        if len(response) != 0:
            assert convert(response, bool)

    for coin in COINS:
        response: Bytes[32] = raw_call(
            coin,
            concat(
                method_id("approve(address,uint256)"),
                convert(POOL, bytes32),
                convert(MAX_UINT256, bytes32)
            ),
            max_outsize=32
        )
        if len(response) != 0:
            assert convert(response, bool)


@external
@view
def coins(i: uint256) -> address:
    _coins: address[N_COINS] = COINS
    return _coins[i]


@external
@view
def underlying_coins(i: uint256) -> address:
    _ucoins: address[N_UL_COINS] = UNDERLYING_COINS
    return _ucoins[i]


@external
@view
def pool() -> address:
    return POOL


@external
@view
def base_pool() -> address:
    return BASE_POOL


@external
@view
def token() -> address:
    return TOKEN


@external
@view
def price_oracle() -> uint256:
    usd_eur: uint256 = CurveCryptoSwap(POOL).price_oracle()
    vprice: uint256 = StableSwap(BASE_POOL).get_virtual_price()
    return vprice * 10**18 / usd_eur


@external
@view
def price_scale() -> uint256:
    usd_eur: uint256 = CurveCryptoSwap(POOL).price_scale()
    vprice: uint256 = StableSwap(BASE_POOL).get_virtual_price()
    return vprice * 10**18 / usd_eur


@external
def add_liquidity(_amounts: uint256[N_UL_COINS], _min_mint_amount: uint256, _receiver: address = msg.sender):
    base_deposit_amounts: uint256[N_STABLECOINS] = empty(uint256[N_STABLECOINS])
    deposit_amounts: uint256[N_COINS] = empty(uint256[N_COINS])
    is_base_deposit: bool = False
    coins: address[N_COINS] = COINS
    underlying_coins: address[N_UL_COINS] = UNDERLYING_COINS

    # transfer base pool coins from caller and deposit to get LP tokens
    for i in range(N_UL_COINS - N_STABLECOINS, N_UL_COINS):
        amount: uint256 = _amounts[i]
        if amount != 0:
            coin: address = underlying_coins[i]
            # transfer underlying coin from msg.sender to self
            _response: Bytes[32] = raw_call(
                coin,
                concat(
                    method_id("transferFrom(address,address,uint256)"),
                    convert(msg.sender, bytes32),
                    convert(self, bytes32),
                    convert(amount, bytes32)
                ),
                max_outsize=32
            )
            if len(_response) != 0:
                assert convert(_response, bool)
            base_deposit_amounts[i - (N_COINS - 1)] = ERC20(coin).balanceOf(self)
            is_base_deposit = True

    if is_base_deposit:
        StableSwap(BASE_POOL).add_liquidity(base_deposit_amounts, 0)
        deposit_amounts[N_COINS - 1] = ERC20(coins[N_COINS-1]).balanceOf(self)

    # transfer remaining underlying coins
    for i in range(N_COINS - 1):
        amount: uint256 = _amounts[i]
        if amount != 0:
            coin: address = underlying_coins[i]
            # transfer underlying coin from msg.sender to self
            _response: Bytes[32] = raw_call(
                coin,
                concat(
                    method_id("transferFrom(address,address,uint256)"),
                    convert(msg.sender, bytes32),
                    convert(self, bytes32),
                    convert(amount, bytes32)
                ),
                max_outsize=32
            )
            if len(_response) != 0:
                assert convert(_response, bool)

            deposit_amounts[i] = amount

    amount: uint256 = CurveCryptoSwap(POOL).add_liquidity(deposit_amounts, _min_mint_amount)
    ERC20(TOKEN).transfer(_receiver, amount)


@external
def exchange_underlying(i: uint256, j: uint256, _dx: uint256, _min_dy: uint256, _receiver: address = msg.sender) -> uint256:
    assert i != j  # dev: coins must be different
    coins: address[N_COINS] = COINS
    underlying_coins: address[N_UL_COINS] = UNDERLYING_COINS

    # transfer `i` from caller into the zap
    response: Bytes[32] = raw_call(
        underlying_coins[i],
        concat(
            method_id("transferFrom(address,address,uint256)"),
            convert(msg.sender, bytes32),
            convert(self, bytes32),
            convert(_dx, bytes32)
        ),
        max_outsize=32
    )
    if len(response) != 0:
        assert convert(response, bool)

    dx: uint256 = _dx
    outer_i: uint256 = min(i, N_COINS - 1)
    outer_j: uint256 = min(j, N_COINS - 1)

    if i >= N_COINS - 1:
        # if `i` is in the base pool, deposit to get LP tokens
        base_deposit_amounts: uint256[N_STABLECOINS] = empty(uint256[N_STABLECOINS])
        base_deposit_amounts[i - (N_COINS - 1)] = dx
        StableSwap(BASE_POOL).add_liquidity(base_deposit_amounts, 0)
        dx = ERC20(coins[N_COINS-1]).balanceOf(self)

    # perform the exchange
    amount: uint256 = dx
    if outer_i != outer_j:
        amount = CurveCryptoSwap(POOL).exchange(outer_i, outer_j, dx, 0)

    if outer_j == N_COINS - 1:
        # if `j` is in the base pool, withdraw the desired underlying asset and transfer to caller
        StableSwap(BASE_POOL).remove_liquidity_one_coin(amount, convert(j - (N_COINS - 1), int128), _min_dy)
        amount = ERC20(underlying_coins[j]).balanceOf(self)
    else:
        # withdraw `j` underlying from lending pool and transfer to caller
        assert amount >= _min_dy

    response = raw_call(
        underlying_coins[j],
        concat(
            method_id("transfer(address,uint256)"),
            convert(_receiver, bytes32),
            convert(amount, bytes32)
        ),
        max_outsize=32
    )
    if len(response) != 0:
        assert convert(response, bool)

    return amount


@external
def remove_liquidity(_amount: uint256, _min_amounts: uint256[N_UL_COINS], _receiver: address = msg.sender):
    underlying_coins: address[N_UL_COINS] = UNDERLYING_COINS

    # transfer LP token from caller and remove liquidity
    ERC20(TOKEN).transferFrom(msg.sender, self, _amount)
    min_amounts: uint256[N_COINS] = [_min_amounts[0], 0]
    CurveCryptoSwap(POOL).remove_liquidity(_amount, min_amounts)

    # withdraw from base pool and transfer underlying assets to receiver
    value: uint256 = ERC20(COINS[1]).balanceOf(self)
    base_min_amounts: uint256[N_STABLECOINS] = [_min_amounts[1], _min_amounts[2], _min_amounts[3]]
    StableSwap(BASE_POOL).remove_liquidity(value, base_min_amounts)
    for i in range(N_UL_COINS):
        value = ERC20(underlying_coins[i]).balanceOf(self)
        response: Bytes[32] = raw_call(
            underlying_coins[i],
            concat(
                method_id("transfer(address,uint256)"),
                convert(_receiver, bytes32),
                convert(value, bytes32)
            ),
            max_outsize=32
        )
        if len(response) != 0:
            assert convert(response, bool)


@external
def remove_liquidity_one_coin(_token_amount: uint256, i: uint256, _min_amount: uint256, _receiver: address = msg.sender):
    underlying_coins: address[N_UL_COINS] = UNDERLYING_COINS

    ERC20(TOKEN).transferFrom(msg.sender, self, _token_amount)
    outer_i: uint256 = min(i, N_COINS - 1)
    value: uint256 = CurveCryptoSwap(POOL).remove_liquidity_one_coin(_token_amount, outer_i, 0)

    if outer_i == N_COINS - 1:
        StableSwap(BASE_POOL).remove_liquidity_one_coin(value, convert(i - (N_COINS - 1), int128), _min_amount)
        value = ERC20(underlying_coins[i]).balanceOf(self)
    else:
        assert value >= _min_amount
    response: Bytes[32] = raw_call(
        underlying_coins[i],
        concat(
            method_id("transfer(address,uint256)"),
            convert(_receiver, bytes32),
            convert(value, bytes32)
        ),
        max_outsize=32
    )
    if len(response) != 0:
        assert convert(response, bool)


@view
@external
def get_dy_underlying(i: uint256, j: uint256, _dx: uint256) -> uint256:
    if min(i, j) >= N_COINS - 1:
        return StableSwap(BASE_POOL).get_dy(convert(i - (N_COINS-1), int128), convert(j - (N_COINS-1), int128), _dx)

    dx: uint256 = _dx
    outer_i: uint256 = min(i, N_COINS - 1)
    outer_j: uint256 = min(j, N_COINS - 1)

    if outer_i == N_COINS-1:
        amounts: uint256[N_STABLECOINS] = empty(uint256[N_STABLECOINS])
        amounts[i - (N_COINS-1)] = dx
        dx = StableSwap(BASE_POOL).calc_token_amount(amounts, True)

    dy: uint256 = CurveCryptoSwap(POOL).get_dy(outer_i, outer_j, dx)
    if outer_j == N_COINS-1:
        return StableSwap(BASE_POOL).calc_withdraw_one_coin(dy, convert(j - (N_COINS-1), int128))
    else:
        return dy


@view
@external
def calc_token_amount(_amounts: uint256[N_UL_COINS]) -> uint256:
    base_amounts: uint256[N_STABLECOINS] = [_amounts[1], _amounts[2], _amounts[3]]
    base_lp: uint256 = 0
    if _amounts[1] + _amounts[2] + _amounts[3] > 0:
        base_lp = StableSwap(BASE_POOL).calc_token_amount(base_amounts, True)
    amounts: uint256[N_COINS] = [_amounts[0], base_lp]
    return CurveCryptoSwap(POOL).calc_token_amount(amounts)


@view
@external
def calc_withdraw_one_coin(token_amount: uint256, i: uint256) -> uint256:
    if i < N_COINS-1:
        return CurveCryptoSwap(POOL).calc_withdraw_one_coin(token_amount, i)

    base_amount: uint256 = CurveCryptoSwap(POOL).calc_withdraw_one_coin(token_amount, N_COINS-1)
    return StableSwap(BASE_POOL).calc_withdraw_one_coin(base_amount, convert(i - (N_COINS-1), int128))
