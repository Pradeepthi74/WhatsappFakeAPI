"""A local message queue; WhatsApp sending is always manual."""

import logging
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, current_app, g, jsonify, render_template, request
from werkzeug.exceptions import BadRequest, HTTPException


def timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def database():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"], timeout=10)
        g.db.row_factory = sqlite3.Row
    return g.db


def json_body():
    if not request.is_json:
        raise BadRequest("A JSON object is required")
    try:
        body = request.get_json()
    except BadRequest:
        raise BadRequest("Invalid JSON") from None
    if not isinstance(body, dict):
        raise BadRequest("A JSON object is required")
    return body


def create_app(config=None):
    app = Flask(__name__)
    app.config["DATABASE"] = str(Path(app.instance_path) / "messages.db")
    if config:
        app.config.update(config)

    @app.teardown_appcontext
    def close_database(error=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    with app.app_context():
        Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)
        with database() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phone TEXT NOT NULL,
                    message TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'sent')),
                    created_at TEXT NOT NULL,
                    sent_at TEXT
                )
            """)

    @app.get("/")
    def dashboard():
        return render_template("index.html")

    @app.get("/api/messages")
    def list_messages():
        rows = database().execute(
            "SELECT * FROM messages ORDER BY created_at DESC, id DESC LIMIT 100"
        ).fetchall()
        return jsonify(success=True, data=[dict(row) for row in rows])

    @app.post("/api/messages")
    def create_message():
        app.logger.info("Message creation request received")
        body = json_body()
        phone, message = body.get("phone"), body.get("message")
        if not isinstance(phone, str) or not phone.strip():
            raise BadRequest("phone is required and must be a string")
        phone = re.sub(r"[+\s\-()\[\]]", "", phone)
        if not re.fullmatch(r"[1-9][0-9]{1,14}", phone):
            raise BadRequest("phone must contain 2–15 international digits, starting with 1–9")
        if not isinstance(message, str) or not message.strip():
            raise BadRequest("message is required and must be a non-empty string")
        db = database()
        with db:
            cursor = db.execute(
                "INSERT INTO messages (phone, message, created_at) VALUES (?, ?, ?)",
                (phone, message, timestamp()),
            )
        row = db.execute("SELECT * FROM messages WHERE id = ?", (cursor.lastrowid,)).fetchone()
        app.logger.info("Message %s created", row["id"])
        return jsonify(success=True, data=dict(row)), 201

    @app.patch("/api/messages/<int:message_id>/status")
    def change_status(message_id):
        status = json_body().get("status")
        if status not in ("pending", "sent"):
            raise BadRequest("status must be pending or sent")
        db = database()
        with db:
            cursor = db.execute(
                "UPDATE messages SET status = ?, sent_at = ? WHERE id = ?",
                (status, timestamp() if status == "sent" else None, message_id),
            )
            if cursor.rowcount == 0:
                return jsonify(success=False, error="Message not found"), 404
        row = db.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()
        app.logger.info("Message %s status changed to %s", message_id, status)
        return jsonify(success=True, data=dict(row))

    @app.after_request
    def no_api_cache(response):
        if request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.errorhandler(HTTPException)
    def request_error(error):
        return jsonify(success=False, error=error.description), error.code

    @app.errorhandler(Exception)
    def unexpected_error(error):
        app.logger.exception("Unexpected application error")
        return jsonify(success=False, error="Unexpected server error"), 500

    return app


logging.basicConfig(level=logging.INFO)
app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
