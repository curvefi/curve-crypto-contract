# @version 0.2.12
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
