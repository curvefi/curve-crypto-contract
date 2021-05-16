import pytest
from .test_stateful import NumbaGoUp
from .conftest import _compiled_swap, _crypto_views, _crypto_swap, _crypto_swap_with_deposit

COINS = [
    ('USDC', 6),
    ('WBTC', 8),
    ('WETH', 18)]

INITIAL_PRICES = [47500 * 10**18, 1500 * 10**18]

MAX_SAMPLES = 20
MAX_COUNT = 20


# Fixtures
@pytest.fixture(scope="module", autouse=True)
def coins_mp(ERC20Mock, accounts):
    yield [ERC20Mock.deploy(name, name, decimals, {"from": accounts[0]})
           for name, decimals in COINS]


@pytest.fixture(scope="module", autouse=True)
def token_mp(CurveTokenV4, accounts):
    yield CurveTokenV4.deploy("Curve USD-BTC-ETH", "crvUSDBTCETH", {"from": accounts[0]})


@pytest.fixture(scope="module", autouse=True)
def crypto_views_mp(CurveCryptoViews3, crypto_math, accounts, coins_mp):
    yield _crypto_views(CurveCryptoViews3, crypto_math, accounts, coins_mp)


@pytest.fixture(scope="module", autouse=True)
def compiled_swap_mp(crypto_math, token_mp, crypto_views_mp, coins_mp):
    return _compiled_swap(crypto_math, token_mp, crypto_views_mp, coins_mp)


@pytest.fixture(scope="module", autouse=True)
def crypto_swap_mp(compiled_swap_mp, token_mp, accounts):
    return _crypto_swap(compiled_swap_mp, token_mp, accounts)


@pytest.fixture(scope="module")
def crypto_swap_with_deposit_mp(crypto_swap_mp, coins_mp, accounts):
    return _crypto_swap_with_deposit(crypto_swap_mp, coins_mp, accounts)


class Multiprecision(NumbaGoUp):
    def rule_exchange(self, exchange_amount_in, exchange_i, exchange_j, user):
        exchange_amount_in = exchange_amount_in // 10**(18-self.decimals[exchange_i])
        super().rule_exchange(exchange_amount_in, exchange_i, exchange_j, user)


def test_multiprecision(crypto_swap_mp, token_mp, chain, accounts, coins_mp, state_machine):
    from hypothesis._settings import HealthCheck

    state_machine(Multiprecision, chain, accounts, coins_mp, crypto_swap_mp, token_mp,
                  settings={'max_examples': MAX_SAMPLES, 'stateful_step_count': MAX_COUNT, 'suppress_health_check': HealthCheck.all()})
