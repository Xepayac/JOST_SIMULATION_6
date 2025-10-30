import pytest
from blackjack_simulator.app import create_app
from blackjack_simulator.app import db as _db

@pytest.fixture(scope='session')
def app():
    """Create a new app instance for each test."""
    app = create_app('testing')
    app.config['SERVER_NAME'] = 'localhost'
    return app

@pytest.fixture
def client(app):
    """A test client for the app."""
    with app.test_request_context():
        yield app.test_client()

@pytest.fixture(scope='session')
def db(app):
    """Session-wide test database."""
    with app.app_context():
        _db.create_all()
        yield _db
        _db.drop_all()
