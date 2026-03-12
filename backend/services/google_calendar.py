"""Google Calendar service built from a service account credential.

The user shares their calendar with the service account email address.
The service object is cached as a module-level singleton.
"""

from google.oauth2 import service_account
from googleapiclient.discovery import build

from backend.config import settings

_SCOPES = ["https://www.googleapis.com/auth/calendar"]

_service = None


def get_service():
    """Return a cached Google Calendar API service object.

    Returns:
      googleapiclient.discovery.Resource: Authenticated Calendar service.
    """
    global _service
    if _service is None:
        creds = service_account.Credentials.from_service_account_file(
            settings.GOOGLE_SERVICE_ACCOUNT_FILE,
            scopes=_SCOPES,
        )
        _service = build("calendar", "v3", credentials=creds, cache_discovery=False)
    return _service
