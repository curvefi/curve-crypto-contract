from math import log
from brownie.test import strategy
from .stateful_base import StatefulBase
from . import simulation_int_many as sim

MAX_SAMPLES = 30
STEP_COUNT = 10


def approx(x1, x2, precision):
    return abs(log(x1 / x2)) <= precision


class StatefulSimulation(StatefulBase):
    exchange_amount_in = strategy('uint256', min_value=10**17, max_value=10**5 * 10**18)

    def setup(self):
        super().setup()

        for u in self.accounts[1:]:
            for coin, q in zip(self.coins, self.initial_deposit):
                coin._mint_for_testing(u, q)
            for i in range(3):
                self.balances[i] += self.initial_deposit[i]
            self.swap.add_liquidity(self.initial_deposit, 0, {'from': u})
            self.total_supply += self.token.balanceOf(u)

        self.virtual_price = self.swap.get_virtual_price()

        self.trader = sim.Trader(
            self.swap.A() // 3**3,
            self.swap.gamma(),
            self.swap.D(),
            3,
            [10**18] + [self.swap.price_scale(i) for i in range(2)],
            self.swap.mid_fee() / 1e10,
            self.swap.out_fee() / 1e10,
            self.swap.price_threshold() / 1e18,
            self.swap.fee_gamma(),
            self.swap.adjustment_step() / 1e18,
            self.swap.ma_half_time()
        )
        for i in range(3):
            self.trader.curve.x[i] = self.swap.balances(i)

        # Adjust virtual prices
        self.trader.xcp_profit = self.swap.xcp_profit()
        self.trader.xcp_profit_real = self.swap.virtual_price()
        self.trader.t = self.chain.time()

    def rule_exchange(self, exchange_amount_in, exchange_i, exchange_j, user):
        exchange_amount_in = exchange_amount_in * 10**18 // self.trader.price_oracle[exchange_i]

        t = self.chain.time()
        if super().rule_exchange(exchange_amount_in, exchange_i, exchange_j, user):
            dy = self.trader.buy(exchange_amount_in, exchange_i, exchange_j)
            price = exchange_amount_in * 10**18 // dy
            self.trader.tweak_price(t, exchange_i, exchange_j, price)

    def invariant_simulator(self):
        assert abs(self.trader.xcp_profit - self.swap.xcp_profit()) / 1e18 < 1e-6
        # virtual_price taking at least half the profit is checked in stateful_base
        for i in range(2):
            assert approx(self.trader.curve.p[i+1], self.swap.price_scale(i), 3e-3)  # adjustment_step * 2


def test_sim(crypto_swap, token, chain, accounts, coins, state_machine):
    state_machine(StatefulSimulation, chain, accounts, coins, crypto_swap, token,
                  settings={'max_examples': MAX_SAMPLES, 'stateful_step_count': STEP_COUNT})
