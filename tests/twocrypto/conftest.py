import pytest

INITIAL_PRICES = [int(0.8 * 10**18)]  # 1/eur


@pytest.fixture(scope="module", autouse=True)
def coins(ERC20Mock, accounts):
    yield [ERC20Mock.deploy(name, name, 18, {"from": accounts[0]})
           for name in ['USD', 'EUR']]


@pytest.fixture(scope="module", autouse=True)
def token(CurveTokenV4, accounts):
    yield CurveTokenV4.deploy("Curve EUR-USD", "crvEURUSD", {"from": accounts[0]})


@pytest.fixture(scope="module", autouse=True)
def crypto_swap(CurveCryptoSwap2, token, coins, accounts):
    swap = CurveCryptoSwap2.deploy(
            accounts[0],
            accounts[0],
            90 * 2**2 * 10000,  # A
            int(2.8e-4 * 1e18),  # gamma
            int(5e-4 * 1e10),  # mid_fee
            int(4e-3 * 1e10),  # out_fee
            10**10,  # allowed_extra_profit
            int(0.012 * 1e18),  # fee_gamma
            int(0.55e-5 * 1e18),  # adjustment_step
            0,  # admin_fee
            600,  # ma_half_time
            INITIAL_PRICES[0],
            token,
            coins,
            {'from': accounts[0]})
    token.set_minter(swap, {"from": accounts[0]})

    return swap


def _crypto_swap_with_deposit(crypto_swap, coins, accounts):
    user = accounts[1]
    quantities = [10**6 * 10**36 // p for p in [10**18] + INITIAL_PRICES]
    for coin, q in zip(coins, quantities):
        coin._mint_for_testing(user, q)
        coin.approve(crypto_swap, 2**256-1, {'from': user})

    # Very first deposit
    crypto_swap.add_liquidity(quantities, 0, {'from': user})

    return crypto_swap


@pytest.fixture(scope="module")
def crypto_swap_with_deposit(crypto_swap, coins, accounts):
    return _crypto_swap_with_deposit(crypto_swap, coins, accounts)


@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass
