# Nora - AI Notetaker

## Project Overview
Nora is an AI Notetaker and calendar manager that is accessible through two means. The first is through Telegram as a telegram bot and the second is through a basic React webapp. Nora enables the user to do various things as outlined below.
In order to pick the correct task to do, Nora uses a structured output router built with the OpenAI API/SDK.

### Backend Functionality

The user can communicate with Nora using both text and voice notes from Telegram. The user can turn on (or off) voice responses from Nora by indicating that it wants to speak (or not speak) back

#### Calendar

- Add, delete, edit, read calendar items for a Google calendar access through the Google Calendar API

#### Notes

- Add, edit, delete notes
- Tag notes
- Link notes with a relationship <note1> -> <relationship> -> <note2>
- Search notes, via tags and / or semantic search
- Notes are saved based on their date as data/notes/YYMMDD-HHMM
- Notes can be archived, then they are stored in data/notes/archive

#### Shopping Lists

- Add, edit, delete shopping lists
- Shopping lists are saved in data/shopping_lists as .txt files with today's date
- Shopping lists can be archived, then they are stored in data/shopping_lists/archive

#### Reminders

- Add, edit and delete reminders
- Reminders are stored in a json file in data/reminders/reminders.json
- The reminders are send to the user through Telegram using a chron job that checks for reminders in the reminders.json

### UI Functionality

The UI consists of a basic React-based UI. The chat section is on the left hand side as a side bar which takes up 60% of the side bar. Below that are three buttons, one below the other that have the sections notes, reminders and calendar. When the user clicks on notes, reminders or calendar, it brings up the relevant screen in the main area on the right hand side

#### Chat section

On the left hand side is a chat side panel where the user can chat with the AI. The AI it chats with is the same as the AI the user chats with through Telegram. The functionality is the same in as much as the user can send through both text and voice messages and receive back both text and voice messages.

#### Notes

The user can search for notes by chatting to Nora. Notes can be returned via tag or semantic search (see Backend Functionality). When a note is returned we see that note in a square box with the note and the tags. We also see all of the other notes which are connected with it, including their relationship. These other notes are shown as smaller boxes to the sides of the main note with lines connecting them.

Shopping lists are stored under notes. These do not have a title and are not connected and can be searched for by date.

#### Calendar

This is basic React calendar widget with our calendar items in it shown in the main part of the display. It really just looks like Google calendar and has the same functionality - i.e. move across months, click on dates and add, edit, delete, read calendar items.

#### Reminders

This is a basic React widget which shows us our reminders and the date and time they will be sent to us in the main part of the display. We can add, edit, delete these. 

#### Login 

A basic login screen with just a password. There's a cookie to remain signed in. Do we need some kind of security cookie during the session?

## Workflow Overview

### Telegram 

When interacting with the bot from Telegram the workflow looks like the following

- The user sends a message (either text or voice) with the bot to the backend
- Voice messages are transcribed to text
- Messages are then routed using a structured outputs (https://developers.openai.com/api/docs/guides/structured-outputs/) router. The Structured Outputs Router captures the route where the routes are explained in the system prompt and defined with a Pydantic object. Additional information like date_to, date_from (both optional) as well as any additional information can be captured by this router that will be helpful downstream are.
- The user is routed in the background to calendar, notes, reminders, shopping lists, free-form chat or help

## Workflow Deepdive

- <I'd like you, Claude, to help me write this>

## Coding Conventions

Be conservative and concise, but also helpful with your comments. Add comments to code where some operation might not
be clearly obvious. 

### Function Docstrings

def function_name(parameter_1 : type, parameter_2: type) -> returnType:
    """Summary of what the function does.
    More detailed description if necessary

    Args:
      argument_name (type): description.

    Returns:
      returnType: description.
  """ 

### Tests

Write unit tests with pytest and store in a folder tests. Run the tests whenever something is pushed to github.

### Linting
Use ruff for linting (https://docs.astral.sh/ruff/)

## Key Dependencies

- Telegram SDK including job-queue
- OpenAI SDK
- React (You need to version this)

