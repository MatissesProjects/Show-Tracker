import pytest
from app import create_app
from database import db
import os

@pytest.fixture
def app():
    # Create app with overrides to use in-memory DB
    app = create_app(config_override={
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'INIT_DB': False
    })

    with app.app_context():
        import models # Ensure models are loaded
        db.create_all()
        yield app
        db.session.remove() # Clean up session
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()