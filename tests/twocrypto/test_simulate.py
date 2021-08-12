from math import log
from brownie.test import strategy
from .stateful_base import StatefulBase
from . import simulation_int_many as sim

MAX_SAMPLES = 20
STEP_COUNT = 100


def approx(x1, x2, precision):
    return abs(log(x1 / x2)) <= precision


class StatefulSimulation(StatefulBase):
    exchange_amount_in = strategy('uint256', min_value=10**17, max_value=10**5 * 10**18)

    def setup(self):
        super().setup()

        for u in self.accounts[1:]:
            for coin, q in zip(self.coins, self.initial_deposit):
                coin._mint_for_testing(u, q)
            for i in range(2):
                self.balances[i] += self.initial_deposit[i]
            self.swap.add_liquidity(self.initial_deposit, 0, {'from': u})
            self.total_supply += self.token.balanceOf(u)

        self.virtual_price = self.swap.get_virtual_price()

        self.trader = sim.Trader(
            self.swap.A(),
            self.swap.gamma(),
            self.swap.D(),
            2,
            [10**18, self.swap.price_scale()],
            self.swap.mid_fee() / 1e10,
            self.swap.out_fee() / 1e10,
            self.swap.allowed_extra_profit(),
            self.swap.fee_gamma(),
            self.swap.adjustment_step() / 1e18,
            self.swap.ma_half_time()
        )
        for i in range(2):
            self.trader.curve.x[i] = self.swap.balances(i)

        # Adjust virtual prices
        self.trader.xcp_profit = self.swap.xcp_profit()
        self.trader.xcp_profit_real = self.swap.virtual_price()
        self.trader.t = self.chain[-1].timestamp

    def rule_exchange(self, exchange_amount_in, exchange_i, user):
        exchange_j = 1 - exchange_i
        exchange_amount_in = exchange_amount_in * 10**18 // self.trader.price_oracle[exchange_i]

        if super().rule_exchange(exchange_amount_in, exchange_i, user):
            dy = self.trader.buy(exchange_amount_in, exchange_i, exchange_j)
            price = exchange_amount_in * 10**18 // dy
            self.trader.tweak_price(self.chain[-1].timestamp, exchange_i, exchange_j, price)

    def invariant_simulator(self):
        if self.trader.xcp_profit / 1e18 - 1 > 1e-8:
            assert abs(self.trader.xcp_profit - self.swap.xcp_profit()) / (self.trader.xcp_profit - 10**18) < 0.05
        assert approx(self.trader.curve.p[1], self.swap.price_scale(), 1e-4)  # adjustment_step * 2


def test_sim(crypto_swap, token, chain, accounts, coins, state_machine):
    from hypothesis._settings import HealthCheck

    state_machine(StatefulSimulation, chain, accounts, coins, crypto_swap, token,
                  settings={'max_examples': MAX_SAMPLES, 'stateful_step_count': STEP_COUNT, 'suppress_health_check': HealthCheck.all()})
