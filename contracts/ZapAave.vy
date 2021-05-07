# @version 0.2.12

from vyper.interfaces import ERC20

interface CurveCryptoSwap:
    def token() -> address: view
    def coins(i: uint256) -> address: view
    def add_liquidity(amounts: uint256[N_COINS], min_mint_amount: uint256, receiver: address): nonpayable
    def exchange(i: uint256, j: uint256, dx: uint256, min_dy: uint256): nonpayable
    def remove_liquidity(amount: uint256, min_amounts: uint256[N_COINS]): nonpayable
    def remove_liquidity_one_coin(token_amount: uint256, i: uint256, min_amount: uint256): nonpayable

interface StableSwap:
    def coins(i: uint256) -> address: view
    def add_liquidity(amounts: uint256[N_COINS], min_mint_amount: uint256, use_underlying: bool) -> uint256: nonpayable
    def remove_liquidity_one_coin(token_amount: uint256, i: uint256, min_amount: uint256, use_underlying: bool) -> uint256: nonpayable
    def remove_liquidity(amount: uint256, min_amounts: uint256[N_COINS], use_underlying: bool) -> uint256[N_COINS]: nonpayable

interface LendingPool:
    def withdraw(underlying_asset: address, amount: uint256, receiver: address): nonpayable

interface aToken:
    def UNDERLYING_ASSET_ADDRESS() -> address: view


N_COINS: constant(int128) = 3
N_UL_COINS: constant(int128) = 5
AAVE_LENDING_POOL: constant(address) = 0x8dFf5E27EA6b7AC08EbFdf9eB090F32ee9a30fcf

aave_referral: uint256
coins: public(address[N_COINS])
underlying_coins: public(address[N_UL_COINS])

pool: public(address)
base_pool: public(address)
token: public(address)


@external
def __init__(_pool: address, _base_pool: address):
    self.pool = _pool
    self.base_pool = _base_pool
    self.token = CurveCryptoSwap(_pool).token()

    for i in range(N_COINS):
        coin: address = StableSwap(_base_pool).coins(i)
        self.underlying_coins[i] = coin
        # approve transfer of underlying coin to base pool
        _response: Bytes[32] = raw_call(
            coin,
            concat(
                method_id("approve(address,uint256)"),
                convert(_base_pool, bytes32),
                convert(MAX_UINT256, bytes32)
            ),
            max_outsize=32
        )
        if len(_response) != 0:
            assert convert(_response, bool)


    for i in range(N_COINS):
        coin: address = CurveCryptoSwap(_pool).coins(i)
        self.coins[i] = coin
        coin = aToken(coin).UNDERLYING_ASSET_ADDRESS()
        self.underlying_coins[i+(N_COINS-1)] = coin
        # approve transfer of underlying coin to aave lending pool
        _response: Bytes[32] = raw_call(
            coin,
            concat(
                method_id("approve(address,uint256)"),
                convert(AAVE_LENDING_POOL, bytes32),
                convert(MAX_UINT256, bytes32)
            ),
            max_outsize=32
        )
        if len(_response) != 0:
            assert convert(_response, bool)


@external
def add_liquidity(_amounts: uint256[N_UL_COINS], _min_mint_amount: uint256, _receiver: address = msg.sender):
    deposit_amounts: uint256[3] = empty(uint256[3])

    # transfer base pool coins from caller and deposit to get LP tokens
    for i in range(N_COINS):
        amount: uint256 = _amounts[i]
        if amount != 0:
            coin: address = self.underlying_coins[i]
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
            deposit_amounts[i] = ERC20(coin).balanceOf(self)

    if deposit_amounts != empty(uint256[3]):
        deposit_amounts = [StableSwap(self.base_pool).add_liquidity(deposit_amounts, 0, True), 0, 0]

    # transfer remaining underlying coins and deposit into aave
    aave_referral: bytes32 = convert(self.aave_referral, bytes32)
    for i in range(N_COINS, N_UL_COINS):
        amount: uint256 = _amounts[i]
        if amount != 0:
            coin: address = self.underlying_coins[i]
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

            # deposit to aave lending pool
            raw_call(
                AAVE_LENDING_POOL,
                concat(
                    method_id("deposit(address,uint256,address,uint16)"),
                    convert(coin, bytes32),
                    convert(amount, bytes32),
                    convert(self, bytes32),
                    aave_referral,
                )
            )
            deposit_amounts[i-(N_COINS-1)] = amount

    CurveCryptoSwap(self.pool).add_liquidity(deposit_amounts, _min_mint_amount, _receiver)


