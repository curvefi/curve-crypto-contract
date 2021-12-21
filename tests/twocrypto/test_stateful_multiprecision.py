import pytest
from .test_stateful import NumbaGoUp
from .conftest import _crypto_swap_with_deposit

COINS = [
    ('USDC', 6),
    ('EURX', 18)]

INITIAL_PRICES = [int(1.2 * 10**18)]

MAX_SAMPLES = 20
MAX_COUNT = 20


# Fixtures
@pytest.fixture(scope="module", autouse=True)
def coins_mp(ERC20Mock, accounts):
    yield [ERC20Mock.deploy(name, name, decimals, {"from": accounts[0]})
           for name, decimals in COINS]


@pytest.fixture(scope="module", autouse=True)
def token_mp(CurveTokenV5, accounts):
    yield CurveTokenV5.deploy("Curve USD-EUR", "crvUSDEUR", {"from": accounts[0]})


@pytest.fixture(scope="module", autouse=True)
def crypto_swap_mp(CurveCryptoSwap2, token_mp, coins_mp, accounts):
    swap = CurveCryptoSwap2.deploy(
            accounts[0],
            accounts[0],
            90 * 2**2 * 10000,  # A
            int(2.8e-4 * 1e18),  # gamma
            int(8.5e-5 * 1e10),  # mid_fee
            int(1.3e-3 * 1e10),  # out_fee
            10**10,  # allowed_extra_profit
            int(0.012 * 1e18),  # fee_gamma
            int(0.55e-5 * 1e18),  # adjustment_step
            0,  # admin_fee
            600,  # ma_half_time
            INITIAL_PRICES[0],
            token_mp,
            coins_mp,
            {'from': accounts[0]})
    token_mp.set_minter(swap, {"from": accounts[0]})
    return swap


@pytest.fixture(scope="module")
def crypto_swap_with_deposit_mp(crypto_swap_mp, coins_mp, accounts):
    return _crypto_swap_with_deposit(crypto_swap_mp, coins_mp, accounts)


class Multiprecision(NumbaGoUp):
    def rule_exchange(self, exchange_amount_in, exchange_i, user):
        exchange_amount_in = exchange_amount_in // 10**(18-self.decimals[exchange_i])
        super().rule_exchange(exchange_amount_in, exchange_i, user)


def test_multiprecision(crypto_swap_mp, token_mp, chain, accounts, coins_mp, state_machine):
    from hypothesis._settings import HealthCheck

    state_machine(Multiprecision, chain, accounts, coins_mp, crypto_swap_mp, token_mp,
                  settings={'max_examples': MAX_SAMPLES, 'stateful_step_count': MAX_COUNT, 'suppress_health_check': HealthCheck.all()})
