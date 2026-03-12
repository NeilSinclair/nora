"""Integration tests for the /auth endpoint."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock


@pytest.fixture
def client():
    # Patch lifespan dependencies so we don't need real DB/Qdrant/prefs on import
    with patch("backend.database.init_db"), \
         patch("backend.services.qdrant_client.ensure_collection", new=AsyncMock()), \
         patch("backend.state.load_preferences"):
        from backend.main import app
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c


def test_login_correct_password(client):
    with patch("backend.config.settings.PASSWORD", "secret"):
        resp = client.post("/auth", json={"password": "secret"})
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    assert "session" in resp.cookies


def test_login_wrong_password(client):
    with patch("backend.config.settings.PASSWORD", "secret"):
        resp = client.post("/auth", json={"password": "wrong"})
    assert resp.status_code == 401


def test_logout_clears_cookie(client):
    resp = client.post("/auth/logout")
    assert resp.status_code == 200
