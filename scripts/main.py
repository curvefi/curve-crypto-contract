from brownie import accounts, Contract


dev = accounts.at("0x7EeAC6CDdbd1D0B8aF061742D41877D7F707289a", force=True)


admin_proxy_abi = [
    {
        "name": "TransactionExecuted",
        "inputs": [
            {"name": "admin", "type": "address", "indexed": True},
            {"name": "target", "type": "address", "indexed": True},
            {"name": "calldata", "type": "bytes", "indexed": False},
            {"name": "value", "type": "uint256", "indexed": False},
        ],
        "anonymous": False,
        "type": "event",
    },
    {
        "name": "RequestAdminChange",
        "inputs": [
            {"name": "current_admin", "type": "address", "indexed": False},
            {"name": "future_admin", "type": "address", "indexed": False},
        ],
        "anonymous": False,
        "type": "event",
    },
    {
        "name": "RevokeAdminChange",
        "inputs": [
            {"name": "current_admin", "type": "address", "indexed": False},
            {"name": "future_admin", "type": "address", "indexed": False},
            {"name": "calling_admin", "type": "address", "indexed": False},
        ],
        "anonymous": False,
        "type": "event",
    },
    {
        "name": "ApproveAdminChange",
        "inputs": [
            {"name": "current_admin", "type": "address", "indexed": False},
            {"name": "future_admin", "type": "address", "indexed": False},
            {"name": "calling_admin", "type": "address", "indexed": False},
        ],
        "anonymous": False,
        "type": "event",
    },
    {
        "name": "AcceptAdminChange",
        "inputs": [
            {"name": "previous_admin", "type": "address", "indexed": False},
            {"name": "current_admin", "type": "address", "indexed": False},
        ],
        "anonymous": False,
        "type": "event",
    },
    {
        "stateMutability": "nonpayable",
        "type": "constructor",
        "inputs": [{"name": "_authorized", "type": "address[2]"}],
        "outputs": [],
    },
    {
        "stateMutability": "payable",
        "type": "function",
        "name": "execute",
        "inputs": [
            {"name": "_target", "type": "address"},
            {"name": "_calldata", "type": "bytes"},
        ],
        "outputs": [],
        "gas": 1168658,
    },
    {
        "stateMutability": "view",
        "type": "function",
        "name": "get_admin_change_status",
        "inputs": [],
        "outputs": [
            {"name": "", "type": "address"},
            {"name": "", "type": "address"},
            {"name": "", "type": "bool"},
        ],
        "gas": 4202,
    },
    {
        "stateMutability": "nonpayable",
        "type": "function",
        "name": "request_admin_change",
        "inputs": [{"name": "_new_admin", "type": "address"}],
        "outputs": [],
        "gas": 148342,
    },
    {
        "stateMutability": "nonpayable",
        "type": "function",
        "name": "approve_admin_change",
        "inputs": [],
        "outputs": [],
        "gas": 41716,
    },
    {
        "stateMutability": "nonpayable",
        "type": "function",
        "name": "revoke_admin_change",
        "inputs": [],
        "outputs": [],
        "gas": 67885,
    },
    {
        "stateMutability": "nonpayable",
        "type": "function",
        "name": "accept_admin_change",
        "inputs": [],
        "outputs": [],
        "gas": 101134,
    },
    {
        "stateMutability": "view",
        "type": "function",
        "name": "admins",
        "inputs": [{"name": "arg0", "type": "uint256"}],
        "outputs": [{"name": "", "type": "address"}],
        "gas": 1377,
    },
]
crypto_registry_abi = [
    {
        "name": "PoolAdded",
        "inputs": [{"name": "pool", "type": "address", "indexed": True}],
        "anonymous": False,
        "type": "event",
    },
    {
        "name": "PoolRemoved",
        "inputs": [{"name": "pool", "type": "address", "indexed": True}],
        "anonymous": False,
        "type": "event",
    },
    {
        "stateMutability": "nonpayable",
        "type": "constructor",
        "inputs": [{"name": "_address_provider", "type": "address"}],
        "outputs": [],
    },
    {
        "stateMutability": "view",
        "type": "function",
        "name": "find_pool_for_coins",
        "inputs": [
            {"name": "_from", "type": "address"},
            {"name": "_to", "type": "address"},
        ],
        "outputs": [{"name": "", "type": "address"}],
        "gas": 3111,
    },
    {
        "stateMutability": "view",
        "type": "function",
        "name": "find_pool_for_coins",
        "inputs": [
            {"name": "_from", "type": "address"},
            {"name": "_to", "type": "address"},
            {"name": "i", "type": "uint256"},
        ],
        "outputs": [{"name": "", "type": "address"}],
        "gas": 3111,
    },
    {
        "stateMutability": "view",
        "type": "function",
        "name": "get_n_coins",
        "inputs": [{"name": "_pool", "type": "address"}],
        "outputs": [{"name": "", "type": "uint256"}],
        "gas": 2834,
    },
    {
        "stateMutability": "view",
        "type": "function",
        "name": "get_coins",
        "inputs": [{"name": "_pool", "type": "address"}],
        "outputs": [{"name": "", "type": "address[8]"}],
        "gas": 22975,
    },
    {
        "stateMutability": "view",
        "type": "function",
        "name": "get_decimals",
        "inputs": [{"name": "_pool", "type": "address"}],
        "outputs": [{"name": "", "type": "uint256[8]"}],
        "gas": 9818,
    },
    {
        "stateMutability": "view",
        "type": "function",
        "name": "get_gauges",
        "inputs": [{"name": "_pool", "type": "address"}],
        "outputs": [
            {"name": "", "type": "address[10]"},
            {"name": "", "type": "int128[10]"},
        ],
        "gas": 26055,
    },
    {
        "stateMutability": "view",
        "type": "function",
        "name": "get_balances",
        "inputs": [{"name": "_pool", "type": "address"}],
        "outputs": [{"name": "", "type": "uint256[8]"}],
        "gas": 41626,
    },
    {
        "stateMutability": "view",
        "type": "function",
        "name": "get_virtual_price_from_lp_token",
        "inputs": [{"name": "_token", "type": "address"}],
        "outputs": [{"name": "", "type": "uint256"}],
        "gas": 5321,
    },
    {
        "stateMutability": "view",
        "type": "function",
        "name": "get_A",
        "inputs": [{"name": "_pool", "type": "address"}],
        "outputs": [{"name": "", "type": "uint256"}],
        "gas": 3139,
    },
    {
        "stateMutability": "view",
        "type": "function",
        "name": "get_D",
        "inputs": [{"name": "_pool", "type": "address"}],
        "outputs": [{"name": "", "type": "uint256"}],
        "gas": 3169,
    },
    {
        "stateMutability": "view",
        "type": "function",
        "name": "get_gamma",
        "inputs": [{"name": "_pool", "type": "address"}],
        "outputs": [{"name": "", "type": "uint256"}],
        "gas": 3199,
    },
    {
        "stateMutability": "view",
        "type": "function",
        "name": "get_fees",
        "inputs": [{"name": "_pool", "type": "address"}],
        "outputs": [{"name": "", "type": "uint256[4]"}],
        "gas": 10333,
    },
    {
        "stateMutability": "view",
        "type": "function",
        "name": "get_admin_balances",
        "inputs": [{"name": "_pool", "type": "address"}],
        "outputs": [{"name": "", "type": "uint256[8]"}],
        "gas": 85771,
    },
    {
        "stateMutability": "view",
        "type": "function",
        "name": "get_coin_indices",
        "inputs": [
            {"name": "_pool", "type": "address"},
            {"name": "_from", "type": "address"},
            {"name": "_to", "type": "address"},
        ],
        "outputs": [{"name": "", "type": "uint256"}, {"name": "", "type": "uint256"}],
        "gas": 23608,
    },
    {
        "stateMutability": "view",
        "type": "function",
        "name": "get_pool_name",
        "inputs": [{"name": "_pool", "type": "address"}],
        "outputs": [{"name": "", "type": "string"}],
        "gas": 13576,
    },
    {
        "stateMutability": "view",
        "type": "function",
        "name": "get_coin_swap_count",
        "inputs": [{"name": "_coin", "type": "address"}],
        "outputs": [{"name": "", "type": "uint256"}],
        "gas": 3224,
    },
    {
        "stateMutability": "view",
        "type": "function",
        "name": "get_coin_swap_complement",
        "inputs": [
            {"name": "_coin", "type": "address"},
            {"name": "_index", "type": "uint256"},
        ],
        "outputs": [{"name": "", "type": "address"}],
        "gas": 3299,
    },
    {
        "stateMutability": "nonpayable",
        "type": "function",
        "name": "add_pool",
        "inputs": [
            {"name": "_pool", "type": "address"},
            {"name": "_n_coins", "type": "uint256"},
            {"name": "_lp_token", "type": "address"},
            {"name": "_gauge", "type": "address"},
            {"name": "_zap", "type": "address"},
            {"name": "_decimals", "type": "uint256"},
            {"name": "_name", "type": "string"},
        ],
        "outputs": [],
        "gas": 18586944,
    },
    {
        "stateMutability": "nonpayable",
        "type": "function",
        "name": "remove_pool",
        "inputs": [{"name": "_pool", "type": "address"}],
        "outputs": [],
        "gas": 399675363514,
    },
    {
        "stateMutability": "nonpayable",
        "type": "function",
        "name": "set_liquidity_gauges",
        "inputs": [
            {"name": "_pool", "type": "address"},
            {"name": "_liquidity_gauges", "type": "address[10]"},
        ],
        "outputs": [],
        "gas": 422284,
    },
    {
        "stateMutability": "nonpayable",
        "type": "function",
        "name": "batch_set_liquidity_gauges",
        "inputs": [
            {"name": "_pools", "type": "address[10]"},
            {"name": "_liquidity_gauges", "type": "address[10]"},
        ],
        "outputs": [],
        "gas": 444084,
    },
    {
        "stateMutability": "view",
        "type": "function",
        "name": "address_provider",
        "inputs": [],
        "outputs": [{"name": "", "type": "address"}],
        "gas": 3126,
    },
    {
        "stateMutability": "view",
        "type": "function",
        "name": "pool_list",
        "inputs": [{"name": "arg0", "type": "uint256"}],
        "outputs": [{"name": "", "type": "address"}],
        "gas": 3201,
    },
    {
        "stateMutability": "view",
        "type": "function",
        "name": "pool_count",
        "inputs": [],
        "outputs": [{"name": "", "type": "uint256"}],
        "gas": 3186,
    },
    {
        "stateMutability": "view",
        "type": "function",
        "name": "coin_count",
        "inputs": [],
        "outputs": [{"name": "", "type": "uint256"}],
        "gas": 3216,
    },
    {
        "stateMutability": "view",
        "type": "function",
        "name": "get_coin",
        "inputs": [{"name": "arg0", "type": "uint256"}],
        "outputs": [{"name": "", "type": "address"}],
        "gas": 3291,
    },
    {
        "stateMutability": "view",
        "type": "function",
        "name": "get_pool_from_lp_token",
        "inputs": [{"name": "arg0", "type": "address"}],
        "outputs": [{"name": "", "type": "address"}],
        "gas": 3548,
    },
    {
        "stateMutability": "view",
        "type": "function",
        "name": "get_lp_token",
        "inputs": [{"name": "arg0", "type": "address"}],
        "outputs": [{"name": "", "type": "address"}],
        "gas": 3578,
    },
    {
        "stateMutability": "view",
        "type": "function",
        "name": "get_zap",
        "inputs": [{"name": "arg0", "type": "address"}],
        "outputs": [{"name": "", "type": "address"}],
        "gas": 3608,
    },
    {
        "stateMutability": "view",
        "type": "function",
        "name": "last_updated",
        "inputs": [],
        "outputs": [{"name": "", "type": "uint256"}],
        "gas": 3366,
    },
]


def pack_values(values):
    assert max(values) < 256

    return sum(i << c * 8 for c, i in enumerate(values))


def main():
    proxy = Contract.from_abi(
        "Admin Proxy", "0xB055EbbAcc8Eefc166c169e9Ce2886D0406aB49b", admin_proxy_abi
    )
    crypto_registry = Contract.from_abi(
        "Crypto Registry",
        "0x90f421832199e93d01b64DaF378b183809EB0988",
        crypto_registry_abi,
    )

    calldata = crypto_registry.add_pool.encode_input(
        "0x204f0620E7E7f07B780535711884835977679bba",  # pool
        3,  # n coins
        "0x6a4aC4DE3bF6bCD2975E2cb15A46954D9bA43fDb",  # lp token
        "0xf6C5Be565A25Be925c9D8fB0368a87bd20ee470b",  # gauge
        "0xA4F4f2252Ca88BB8079742A01981Cde8D6DFbE4E",  # zap
        pack_values([18, 8, 18]),
        "CurveFi USD-BTC-AVAX",
    )

    proxy.execute(crypto_registry, calldata, {"from": dev, "priority_fee": "auto"})
