import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
# Correctly load from the root .env file
load_dotenv(os.path.join(basedir, '..', '..', '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Celery Configuration
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL') or 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND') or 'redis://localhost:6379/0'

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'  # Use in-memory SQLite database for tests
    WTF_CSRF_ENABLED = False  # Disable CSRF for testing forms
    CELERY_TASK_ALWAYS_EAGER = True  # Run Celery tasks synchronously for testing
    SERVER_NAME = 'localhost.localdomain' # Add server name for url_for to work in tests

class DevelopmentConfig(Config):
    DEBUG = True

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'default': Config
}
