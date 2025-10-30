import pytest
from unittest.mock import MagicMock

from blackjack_simulator.app import create_app, db
from blackjack_simulator.config import TestingConfig

@pytest.fixture(scope='function')
def app():
    """Instantiates the Flask app for testing and sets up the database."""
    app = create_app(config_class=TestingConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture(scope='function')
def client(app):
    """Provides a test client for making requests to the app."""
    return app.test_client()

@pytest.fixture
def mock_celery_task(monkeypatch):
    """
    Mocks the celery.send_task function to avoid actual task execution.
    """
    mock_task_instance = MagicMock()
    mock_task_instance.id = 'test_task_12345'
    
    mock_send_task = MagicMock(return_value=mock_task_instance)
    
    # Correct path to where celery.send_task is imported and used
    monkeypatch.setattr('blackjack_simulator.routes.celery.send_task', mock_send_task)
    
    return mock_send_task