@external
def exchange_underlying(i: uint256, j: uint256, _dx: uint256, _min_dy: uint256, _receiver: address):
    # transfer `i` from caller into the zap
    response: Bytes[32] = raw_call(
        self.underlying_coins[i],
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
    base_i: uint256 = 0
    base_j: uint256 = 0
    if j < N_COINS:
        base_j = 0
    else:
        base_j = j - (N_COINS - 1)

    if i < N_COINS:
        # if `i` is in the base pool, deposit to get LP tokens
        base_i = 0
        deposit_amounts: uint256[N_COINS] = empty(uint256[N_COINS])
        deposit_amounts[i] = dx
        dx = StableSwap(self.base_pool).add_liquidity(deposit_amounts, 0, True)
    else:
        # if `i` is an aToken, deposit to the aave lending pool
        base_i = i - (N_COINS - 1)
        raw_call(
            AAVE_LENDING_POOL,
            concat(
                method_id("deposit(address,uint256,address,uint16)"),
                convert(self.underlying_coins[i], bytes32),
                convert(dx, bytes32),
                convert(self, bytes32),
                convert(self.aave_referral, bytes32),
            )
        )

    # perform the exchange
    CurveCryptoSwap(self.pool).exchange(base_i, base_j, dx, 0)
    amount: uint256 = ERC20(self.coins[j]).balanceOf(self)

    if base_j == 0:
        # if `j` is in the base pool, withdraw the desired underlying asset and transfer to caller
        amount = StableSwap(self.base_pool).remove_liquidity_one_coin(amount, j, _min_dy, True)
        response = raw_call(
            self.underlying_coins[j],
            concat(
                method_id("transfer(address,uint256)"),
                convert(msg.sender, bytes32),
                convert(amount, bytes32)
            ),
            max_outsize=32
        )
        if len(response) != 0:
            assert convert(response, bool)
    else:
        # withdraw `j` underlying from lending pool and transfer to caller
        assert amount >= _min_dy
        LendingPool(AAVE_LENDING_POOL).withdraw(self.underlying_coins[j], amount, _receiver)


@external
def remove_liquidity(_amount: uint256, _min_amounts: uint256[N_UL_COINS], _receiver: address):
    # transfer LP token from caller and remove liquidity
    ERC20(self.token).transferFrom(msg.sender, self, _amount)
    CurveCryptoSwap(self.pool).remove_liquidity(_amount, [0, _min_amounts[3], _min_amounts[4]])

    # withdraw from base pool and transfer underlying assets to receiver
    value: uint256 = ERC20(self.coins[0]).balanceOf(self)
    received: uint256[N_COINS] = StableSwap(self.base_pool).remove_liquidity(value, [_min_amounts[0], _min_amounts[1], _min_amounts[2]], True)
    for i in range(N_COINS):
        response: Bytes[32] = raw_call(
            self.underlying_coins[i],
            concat(
                method_id("transfer(address,uint256)"),
                convert(_receiver, bytes32),
                convert(received[i], bytes32)
            ),
            max_outsize=32
        )
        if len(response) != 0:
            assert convert(response, bool)

    # withdraw from aave lending pool and transfer to receiver
    for i in range(N_COINS, N_UL_COINS):
        value = ERC20(self.coins[i-(N_COINS-1)]).balanceOf(self)
        LendingPool(AAVE_LENDING_POOL).withdraw(self.underlying_coins[i], value, _receiver)


@external
def remove_liquidity_one_coin(_token_amount: uint256, i: uint256, _min_amount: uint256, _receiver: address):
    ERC20(self.token).transferFrom(msg.sender, self, _token_amount)
    base_i: uint256 = 0
    if i >= N_COINS:
        base_i = i - (N_COINS-1)
    CurveCryptoSwap(self.pool).remove_liquidity_one_coin(_token_amount, i, 0)

    value: uint256 = ERC20(self.coins[base_i]).balanceOf(self)
    if base_i == 0:
        value = StableSwap(self.base_pool).remove_liquidity_one_coin(value, i, _min_amount, True)
        response: Bytes[32] = raw_call(
            self.underlying_coins[i],
            concat(
                method_id("transfer(address,uint256)"),
                convert(msg.sender, bytes32),
                convert(value, bytes32)
            ),
            max_outsize=32
        )
        if len(response) != 0:
            assert convert(response, bool)
    else:
        assert value >= _min_amount
        LendingPool(AAVE_LENDING_POOL).withdraw(self.underlying_coins[i], value, _receiver)
