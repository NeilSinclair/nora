"""Unit tests for the router pipeline stage."""

from unittest.mock import AsyncMock, patch

import pytest

from backend.pipeline.models import RouterOutput
from backend.pipeline.router import route


@pytest.mark.asyncio
async def test_route_returns_router_output():
    mock_output = RouterOutput(route="notes", date_from=None, date_to=None, extra_context=None)
    with patch(
        "backend.pipeline.router.responses_structured", new=AsyncMock(return_value=mock_output)
    ):
        result = await route("save a note about my meeting", [])
    assert result.route == "notes"


@pytest.mark.asyncio
async def test_route_passes_history():
    mock_output = RouterOutput(route="calendar")
    history = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]
    with patch(
        "backend.pipeline.router.responses_structured", new=AsyncMock(return_value=mock_output)
    ) as mock_call:
        await route("add that to my calendar", history)
    call_args = mock_call.call_args
    messages = call_args.kwargs["messages"]
    # History messages should be included between system prompt and user message
    assert any(m["role"] == "user" and m["content"] == "hi" for m in messages)
