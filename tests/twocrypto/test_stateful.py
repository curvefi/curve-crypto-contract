import brownie
from brownie.test import strategy
from .conftest import INITIAL_PRICES
from .stateful_base import StatefulBase


MAX_SAMPLES = 20
MAX_COUNT = 20
MAX_D = 10**12 * 10**18  # $1T is hopefully a reasonable cap for tests


class NumbaGoUp(StatefulBase):
    """
    Test that profit goes up
    """

    deposit_amounts = strategy('uint256[2]', min_value=0, max_value=10**9 * 10**18)
    token_amount = strategy('uint256', max_value=10**12 * 10**18)
    check_out_amount = strategy('bool')

    def rule_deposit(self, deposit_amounts, user):
        if self.swap.D() > MAX_D:
            return

        amounts = self.convert_amounts(deposit_amounts)
        if sum(amounts) == 0:
            return
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
            try:
                self.swap.calc_token_amount.transact(amounts, {'from': user})
            except Exception:
                if sum(amounts) > 10000:
                    raise
            if self.check_limits(amounts) and self.swap.calc_token_amount(amounts) > 0:
                raise
            else:
                return

        # This is to check that we didn't end up in a borked state after
        # an exchange succeeded
        try:
            self.swap.get_dy(0, 1, 10**(self.decimals[0]-2))
        except Exception:
            self.swap.get_dy(1, 0, 10**16 * 10**self.decimals[1] // self.swap.price_scale())

    def rule_remove_liquidity(self, token_amount, user):
        if self.token.balanceOf(user) < token_amount or token_amount == 0:
            with brownie.reverts():
                self.swap.remove_liquidity(token_amount, [0] * 2, {'from': user})
        else:
            amounts = [c.balanceOf(user) for c in self.coins]
            tokens = self.token.balanceOf(user)
            self.swap.remove_liquidity(token_amount, [0] * 2, {'from': user})
            tokens -= self.token.balanceOf(user)
            self.total_supply -= tokens
            amounts = [(c.balanceOf(user) - a) for c, a in zip(self.coins, amounts)]
            self.balances = [b-a for a, b in zip(amounts, self.balances)]

            # Virtual price resets if everything is withdrawn
            if self.total_supply == 0:
                self.virtual_price = 10**18

    def rule_remove_liquidity_one_coin(self, token_amount, exchange_i, user, check_out_amount):
        if check_out_amount:
            self.swap.claim_admin_fees()

        try:
            calc_out_amount = self.swap.calc_withdraw_one_coin(token_amount, exchange_i)
        except Exception:
            if self.check_limits([0] * 2) and not (token_amount > self.total_supply):
                raise
            return

        d_token = self.token.balanceOf(user)
        if d_token < token_amount:
            with brownie.reverts():
                self.swap.remove_liquidity_one_coin(token_amount, exchange_i, 0, {'from': user})
            return

        d_balance = self.coins[exchange_i].balanceOf(user)
        try:
            self.swap.remove_liquidity_one_coin(token_amount, exchange_i, 0, {'from': user})
        except Exception:
            # Small amounts may fail with rounding errors
            if calc_out_amount > 100 and\
               token_amount / self.total_supply > 1e-10 and\
               calc_out_amount / self.swap.balances(exchange_i) > 1e-10:
                raise
            return

        # This is to check that we didn't end up in a borked state after
        # an exchange succeeded
        _deposit = [0] * 2
        _deposit[exchange_i] = 10**16 * 10**self.decimals[exchange_i] // ([10**18] + INITIAL_PRICES)[exchange_i]
        self.swap.calc_token_amount(_deposit)

        d_balance = self.coins[exchange_i].balanceOf(user) - d_balance
        d_token = d_token - self.token.balanceOf(user)

        if check_out_amount:
            if check_out_amount is True:
                assert calc_out_amount == d_balance, f"{calc_out_amount} vs {d_balance} for {token_amount}"
            else:
                assert abs(calc_out_amount - d_balance) <= max(check_out_amount * calc_out_amount, 5), f"{calc_out_amount} vs {d_balance} for {token_amount}"

        self.balances[exchange_i] -= d_balance
        self.total_supply -= d_token

        # Virtual price resets if everything is withdrawn
        if self.total_supply == 0:
            self.virtual_price = 10**18


def test_numba_go_up(crypto_swap, token, chain, accounts, coins, state_machine):
    from hypothesis._settings import HealthCheck

    state_machine(NumbaGoUp, chain, accounts, coins, crypto_swap, token,
                  settings={'max_examples': MAX_SAMPLES, 'stateful_step_count': MAX_COUNT, 'suppress_health_check': HealthCheck.all()})
