from brownie.test import strategy
from .test_simulate import StatefulSimulation

MAX_SAMPLES = 10
STEP_COUNT = 100


class Realistic(StatefulSimulation):
    exchange_amount_in = strategy('uint256', min_value=100 * 10**18, max_value=1000 * 10**18)
    sleep_time = strategy('uint256', max_value=100)


def test_sim(crypto_swap, token, chain, accounts, coins, state_machine):
    state_machine(Realistic, chain, accounts, coins, crypto_swap, token,
                  settings={'max_examples': MAX_SAMPLES, 'stateful_step_count': STEP_COUNT})
