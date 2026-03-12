"""Calendar handler: add/edit/delete/search/list Google Calendar events."""

from backend.config import settings
from backend.pipeline.models import CalendarIntentOutput, PipelineContext
from backend.services.google_calendar import get_service

_CALENDAR_ID = settings.GOOGLE_CALENDAR_ID


async def handle(ctx: PipelineContext) -> str:
    """Execute the calendar intent.

    Args:
      ctx (PipelineContext): Pipeline context; intent_data must be CalendarIntentOutput.

    Returns:
      str: Human-readable result (raw data; LLM post-processing applied if flagged).
    """
    intent_data: CalendarIntentOutput = ctx.intent_data  # type: ignore[assignment]
    service = get_service()

    match intent_data.intent:
        case "add":
            return _add(service, intent_data, ctx)
        case "edit":
            return _edit(service, intent_data)
        case "delete":
            return _delete(service, intent_data)
        case "search" | "list":
            return _list_events(service, intent_data, ctx)
        case _:
            return "I'm not sure what you want to do with your calendar."


def _add(service, intent_data: CalendarIntentOutput, ctx: PipelineContext) -> str:
    if not intent_data.title or not intent_data.start:
        return "Please provide a title and start time for the event."
    body = {
        "summary": intent_data.title,
        "start": {"dateTime": intent_data.start, "timeZone": "UTC"},
        "end": {"dateTime": intent_data.end or intent_data.start, "timeZone": "UTC"},
    }
    if intent_data.description:
        body["description"] = intent_data.description
    event = service.events().insert(calendarId=_CALENDAR_ID, body=body).execute()
    return f"Event created: \"{event['summary']}\" on {event['start']['dateTime']} (ID: {event['id']})."


def _edit(service, intent_data: CalendarIntentOutput) -> str:
    if not intent_data.event_id:
        return "Which event would you like to edit? Please provide the event ID."
    event = service.events().get(calendarId=_CALENDAR_ID, eventId=intent_data.event_id).execute()
    if intent_data.title:
        event["summary"] = intent_data.title
    if intent_data.start:
        event["start"] = {"dateTime": intent_data.start, "timeZone": "UTC"}
    if intent_data.end:
        event["end"] = {"dateTime": intent_data.end, "timeZone": "UTC"}
    if intent_data.description:
        event["description"] = intent_data.description
    updated = service.events().update(
        calendarId=_CALENDAR_ID, eventId=intent_data.event_id, body=event
    ).execute()
    return f"Event updated: \"{updated['summary']}\"."


def _delete(service, intent_data: CalendarIntentOutput) -> str:
    if not intent_data.event_id:
        return "Which event would you like to delete? Please provide the event ID."
    service.events().delete(calendarId=_CALENDAR_ID, eventId=intent_data.event_id).execute()
    return "Event deleted."


def _list_events(service, intent_data: CalendarIntentOutput, ctx: PipelineContext) -> str:
    params: dict = {
        "calendarId": _CALENDAR_ID,
        "singleEvents": True,
        "orderBy": "startTime",
        "maxResults": 10,
    }
    if ctx.date_from:
        params["timeMin"] = f"{ctx.date_from}T00:00:00Z"
    if ctx.date_to:
        params["timeMax"] = f"{ctx.date_to}T23:59:59Z"
    if intent_data.contextual_search_term:
        params["q"] = intent_data.contextual_search_term

    events_result = service.events().list(**params).execute()
    items = events_result.get("items", [])
    if not items:
        return "No events found."

    lines = []
    for e in items:
        start = e["start"].get("dateTime", e["start"].get("date", ""))
        lines.append(f"- [{e['id'][:8]}] {e['summary']} @ {start}")
    return "Events:\n" + "\n".join(lines)
