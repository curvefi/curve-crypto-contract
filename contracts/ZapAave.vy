# @version 0.2.12

from vyper.interfaces import ERC20

interface CurveCryptoSwap:
    def token() -> address: view
    def coins(i: uint256) -> address: view
    def add_liquidity(amounts: uint256[N_COINS], min_mint_amount: uint256, receiver: address): nonpayable
    def exchange(i: uint256, j: uint256, dx: uint256, min_dy: uint256): nonpayable
    def remove_liquidity(amount: uint256, min_amounts: uint256[N_COINS]): nonpayable
    def remove_liquidity_one_coin(token_amount: uint256, i: uint256, min_amount: uint256): nonpayable

interface LendingPool:
    def withdraw(underlying_asset: address, amount: uint256, receiver: address): nonpayable

interface aToken:
    def UNDERLYING_ASSET_ADDRESS() -> address: view


N_COINS: constant(int128) = 3
AAVE_LENDING_POOL: constant(address) = 0x8dFf5E27EA6b7AC08EbFdf9eB090F32ee9a30fcf

aave_referral: uint256
coins: public(address[N_COINS])
underlying_coins: public(address[N_COINS])

pool: public(address)
token: public(address)


@external
def __init__(_pool: address):
    self.pool = _pool
    self.token = CurveCryptoSwap(_pool).token()
    for i in range(N_COINS):
        coin: address = CurveCryptoSwap(_pool).coins(i)
        self.coins[i] = coin
        coin = aToken(coin).UNDERLYING_ASSET_ADDRESS()
        self.underlying_coins[i] = coin
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
def add_liquidity(_amounts: uint256[N_COINS], _min_mint_amount: uint256, _receiver: address = msg.sender):
     # Take coins from the sender
    aave_referral: bytes32 = convert(self.aave_referral, bytes32)

    # Take coins from the sender
    for i in range(N_COINS):
        amount: uint256 = _amounts[i]
        if amount != 0:
            coin: address = self.coins[i]
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

    CurveCryptoSwap(self.pool).add_liquidity(_amounts, _min_mint_amount, _receiver)


@external
def exchange_underlying(i: uint256, j: uint256, dx: uint256, min_dy: uint256, receiver: address):
    coin: address = self.coins[i]
    # transfer underlying coin from msg.sender to self
    _response: Bytes[32] = raw_call(
        coin,
        concat(
            method_id("transferFrom(address,address,uint256)"),
            convert(msg.sender, bytes32),
            convert(self, bytes32),
            convert(dx, bytes32)
        ),
        max_outsize=32
    )
    if len(_response) != 0:
        assert convert(_response, bool)

    # deposit `i` to aave lending pool
    raw_call(
        AAVE_LENDING_POOL,
        concat(
            method_id("deposit(address,uint256,address,uint16)"),
            convert(coin, bytes32),
            convert(dx, bytes32),
            convert(self, bytes32),
            convert(self.aave_referral, bytes32),
        )
    )

    CurveCryptoSwap(self.pool).exchange(i, j, dx, min_dy)
    amount: uint256 = ERC20(self.coins[j]).balanceOf(self)

    # withdraw `j` underlying from lending pool and transfer to caller
    LendingPool(AAVE_LENDING_POOL).withdraw(self.underlying_coins[j], amount, receiver)


@external
def remove_liquidity(_amount: uint256, _min_amounts: uint256[N_COINS], _receiver: address):
    ERC20(self.token).transferFrom(msg.sender, self, _amount)
    CurveCryptoSwap(self.pool).remove_liquidity(_amount, _min_amounts)

    for i in range(N_COINS):
        value: uint256 = ERC20(self.coins[i]).balanceOf(self)
        LendingPool(AAVE_LENDING_POOL).withdraw(self.underlying_coins[i], value, _receiver)


@external
def remove_liquidity_one_coin(_token_amount: uint256, i: uint256, _min_amount: uint256, _receiver: address):
    ERC20(self.token).transferFrom(msg.sender, self, _token_amount)
    CurveCryptoSwap(self.pool).remove_liquidity_one_coin(_token_amount, i, _min_amount)

    value: uint256 = ERC20(self.coins[i]).balanceOf(self)
    LendingPool(AAVE_LENDING_POOL).withdraw(self.underlying_coins[i], value, _receiver)
