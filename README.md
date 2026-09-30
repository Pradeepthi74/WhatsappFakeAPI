# WhatsApp Message Queue

A small Flask application that receives phone numbers and messages through an API, stores them in SQLite, and displays them in a dashboard. It uses simple HTML, CSS, and JavaScript with no frontend build step.

## Local setup

Requires Python 3.9 or newer. From the project folder:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Open **http://127.0.0.1:5000** in your browser. Stop the server with **Ctrl+C**.

For later runs:

```sh
source .venv/bin/activate
python app.py
```

The application automatically creates `instance/messages.db`. Messages remain saved when you restart the app.

## How it works

1. An external application sends a phone number and message to `POST /api/messages`.
2. The app normalizes the phone number and saves the message with a `pending` status and creation timestamp.
3. The dashboard loads the latest 100 messages, newest first, and checks for updates every three seconds.
4. Click **Open WhatsApp** to open a chat with the recipient and message pre-filled. Press **Send** manually in WhatsApp.
5. Check **Sent** in the dashboard after sending. The saved checkbox state survives refreshes and restarts. Unchecking it changes the status back to `pending`.

The application does **not** send WhatsApp messages automatically. Opening a chat does not mark the message as sent.

The dashboard also supports manual refresh and sorting by newest, oldest, pending, or sent. Creation times display in your browser's local timezone.

## Add a test message

With the server running, use another terminal:

```sh
curl -i http://127.0.0.1:5000/api/messages \
  -H 'Content-Type: application/json' \
  -d '{"phone":"+91 98765 43210","message":"Hello, this is a test message."}'
```

Use your own full international phone number to test WhatsApp. Supply the phone as a string, including the country code; the app removes formatting characters but does not infer a country code. A successful request returns HTTP **201** and the saved record.

## API

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/messages` | Create a message using `{"phone":"919876543210","message":"Hello"}`. |
| GET | `/api/messages` | Return the latest 100 messages, newest first. |
| PATCH | `/api/messages/<id>/status` | Save `{"status":"sent"}` or `{"status":"pending"}`. |

Marking a message sent saves `sent_at`; marking it pending clears that timestamp. Responses use `success` with either `data` or `error`.

## Project files

- `app.py`: Flask API and SQLite storage.
- `templates/index.html`: dashboard, styles, and JavaScript.
- `requirements.txt`: Flask dependency.
- `.gitignore`: excludes `docs/`, virtual environments, databases, and caches.

Development and hosting guides are kept locally under the ignored `docs/` folder. The current app has no authentication; add dashboard and API protection before exposing real message data publicly.
