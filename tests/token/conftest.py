import pytest


@pytest.fixture(scope="session")
def alice(accounts):
    return accounts[0]


@pytest.fixture(scope="session")
def bob(accounts):
    return accounts[1]


@pytest.fixture(scope="session")
def charlie(accounts):
    return accounts[2]


@pytest.fixture(scope="module")
def token(alice, CurveTokenV5):
    return CurveTokenV5.deploy("Sample Token", "ST", {"from": alice})


@pytest.fixture(autouse=True)
def isolate(fn_isolation):
    pass

