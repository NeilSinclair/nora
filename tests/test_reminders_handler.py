"""Unit tests for the reminders handler."""

import json

import pytest

from backend.handlers.reminders import handle
from backend.pipeline.models import PipelineContext, RemindersIntentOutput


def _make_ctx(intent_data: RemindersIntentOutput) -> PipelineContext:
    ctx = PipelineContext(user_id="test", raw_text="")
    ctx.route = "reminders"
    ctx.intent = intent_data.intent
    ctx.intent_data = intent_data
    return ctx


@pytest.mark.asyncio
async def test_add_reminder(tmp_data_dir):
    intent = RemindersIntentOutput(intent="add", text="Buy milk", remind_at="2026-04-01T09:00:00")
    result = await handle(_make_ctx(intent))
    assert "Buy milk" in result

    reminders_file = tmp_data_dir / "reminders" / "reminders.json"
    data = json.loads(reminders_file.read_text())
    assert len(data["reminders"]) == 1
    assert data["reminders"][0]["text"] == "Buy milk"


@pytest.mark.asyncio
async def test_list_reminders_empty(tmp_data_dir):
    intent = RemindersIntentOutput(intent="list")
    result = await handle(_make_ctx(intent))
    assert "no upcoming" in result.lower()


@pytest.mark.asyncio
async def test_delete_reminder(tmp_data_dir):
    # First add
    add_intent = RemindersIntentOutput(intent="add", text="Test", remind_at="2026-04-01T09:00:00")
    await handle(_make_ctx(add_intent))

    reminders_file = tmp_data_dir / "reminders" / "reminders.json"
    rid = json.loads(reminders_file.read_text())["reminders"][0]["id"]

    # Then delete
    del_intent = RemindersIntentOutput(intent="delete", reminder_id=rid)
    result = await handle(_make_ctx(del_intent))
    assert "deleted" in result.lower()

    data = json.loads(reminders_file.read_text())
    assert data["reminders"] == []
