import brownie
from math import log
from brownie.test import strategy
from .conftest import INITIAL_PRICES


MAX_SAMPLES = 250
MAX_D = 10**12 * 10**18  # $1T is hopefully a reasonable cap for tests


class NumbaGoUp:
    """
    Test that profit goes up
    """

    exchange_amount_in = strategy('uint256', max_value=10**9 * 10**18)  # in USD
    exchange_i = strategy('uint8', max_value=2)
    exchange_j = strategy('uint8', max_value=2)
    deposit_amounts = strategy('uint256[3]', min_value=0, max_value=10**9 * 10**18)
    token_amount = strategy('uint256', max_value=10**12 * 10**18)
    sleep_time = strategy('uint256', max_value=86400 * 7)
    user = strategy('address')

    def __init__(self, chain, accounts, coins, crypto_swap, token):
        self.accounts = accounts
        self.swap = crypto_swap
        self.coins = coins
        self.chain = chain
        self.token = token

    def setup(self):
        self.user_balances = {u: [0] * 3 for u in self.accounts}
        self.initial_deposit = [10**4 * 10**36 // p for p in [10**18] + INITIAL_PRICES]  # $10k * 3
        self.initial_prices = [10**18] + INITIAL_PRICES
        user = self.accounts[0]

        for coin, q in zip(self.coins, self.initial_deposit):
            coin._mint_for_testing(user, q)
            coin.approve(self.swap, 2**256-1, {'from': user})

        # Inf approve all, too. Not always that's the best way though
        for u in self.accounts[1:]:
            for coin in self.coins:
                coin.approve(self.swap, 2**256-1, {'from': u})

        # Very first deposit
        self.swap.add_liquidity(self.initial_deposit, 0, {'from': user})

        self.balances = self.initial_deposit
        self.initial_vprice = self.swap.get_virtual_price()
        self.total_supply = self.token.balanceOf(user)

    def convert_amounts(self, amounts):
        prices = [10**18] + [self.swap.price_scale(i) for i in range(2)]
        return [p * a // 10**18 for p, a in zip(prices, amounts)]

    def check_limits(self, amounts, D=True, y=True):
        """
        Should be good if within limits, but if outside - can be either
        """
        _D = self.swap.D()
        prices = [10**18] + [self.swap.price_scale(i) for i in range(2)]
        xp_0 = [self.swap.balances(i) for i in range(3)]
        xp = xp_0
        xp_0 = [x * p // 10**18 for x, p in zip(xp_0, prices)]
        xp = [(x + a) * p // 10**18 for a, x, p in zip(amounts, xp, prices)]

        if D:
            for _xp in [xp_0, xp]:
                if (min(_xp) * 10**18 // max(_xp) < 10**11) or\
                   (max(_xp) < 10**9 * 10**18) or (max(_xp) > 10**15 * 10**18):
                    return False

        if y:
            for _xp in [xp_0, xp]:
                if (_D < 10**17) or (_D > 10**15 * 10**18) or\
                   (min(_xp) * 10**18 // _D < 5 * 10**15) or (max(_xp) * 10**18 // _D > 2 * 10**20):
                    return False

        return True

    def rule_deposit(self, deposit_amounts, user):
        if self.swap.D() > MAX_D:
            return

        amounts = self.convert_amounts(deposit_amounts)
        new_balances = [x + y for x, y in zip(self.balances, amounts)]

        for coin, q in zip(self.coins, amounts):
            coin._mint_for_testing(user, q)

        try:
            tokens = self.token.balanceOf(user)
            self.swap.add_liquidity(amounts, 0, {'from': user})
            tokens = self.token.balanceOf(user) - tokens
            self.total_supply += tokens
            self.balances = new_balances
        except Exception:
            if self.check_limits(amounts):
                raise

    def rule_remove_liquidity(self, token_amount, user):
        if self.token.balanceOf(user) < token_amount:
            with brownie.reverts():
                self.swap.remove_liquidity(token_amount, [0] * 3, {'from': user})
        else:
            amounts = [c.balanceOf(user) for c in self.coins]
            tokens = self.token.balanceOf(user)
            self.swap.remove_liquidity(token_amount, [0] * 3, {'from': user})
            tokens -= self.token.balanceOf(user)
            self.total_supply -= tokens
            amounts = [(c.balanceOf(user) - a) for c, a in zip(self.coins, amounts)]
            self.balances = [b-a for a, b in zip(amounts, self.balances)]

    def rule_remove_liquidity_one_coin(self, token_amount, exchange_i, user):
        try:
            calc_out_amount = self.swap.calc_withdraw_one_coin(token_amount, exchange_i)
        except Exception:
            if self.check_limits([0] * 3) and not (token_amount > self.total_supply):
                raise
            return

        d_token = self.token.balanceOf(user)
        if d_token < token_amount:
            with brownie.reverts():
                self.swap.remove_liquidity_one_coin(token_amount, exchange_i, 0, {'from': user})
            return

        d_balance = self.coins[exchange_i].balanceOf(user)
        self.swap.remove_liquidity_one_coin(token_amount, exchange_i, 0, {'from': user})
        d_balance = self.coins[exchange_i].balanceOf(user) - d_balance
        d_token = d_token - self.token.balanceOf(user)

        assert calc_out_amount == d_balance

        self.balances[exchange_i] -= d_balance
        self.total_supply -= d_token

    def rule_exchange(self, exchange_amount_in, exchange_i, exchange_j, user):
        if exchange_i == exchange_j:
            return
        try:
            calc_amount = self.swap.get_dy(exchange_i, exchange_j, exchange_amount_in)
        except Exception:
            _amounts = [0] * 3
            _amounts[exchange_i] = exchange_amount_in
            if self.check_limits(_amounts):
                raise
            return
        self.coins[exchange_i]._mint_for_testing(user, exchange_amount_in)

        d_balance_i = self.coins[exchange_i].balanceOf(user)
        d_balance_j = self.coins[exchange_j].balanceOf(user)
        self.swap.exchange(exchange_i, exchange_j, exchange_amount_in, 0, {'from': user})
        d_balance_i -= self.coins[exchange_i].balanceOf(user)
        d_balance_j -= self.coins[exchange_j].balanceOf(user)

        assert d_balance_i == exchange_amount_in
        assert -d_balance_j == calc_amount

        self.balances[exchange_i] += d_balance_i
        self.balances[exchange_j] += d_balance_j

    def rule_sleep(self, sleep_time):
        self.chain.sleep(sleep_time)

    def invariant_balances(self):
        balances = [self.swap.balances(i) for i in range(3)]
        balances_of = [c.balanceOf(self.swap) for c in self.coins]
        for i in range(3):
            assert self.balances[i] == balances[i]
            assert self.balances[i] == balances_of[i]

    def invariant_total_supply(self):
        assert self.total_supply == self.token.totalSupply()

    def invariant_virtual_price(self):
        xcp_profit_real = self.swap.xcp_profit_real()
        xcp_profit = self.swap.xcp_profit()
        virtual_price = self.swap.get_virtual_price()

        assert xcp_profit >= 10**18
        assert xcp_profit_real >= 10**18
        assert virtual_price >= 10**18

        assert (xcp_profit_real - 10**18) * 2 >= xcp_profit - 10**18
        assert abs(log(xcp_profit_real / virtual_price)) < 1e-3


def test_numba_go_up(crypto_swap, token, chain, accounts, coins, state_machine):
    state_machine(NumbaGoUp, chain, accounts, coins, crypto_swap, token,
                  settings={'max_examples': MAX_SAMPLES, 'stateful_step_count': 20})
