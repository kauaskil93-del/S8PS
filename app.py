import os
import sqlite3
import time
import uuid
from contextlib import closing
from flask import Flask, jsonify, request

app = Flask(__name__)

VERSION = "3.0.0l"
DB_PATH = os.environ.get("DB_PATH", "asphalt8_test.db")


# -----------------------------
# Database
# -----------------------------

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with closing(db()) as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS players (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            level INTEGER NOT NULL DEFAULT 1,
            created_at INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id TEXT NOT NULL,
            score INTEGER NOT NULL DEFAULT 0,
            created_at INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS rooms (
            id TEXT PRIMARY KEY,
            host_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'waiting',
            created_at INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS room_players (
            room_id TEXT NOT NULL,
            player_id TEXT NOT NULL,
            joined_at INTEGER NOT NULL,
            PRIMARY KEY(room_id, player_id)
        );
        """)
        conn.commit()


init_db()


def now():
    return int(time.time())


def ensure_player(player_id=None, name="TestPlayer"):
    player_id = str(player_id or uuid.uuid4())

    with closing(db()) as conn:
        row = conn.execute(
            "SELECT * FROM players WHERE id = ?", (player_id,)
        ).fetchone()

        if row is None:
            conn.execute(
                "INSERT INTO players(id, name, level, created_at) VALUES (?, ?, ?, ?)",
                (player_id, name[:32], 1, now()),
            )
            conn.commit()

    return player_id


def json_error(message, status=400):
    return jsonify({
        "status": 1,
        "result": "error",
        "message": message
    }), status


# -----------------------------
# Basic server/config endpoints
# -----------------------------

@app.get("/")
def index():
    return jsonify({
        "status": 0,
        "result": "ok",
        "server": "asphalt8-test",
        "version": VERSION
    })


@app.get("/api/status")
def api_status():
    return jsonify({
        "status": 0,
        "result": "success",
        "server": "asphalt8-test",
        "version": VERSION,
        "time": now()
    })


@app.route("/api/public/app/config", methods=["GET", "POST"])
def app_config():
    return jsonify({
        "status": 0,
        "result": "success",
        "version": VERSION,
        "environment": "test",
        "features": {
            "profile": True,
            "leaderboard": True,
            "rooms": True,
            "automatch": True,
            "multiplayer": True
        }
    })


# Test equivalent for a client that requests a datacenter list.
# It deliberately returns the test service rather than an official endpoint.
@app.route("/config/<path:config_path>/datacenters", methods=["GET", "POST"])
@app.route("/config/<path:config_path>/datacenters/", methods=["GET", "POST"])
def datacenters(config_path):
    return jsonify({
        "status": 0,
        "result": "success",
        "version": VERSION,
        "environment": "test",
        "datacenters": [{
            "name": "test",
            "host": request.host,
            "port": int(os.environ.get("PORT", 10000)),
            "protocol": "http"
        }]
    })


@app.route("/urls", methods=["GET", "POST"])
def urls():
    base = request.host_url.rstrip("/")

    return jsonify({
        "status": 0,
        "result": "success",
        "version": VERSION,
        "urls": {
            "api": base,
            "profile": base + "/profiles",
            "rooms": base + "/rooms",
            "automatch": base + "/automatch"
        }
    })


# -----------------------------
# Social connection test
# -----------------------------

@app.route("/social_player.php", methods=["GET", "POST"])
@app.route("/ope/social_player.php", methods=["GET", "POST"])
def social_player():
    action = request.args.get("action", "")
    player_id = (
        request.values.get("player_id")
        or request.values.get("profileId")
    )

    if player_id:
        ensure_player(player_id)

    print(
        "[social_player.php]",
        "action=", action,
        "player_id=", player_id,
        "game_version=", request.values.get("game_version")
    )

    if action == "logConnectStatus":
        return jsonify({
            "status": 0,
            "result": "success",
            "message": "connected"
        })

    return jsonify({
        "status": 0,
        "domain": "test",
        "port": "0"
    })


# -----------------------------
# Profile API
# -----------------------------

@app.route("/data/me", methods=["GET", "POST"])
def data_me():
    player_id = (
        request.values.get("player_id")
        or request.values.get("profileId")
        or request.values.get("id")
    )

    if not player_id:
        player_id = str(uuid.uuid4())

    ensure_player(player_id)

    with closing(db()) as conn:
        player = conn.execute(
            "SELECT * FROM players WHERE id = ?", (player_id,)
        ).fetchone()

    return jsonify({
        "status": 0,
        "result": "success",
        "player": dict(player)
    })


@app.route("/profiles", methods=["GET", "POST"])
def profiles():
    player_id = (
        request.values.get("player_id")
        or request.values.get("profileId")
        or request.values.get("id")
    )

    name = request.values.get("name", "TestPlayer")

    player_id = ensure_player(player_id, name)

    with closing(db()) as conn:
        player = conn.execute(
            "SELECT * FROM players WHERE id = ?", (player_id,)
        ).fetchone()

    return jsonify({
        "status": 0,
        "result": "success",
        "profile": dict(player)
    })


@app.route("/profiles/<player_id>", methods=["GET", "POST"])
def profile(player_id):
    ensure_player(player_id)

    with closing(db