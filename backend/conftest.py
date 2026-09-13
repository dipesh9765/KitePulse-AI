import os
import pytest

TEST_DB_PATH = os.path.join(os.path.dirname(__file__), "test_trading.db")
os.environ["TRADING_DB_PATH"] = TEST_DB_PATH

@pytest.fixture(autouse=True, scope="session")
def setup_isolated_test_database():
    os.environ["TRADING_DB_PATH"] = TEST_DB_PATH
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except Exception:
            pass

    import database
    database.init_db()

    yield

    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except Exception:
            pass
