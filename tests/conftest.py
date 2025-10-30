import pytest
from blackjack_simulator.app import create_app, init_db
from blackjack_simulator.config import TestingConfig
from blackjack_simulator.models import db

@pytest.fixture(scope='function')
def app():
    """Create and configure a new app instance for each test."""
    app = create_app(config_class=TestingConfig)

    with app.app_context():
        db.create_all()
        init_db()
        yield app
        db.drop_all()

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()
