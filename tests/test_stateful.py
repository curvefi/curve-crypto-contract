from brownie.test import strategy
from .conftest import INITIAL_PRICES


class NumbaGoUp:
    """
    Test that profit goes up
    """

    exchange_amount_in = strategy('uint256', max_value=10**9 * 10**18)  # in USD
    exchange_i = strategy('uint8', max_value=3)  # 3 is deliberately wrong one
    deposit_amounts = strategy('uint256[3]', min_value=0, max_value=10**9 * 10**18)
    sleep_time = strategy('uint256', max_value=86400 * 7)
    user = strategy('address')

    def __init__(self, chain, accounts, coins, crypto_swap):
        self.accounts = accounts
        self.swap = crypto_swap
        self.coins = coins
        self.chain = chain

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
        amounts = self.convert_amounts(deposit_amounts)
        new_balances = [x + y for x, y in zip(self.balances, amounts)]

        for coin, q in zip(self.coins, amounts):
            coin._mint_for_testing(user, q)

        try:
            self.swap.add_liquidity(amounts, 0, {'from': user})
            self.balances = new_balances
        except Exception:
            if self.check_limits(amounts):
                raise

    def rule_sleep(self, sleep_time):
        self.chain.sleep(sleep_time)


def test_numba_go_up(crypto_swap, chain, accounts, coins, state_machine):
    state_machine(NumbaGoUp, chain, accounts, coins, crypto_swap)
