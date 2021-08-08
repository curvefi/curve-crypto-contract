import unittest
import hypothesis.strategies as st
from hypothesis import given, settings


def halfpow(power, precision):
    """
    1e18 * 0.5 ** (power/1e18)
    """
    intpow = power // 10**18
    otherpow = power - intpow * 10**18
    if intpow > 59:
        return 0
    result = 10**18 // 2**intpow

    term = 10**18
    x = 5 * 10**17
    S = 10**18  # Avoiding negative numbers here
    neg = False
    for i in range(1, 256):
        K = i * 10**18
        c = (K - 10**18)
        if otherpow > c:
            c = otherpow - c
            neg = not neg
        else:
            c -= otherpow
        term = term * (c * x // 10**18) // K
        if neg:
            S -= term
        else:
            S += term
        assert S >= 0
        if term < precision:
            return result * S // 10**18
    raise ValueError("Did not converge")


class TestExp(unittest.TestCase):
    @given(
        st.integers(0, 10**22),
        st.integers(10, 10**15)
    )
    @settings(max_examples=10000)
    def test_exp(self, power, precision):
        pow_int = halfpow(power, precision) / 1e18
        pow_ideal = 0.5 ** (power / 1e18)
        assert abs(pow_int - pow_ideal) < max(5 * precision / 1e18, 5e-16)


if __name__ == "__main__":
    unittest.main()
