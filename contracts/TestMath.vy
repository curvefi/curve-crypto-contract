# @version 0.2.8
N_COINS: constant(uint256) = 3
A_MULTIPLIER: constant(uint256) = 100

@internal
@pure
def sort(A0: uint256[N_COINS]) -> uint256[N_COINS]:
    """
    Insertion sort from high to low
    """
    A: uint256[N_COINS] = A0
    for i in range(1, N_COINS):
        x: uint256 = A[i]
        cur: uint256 = i
        for j in range(N_COINS):
            y: uint256 = A[cur-1]
            if y > x:
                break
            A[cur] = y
            cur -= 1
            if cur == 0:
                break
        A[cur] = x
    return A


@external
@view
def pub_sort(A0: uint256[N_COINS]) -> uint256[N_COINS]:
    return self.sort(A0)


@internal
@view
def geometric_mean(unsorted_x: uint256[N_COINS], sort: bool = True) -> uint256:
    """
    (x[0] * x[1] * ...) ** (1/N)
    """
    x: uint256[N_COINS] = unsorted_x
    if sort:
        x = self.sort(x)
    D: uint256 = x[0]
    diff: uint256 = 0
    for i in range(255):
        D_prev: uint256 = D
        tmp: uint256 = 10**18
        for _x in x:
            tmp = tmp * _x / D
        D = D * ((N_COINS - 1) * 10**18 + tmp) / (N_COINS * 10**18)
        if D > D_prev:
            diff = D - D_prev
        else:
            diff = D_prev - D
        if diff <= 1 or diff * 10**18 < D:
            return D
    raise "Did not converge"


@external
@view
def pub_geometric_mean(unsorted_x: uint256[N_COINS]) -> uint256:
    return self.geometric_mean(unsorted_x)


@internal
@pure
def reduction_coefficient(x: uint256[N_COINS], gamma: uint256) -> uint256:
    """
    gamma / (gamma + (1 - K))
    where
    K = prod(x) / (sum(x) / N)**N
    (all normalized to 1e18)
    """
    K: uint256 = 10**18
    S: uint256 = 0
    for x_i in x:
        S += x_i
    # Could be good to pre-sort x, but it is used only for dynamic fee,
    # so that is not so important
    for x_i in x:
        K = K * N_COINS * x_i / S
    if gamma > 0:
        K = gamma * 10**18 / (gamma + 10**18 - K)
    return K


@external
@view
def pub_reduction_coefficient(x: uint256[N_COINS], gamma: uint256) -> uint256:
    return self.reduction_coefficient(x, gamma)


@internal
@view
def newton_D(ANN: uint256, gamma: uint256, x_unsorted: uint256[N_COINS]) -> uint256:
    """
    Finding the invariant using Newton method.
    ANN is higher by the factor A_MULTIPLIER
    ANN is already A * N**N

    Currently uses 60k gas
    """
    # Initial value of invariant D is that for constant-product invariant
    x: uint256[N_COINS] = self.sort(x_unsorted)
    D: uint256 = N_COINS * self.geometric_mean(x, False)
    S: uint256 = 0
    for x_i in x:
        S += x_i

    for i in range(255):
        D_prev: uint256 = D

        K0: uint256 = 10**18
        for _x in x:
            K0 = K0 * _x * N_COINS / D

        _g1k0: uint256 = gamma + 10**18
        if _g1k0 > K0:
            _g1k0 -= K0
        else:
            _g1k0 = K0 - _g1k0

        # D / (A * N**N) * _g1k0**2 / gamma**2
        mul1: uint256 = 10**18 * D / gamma * _g1k0 / gamma * _g1k0 * A_MULTIPLIER / ANN

        # 2*N*K0 / _g1k0
        mul2: uint256 = (2 * 10**18) * N_COINS * K0 / _g1k0

        neg_fprime: uint256 = (S + S * mul2 / 10**18) + mul1 * N_COINS / K0 - mul2 * D / 10**18

        # D -= f / fprime
        D_plus: uint256 = D * (neg_fprime + S) / neg_fprime
        D_minus: uint256 = D*D / neg_fprime
        if 10**18 > K0:
            D_minus += D * (mul1 / neg_fprime) / 10**18 * (10**18 - K0) / K0
        else:
            D_minus -= D * (mul1 / neg_fprime) / 10**18 * (K0 - 10**18) / K0

        if D_plus > D_minus:
            D = D_plus - D_minus
        else:
            D = (D_minus - D_plus) / 2

        diff: uint256 = 0
        if D > D_prev:
            diff = D - D_prev
        else:
            diff = D_prev - D
        if diff * 10**14 < max(10**16, D):  # Could reduce precision for gas efficiency here
            return D

    raise "Did not converge"


@external
@view
def public_newton_D(A: uint256, gamma: uint256, x_unsorted: uint256[N_COINS]) -> uint256:
    return self.newton_D(A * N_COINS**N_COINS * A_MULTIPLIER, gamma, x_unsorted)
