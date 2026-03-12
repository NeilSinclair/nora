"""REST endpoints for Google Calendar events."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.api.deps import require_auth
from backend.config import settings
from backend.services.google_calendar import get_service

router = APIRouter(prefix="/calendar", dependencies=[Depends(require_auth)])

_CALENDAR_ID = settings.GOOGLE_CALENDAR_ID


class EventCreate(BaseModel):
    title: str
    start: str   # ISO datetime string
    end: str     # ISO datetime string
    description: str | None = None


class EventUpdate(BaseModel):
    title: str | None = None
    start: str | None = None
    end: str | None = None
    description: str | None = None


@router.get("/events")
async def list_events(time_min: str | None = None, time_max: str | None = None, q: str | None = None):
    service = get_service()
    params: dict = {
        "calendarId": _CALENDAR_ID,
        "singleEvents": True,
        "orderBy": "startTime",
        "maxResults": 50,
    }
    if time_min:
        params["timeMin"] = time_min
    if time_max:
        params["timeMax"] = time_max
    if q:
        params["q"] = q
    result = service.events().list(**params).execute()
    return {"events": result.get("items", [])}


@router.post("/events", status_code=201)
async def create_event(body: EventCreate):
    service = get_service()
    event_body = {
        "summary": body.title,
        "start": {"dateTime": body.start, "timeZone": "UTC"},
        "end": {"dateTime": body.end, "timeZone": "UTC"},
    }
    if body.description:
        event_body["description"] = body.description
    event = service.events().insert(calendarId=_CALENDAR_ID, body=event_body).execute()
    return event


@router.patch("/events/{event_id}")
async def update_event(event_id: str, body: EventUpdate):
    service = get_service()
    event = service.events().get(calendarId=_CALENDAR_ID, eventId=event_id).execute()
    if body.title:
        event["summary"] = body.title
    if body.start:
        event["start"] = {"dateTime": body.start, "timeZone": "UTC"}
    if body.end:
        event["end"] = {"dateTime": body.end, "timeZone": "UTC"}
    if body.description is not None:
        event["description"] = body.description
    return service.events().update(calendarId=_CALENDAR_ID, eventId=event_id, body=event).execute()


@router.delete("/events/{event_id}", status_code=204)
async def delete_event(event_id: str):
    service = get_service()
    service.events().delete(calendarId=_CALENDAR_ID, eventId=event_id).execute()
