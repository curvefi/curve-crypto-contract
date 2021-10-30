from brownie import interface


def test_oracle(crypto_zap):
    base_pool = interface.StableSwap3Pool(crypto_zap.base_pool())
    vp = base_pool.get_virtual_price()
    price = 1 / 0.8

    assert (crypto_zap.price_oracle() - vp * price) / (vp * price) < 1e-4
    assert (crypto_zap.price_scale() - vp * price) / (vp * price) < 1e-4
