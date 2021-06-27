from .test_stateful import NumbaGoUp

MAX_SAMPLES = 20
MAX_COUNT = 20
MAX_D = 10**12 * 10**18  # $1T is hopefully a reasonable cap for tests


class RampTest(NumbaGoUp):
    def setup(self, user_id=0):
        super().setup(user_id)
        new_A = self.swap.A() * 2
        new_gamma = self.swap.gamma() // 2
        self.swap.ramp_A_gamma(new_A, new_gamma, self.chain.time() + 14*86400, {'from': self.accounts[0]})


def test_ramp(crypto_swap, token, chain, accounts, coins, state_machine):
    from hypothesis._settings import HealthCheck

    state_machine(RampTest, chain, accounts, coins, crypto_swap, token,
                  settings={'max_examples': MAX_SAMPLES, 'stateful_step_count': MAX_COUNT, 'suppress_health_check': HealthCheck.all()})
