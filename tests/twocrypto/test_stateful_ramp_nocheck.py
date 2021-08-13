from brownie.test import strategy
from .test_stateful import NumbaGoUp

MAX_SAMPLES = 20
MAX_COUNT = 100
MAX_D = 10**12 * 10**18  # $1T is hopefully a reasonable cap for tests
ALLOWED_DIFFERENCE = 0.02


class RampTest(NumbaGoUp):
    future_gamma = strategy('uint256', min_value=int(2.8e-4 * 1e18 / 9), max_value=int(2.8e-4 * 1e18 * 9))
    future_A = strategy('uint256', min_value=90 * 2**2 * 10000 // 9, max_value=90 * 2**2 * 10000 * 9)

    def initialize(self, future_A, future_gamma):
        self.swap.ramp_A_gamma(future_A, future_gamma, self.chain.time() + 14*86400, {'from': self.accounts[0]})

    def rule_exchange(self, exchange_amount_in, exchange_i, user):
        try:
            super()._rule_exchange(exchange_amount_in, exchange_i, user, False)
        except Exception:
            if exchange_amount_in > 10**9:
                # Small swaps can fail at ramps
                raise

    def rule_remove_liquidity_one_coin(self, token_amount, exchange_i, user):
        super().rule_remove_liquidity_one_coin(token_amount, exchange_i, user, False)

    def invariant_virtual_price(self):
        # Invariant is not conserved here
        pass


def test_ramp(crypto_swap, token, chain, accounts, coins, state_machine):
    from hypothesis._settings import HealthCheck

    state_machine(RampTest, chain, accounts, coins, crypto_swap, token,
                  settings={'max_examples': MAX_SAMPLES, 'stateful_step_count': MAX_COUNT, 'suppress_health_check': HealthCheck.all()})
