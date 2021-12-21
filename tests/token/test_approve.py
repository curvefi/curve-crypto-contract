import brownie
import pytest
from eip712.messages import EIP712Message


@pytest.mark.parametrize("idx", range(5))
def test_initial_approval_is_zero(alice, accounts, idx, token):
    assert token.allowance(alice, accounts[idx]) == 0


def test_approve(alice, bob, token):
    token.approve(bob, 10 ** 19, {"from": alice})

    assert token.allowance(alice, bob) == 10 ** 19


def test_modify_approve_nonzero(alice, bob, token):
    token.approve(bob, 10 ** 19, {"from": alice})
    token.approve(bob, 12345678, {"from": alice})

    assert token.allowance(alice, bob) == 12345678


def test_modify_approve_zero_nonzero(alice, bob, token):
    token.approve(bob, 10 ** 19, {"from": alice})
    token.approve(bob, 0, {"from": alice})
    token.approve(bob, 12345678, {"from": alice})

    assert token.allowance(alice, bob) == 12345678


def test_revoke_approve(alice, bob, token):
    token.approve(bob, 10 ** 19, {"from": alice})
    token.approve(bob, 0, {"from": alice})

    assert token.allowance(alice, bob) == 0


def test_approve_self(alice, bob, token):
    token.approve(alice, 10 ** 19, {"from": alice})

    assert token.allowance(alice, alice) == 10 ** 19


def test_only_affects_target(alice, bob, token):
    token.approve(bob, 10 ** 19, {"from": alice})

    assert token.allowance(bob, alice) == 0


def test_returns_true(alice, bob, token):
    tx = token.approve(bob, 10 ** 19, {"from": alice})

    assert tx.return_value is True


def test_approval_event_fires(alice, bob, token):
    tx = token.approve(bob, 10 ** 19, {"from": alice})

    assert len(tx.events) == 1
    assert tx.events["Approval"].values() == [alice, bob, 10 ** 19]


def test_infinite_approval(alice, bob, token):
    token.mint(alice, 10 ** 18, {"from": alice})

    token.approve(bob, 2 ** 256 - 1, {"from": alice})
    token.transferFrom(alice, bob, 10 ** 18, {"from": bob})

    assert token.allowance(alice, bob) == 2 ** 256 - 1


def test_increase_allowance(alice, bob, token):
    token.approve(bob, 100, {"from": alice})
    token.increaseAllowance(bob, 403, {"from": alice})

    assert token.allowance(alice, bob) == 503


def test_decrease_allowance(alice, bob, token):
    token.approve(bob, 100, {"from": alice})
    token.decreaseAllowance(bob, 34, {"from": alice})

    assert token.allowance(alice, bob) == 66


def test_permit(accounts, bob, chain, token, web3):

    alice = accounts.add("0x416b8a7d9290502f5661da81f0cf43893e3d19cb9aea3c426cfb36e8186e9c09")

    class Permit(EIP712Message):
        # EIP-712 Domain Fields
        _name_: "string" = token.name()
        _version_: "string" = token.version()
        _chainId_: "uint256" = chain.id
        _verifyingContract_: "address" = token.address

        # EIP-2612 Data Fields
        owner: "address"
        spender: "address"
        value: "uint256"
        nonce: "uint256"
        deadline: "uint256" = 2 ** 256 - 1

    permit = Permit(owner=alice.address, spender=bob.address, value=2 ** 256 - 1, nonce=0)
    sig = alice.sign_message(permit)

    tx = token.permit(alice, bob, 2 ** 256 - 1, 2 ** 256 - 1, sig.v, sig.r, sig.s)

    assert token.allowance(alice, bob) == 2 ** 256 - 1
    assert tx.return_value is True
    assert len(tx.events) == 1
    assert tx.events["Approval"].values() == [alice.address, bob, 2 ** 256 - 1]
    assert token.nonces(alice) == 1


def test_permit_contract(accounts, bob, chain, token, web3):

    src = """
@view
@external
def isValidSignature(_hash: bytes32, _sig: Bytes[65]) -> bytes32:
    return 0x1626ba7e00000000000000000000000000000000000000000000000000000000
    """
    mock_contract = brownie.compile_source(src, vyper_version="0.3.1").Vyper.deploy({"from": bob})
    alice = accounts.add("0x416b8a7d9290502f5661da81f0cf43893e3d19cb9aea3c426cfb36e8186e9c09")

    class Permit(EIP712Message):
        # EIP-712 Domain Fields
        _name_: "string" = token.name()
        _version_: "string" = token.version()
        _chainId_: "uint256" = chain.id
        _verifyingContract_: "address" = token.address

        # EIP-2612 Data Fields
        owner: "address"
        spender: "address"
        value: "uint256"
        nonce: "uint256"
        deadline: "uint256" = 2 ** 256 - 1

    permit = Permit(owner=alice.address, spender=bob.address, value=2 ** 256 - 1, nonce=0)
    sig = alice.sign_message(permit)

    tx = token.permit(mock_contract, bob, 2 ** 256 - 1, 2 ** 256 - 1, sig.v, sig.r, sig.s)

    # make sure this is hit when owner is a contract
    assert tx.subcalls[0]["function"] == "isValidSignature(bytes32,bytes)"

def test_domain_separator_change(alice, token):
    src = """
owner: public(address)

@external
def __init__():
    self.owner = msg.sender
    """
    mock_minter = brownie.compile_source(src, vyper_version="0.3.1").Vyper.deploy({"from": alice})
    token.set_minter(mock_minter, {"from": alice})

    domain_separator = token.DOMAIN_SEPARATOR()
    token.set_name("New Name", "NN", {"from": alice})

    # should update
    assert token.DOMAIN_SEPARATOR() != domain_separator
