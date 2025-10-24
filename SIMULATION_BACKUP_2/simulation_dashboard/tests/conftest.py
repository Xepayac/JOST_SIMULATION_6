
import pytest
from simulation_dashboard.app import app as flask_app, db

@pytest.fixture(scope='module')
def app():
    """Create and configure a new app instance for each test module."""
    flask_app.config['TESTING'] = True
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    # Create the database and the database tables
    with flask_app.app_context():
        db.create_all()

    yield flask_app

    # Tear down the database
    with flask_app.app_context():
        db.drop_all()

@pytest.fixture(scope='module')
def client(app):
    """A test client for the app."""
    return app.test_client()
