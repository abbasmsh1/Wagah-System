"""Smoke tests: app boots, auth gates hold, CSRF rejects, login flow works."""
import os
import tempfile

# Must be set before importing the app: settings are cached at import time.
_db_path = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["COOKIE_SECURE"] = "False"
os.environ["ALLOWED_HOSTS"] = '["testserver"]'
os.environ["DEBUG"] = "False"

import pytest
from fastapi.testclient import TestClient

from database import init_db, SessionLocal, User
from config.security import get_password_hash
from main import app


@pytest.fixture(scope="session")
def client():
    init_db()
    db = SessionLocal()
    try:
        db.add(User(
            username="testadmin",
            hashed_password=get_password_hash("Testpass1!"),
            role="admin",
            designation="Test",
            is_active=True,
        ))
        db.commit()
    finally:
        db.close()
    with TestClient(app) as c:
        yield c


def login(client):
    client.get("/login")
    csrf = client.cookies["csrf_token"]
    return client.post(
        "/login",
        data={"username": "testadmin", "password": "Testpass1!", "csrf_token": csrf},
        follow_redirects=False,
    )


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_login_page(client):
    response = client.get("/login")
    assert response.status_code == 200
    # Set on the first response of the session; lives in the client jar after.
    assert "csrf_token" in client.cookies


def test_admin_requires_auth(client):
    response = client.get("/admin/dashboard", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_post_without_csrf_rejected(client):
    response = client.post("/login", data={"username": "x", "password": "y"})
    assert response.status_code == 403


def test_login_flow_reaches_admin(client):
    response = login(client)
    assert response.status_code == 303
    assert "access_token" in response.cookies
    dashboard = client.get("/admin/dashboard")
    assert dashboard.status_code == 200
