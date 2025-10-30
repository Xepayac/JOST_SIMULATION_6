import pytest
from blackjack_simulator.app import create_app, db as _db, init_db


@pytest.fixture(scope='function')
def app():
    """Function-wide test Flask application."""
    app = create_app('testing')
    with app.app_context():
        _db.create_all()
        init_db()  # Initialize the database with default profiles
        yield app
        _db.drop_all()


@pytest.fixture()
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()
