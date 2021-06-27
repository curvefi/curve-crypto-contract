from brownie.test import strategy
from .test_stateful import NumbaGoUp

MAX_SAMPLES = 20
MAX_COUNT = 100
MAX_D = 10**12 * 10**18  # $1T is hopefully a reasonable cap for tests


class RampTest(NumbaGoUp):
    check_out_amount = strategy('bool')

    def setup(self, user_id=0):
        super().setup(user_id)
        new_A = self.swap.A() * 2
        new_gamma = self.swap.gamma() * 2
        self.swap.ramp_A_gamma(new_A, new_gamma, self.chain.time() + 14*86400, {'from': self.accounts[0]})

    def rule_exchange(self, exchange_amount_in, exchange_i, exchange_j, user, check_out_amount):
        if check_out_amount:
            self.swap.claim_admin_fees()
        super().rule_exchange(exchange_amount_in, exchange_i, exchange_j, user, 0.02 if check_out_amount else False)

    def rule_remove_liquidity_one_coin(self, token_amount, exchange_i, user, check_out_amount):
        if check_out_amount:
            self.swap.claim_admin_fees()
            super().rule_remove_liquidity_one_coin(token_amount, exchange_i, user, 0.02)
        else:
            super().rule_remove_liquidity_one_coin(token_amount, exchange_i, user, False)

    def invariant_virtual_price(self):
        # Invariant is not conserved here
        pass


def test_ramp(crypto_swap, token, chain, accounts, coins, state_machine):
    from hypothesis._settings import HealthCheck

    state_machine(RampTest, chain, accounts, coins, crypto_swap, token,
                  settings={'max_examples': MAX_SAMPLES, 'stateful_step_count': MAX_COUNT, 'suppress_health_check': HealthCheck.all()})
