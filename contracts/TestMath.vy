# @version 0.2.8
N_COINS: constant(uint256) = 3

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
def geometric_mean(unsorted_x: uint256[N_COINS]) -> uint256:
    """
    (x[0] * x[1] * ...) ** (1/N)
    """
    x: uint256[N_COINS] = self.sort(unsorted_x)
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
