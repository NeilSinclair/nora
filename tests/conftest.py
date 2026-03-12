"""Shared pytest fixtures."""

import sqlite3
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def tmp_data_dir(tmp_path: Path, monkeypatch):
    """Redirect all data paths to a temporary directory."""
    (tmp_path / "notes" / "archive").mkdir(parents=True)
    (tmp_path / "shopping_lists" / "archive").mkdir(parents=True)
    (tmp_path / "reminders").mkdir()
    (tmp_path / "reminders" / "reminders.json").write_text('{"reminders": []}')

    monkeypatch.setattr("backend.config.settings.DATA_DIR", tmp_path)
    return tmp_path


@pytest.fixture
def mock_openai():
    """Mock OpenAI client responses."""
    with patch("backend.services.openai_client.get_client") as mock:
        client = MagicMock()
        client.responses.create = AsyncMock(return_value=MagicMock(output_text="{}"))
        client.embeddings.create = AsyncMock(
            return_value=MagicMock(data=[MagicMock(embedding=[0.0] * 1536)])
        )
        mock.return_value = client
        yield client


@pytest.fixture
def mock_qdrant():
    """Mock Qdrant client operations."""
    with patch("backend.services.qdrant_client.get_client") as mock:
        client = MagicMock()
        client.get_collections = AsyncMock(return_value=MagicMock(collections=[]))
        client.create_collection = AsyncMock()
        client.upsert = AsyncMock()
        client.search = AsyncMock(return_value=[])
        client.delete = AsyncMock()
        mock.return_value = client
        yield client
