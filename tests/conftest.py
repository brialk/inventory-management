import pytest

import app as app_module


@pytest.fixture
def client():
    """A fresh test client with an empty inventory for every test."""
    app_module.inventory.clear()
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()