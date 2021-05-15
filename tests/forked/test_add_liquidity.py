def test_add_all_coins(alice, crypto_zap, deposit_amounts, crypto_lp_token):
    crypto_zap.add_liquidity(deposit_amounts, 0, {"from": alice})

    assert crypto_lp_token.balanceOf(alice) > 0


def test_add_base_coins(alice, crypto_zap, deposit_amounts, crypto_lp_token):
    amounts = deposit_amounts[:3] + [0, 0]
    crypto_zap.add_liquidity(amounts, 0, {"from": alice})

    assert crypto_lp_token.balanceOf(alice) > 0


def test_add_unwrapped_coins(alice, crypto_zap, deposit_amounts, crypto_lp_token):
    amounts = [0, 0, 0] + deposit_amounts[3:]
    crypto_zap.add_liquidity(amounts, 0, {"from": alice})

    assert crypto_lp_token.balanceOf(alice) > 0


def test_add_coins_for_alt_receiver(
    alice, bob, crypto_zap, deposit_amounts, crypto_lp_token
):
    crypto_zap.add_liquidity(deposit_amounts, 0, bob, {"from": alice})

    assert crypto_lp_token.balanceOf(alice) == 0
    assert crypto_lp_token.balanceOf(bob) > 0


def test_add_coins_min_mint_amount(alice, crypto_zap, deposit_amounts, crypto_lp_token):
    amt = crypto_zap.calc_token_amount.call(deposit_amounts, True)
    crypto_zap.add_liquidity(deposit_amounts, amt * 0.99, {"from": alice})

    assert crypto_lp_token.balanceOf(alice) >= amt * 0.99


# def test_revert_mint_not_enough(alice, crypto_zap, deposit_amounts, crypto_lp_token):
#     with brownie.reverts():
#         crypto_zap.add_liquidity(deposit_amounts, 2 ** 10 ** 18, {"from": alice})

#     assert crypto_lp_token.balanceOf(alice) == 0
