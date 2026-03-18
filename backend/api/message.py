"""POST /message — shared chat entry point for the React UI."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.api.deps import require_auth
from backend.pipeline.dispatcher import dispatch
from backend.pipeline.intent_parser import parse_intent
from backend.pipeline.models import PipelineContext
from backend.pipeline.router import route
from backend import state

router = APIRouter()

_WEB_USER_ID = "web"


class MessageRequest(BaseModel):
    text: str


class MessageResponse(BaseModel):
    text: str


@router.post("/message", response_model=MessageResponse, dependencies=[Depends(require_auth)])
async def message(request: MessageRequest):
    history = await state.get_history(_WEB_USER_ID)

    router_output = await route(request.text, history)
    intent_data = await parse_intent(
        route=router_output.route,
        raw_text=request.text,
        history=history,
        router_extra_context=router_output.extra_context,
    )

    ctx = PipelineContext(
        user_id=_WEB_USER_ID,
        raw_text=request.text,
        history=history,
        route=router_output.route,
        date_from=router_output.date_from,
        date_to=router_output.date_to,
        extra_context=router_output.extra_context,
        intent=intent_data.intent,
        intent_data=intent_data,
    )

    response_text = await dispatch(ctx)
    await state.append_turn(_WEB_USER_ID, request.text, response_text)

    return MessageResponse(text=response_text)
