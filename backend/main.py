"""FastAPI application entry point.

Run with: uvicorn backend.main:app --reload
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import auth, calendar, message, notes, reminders, shopping_lists, voice
from backend.database import init_db
from backend.services.chroma_client import init_chroma
from backend import state


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    init_chroma()
    state.load_preferences()
    yield
    # Shutdown (nothing to clean up)


app = FastAPI(title="Nora", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(message.router)
app.include_router(notes.router)
app.include_router(shopping_lists.router)
app.include_router(reminders.router)
app.include_router(calendar.router)
app.include_router(voice.router)
