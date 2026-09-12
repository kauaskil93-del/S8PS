import os
import sqlite3
import time
import uuid
from contextlib import closing

from flask import Flask, jsonify, request

app = Flask(__name__)

VERSION = "3.0.0l"
SERVER_NAME = "asphalt8-test"
DB_PATH = os.environ.get("DB_PATH", "asphalt8_test.db")


# ---------------------------------------------------------
# Database
# ---------------------------------------------------------

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def now():
    return int(time.time())


def init_db():
    with closing(db()) as conn:
        conn.executescript(
            """
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
                PRIMARY KEY (room_id, player_id)
            );
            """
        )
        conn.commit()


init_db()


def ensure_player(player_id=None, name="TestPlayer"):
    player_id = str(player_id or uuid.uuid4())
    safe_name = str(name or "TestPlayer")[:32]

    with closing(db()) as conn:
        row = conn.execute(
            "SELECT id FROM players WHERE id = ?",
            (player_id,),
        ).fetchone()

        if row is None:
            conn.execute(
                """
                INSERT INTO players(id, name, level, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (player_id, safe_name, 1, now()),
            )
            conn.commit()

    return player_id


def json_error(message, status=400):
    return jsonify(
        {
            "status": 1,
            "result": "error",
            "message": message,
        }
    ), status


# ---------------------------------------------------------
# Basic status/config
# ---------------------------------------------------------

@app.get("/")
def index():
    return jsonify(
        {
            "status": 0,
            "result": "ok",
            "server": SERVER_NAME,
            "version": VERSION,
        }
    )


@app.get("/api/status")
def api_status():
    return jsonify(
        {
            "status": 0,
            "result": "success",
            "server": SERVER_NAME,
            "version": VERSION,
            "time": now(),
        }
    )


@app.route("/api/public/app/config", methods=["GET", "POST"])
def app_config():
    return jsonify(
        {
            "status": 0,
            "result": "success",
            "version": VERSION,
            "environment": "test",
            "features": {
                "profile": True,
                "leaderboard": True,
                "rooms": True,
                "automatch": True,
                "multiplayer": True,
            },
        }
    )


@app.route(
    "/config/<path:config_path>/datacenters",
    methods=["GET", "POST"],
)
@app.route(
    "/config/<path:config_path>/datacenters/",
    methods=["GET", "POST"],
)
def datacenters(config_path):
    # Render exposes the service through HTTPS while the Flask process
    # listens on the internal PORT supplied by Render.
    return jsonify(
        {
            "status": 0,
            "result": "success",
            "version": VERSION,
            "environment": "test",
            "datacenters": [
                {
                    "name": "test",
                    "host": request.host,
                    "port": 443,
                    "protocol": "https",
                }
            ],
        }
    )


@app.route("/urls", methods=["GET", "POST"])
def urls():
    base = request.host_url.rstrip("/")

    return jsonify(
        {
            "status": 0,
            "result": "success",
            "version": VERSION,
            "urls": {
                "api": base,
                "profile": base + "/profiles",
                "rooms": base + "/rooms",
                "automatch": base + "/automatch",
            },
        }
    )


# ---------------------------------------------------------
# Social/player endpoints
# ---------------------------------------------------------

@app.route("/social_player.php", methods=["GET", "POST"])
@app.route("/ope/social_player.php", methods=["GET", "POST"])
def social_player():
    action = request.values.get("action", "")
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
        "game_version=", request.values.get("game_version"),
    )

    if action == "logConnectStatus":
        return jsonify(
            {
                "status": 0,
                "result": "success",
                "message": "connected",
            }
        )

    return jsonify(
        {
            "status": 0,
            "domain": "test",
            "port": "0",
        }
    )


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
            "SELECT * FROM players WHERE id = ?",
            (player_id,),
        ).fetchone()

    return jsonify(
        {
            "status": 0,
            "result": "success",
            "player": dict(player),
        }
    )


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
            "SELECT * FROM players WHERE id = ?",
            (player_id,),
        ).fetchone()

    return jsonify(
        {
            "status": 0,
            "result": "success",
            "profile": dict(player),
        }
    )


@app.route("/profiles/<player_id>", methods=["GET", "POST"])
def profile(player_id):
    ensure_player(player_id)

    with closing(db()) as conn:
        row = conn.execute(
            "SELECT * FROM players WHERE id = ?",
            (player_id,),
        ).fetchone()

    return jsonify(
        {
            "status": 0,
            "result": "success",
            "profile": dict(row),
        }
    )


@app.route("/api/profile/<player_id>", methods=["GET", "POST"])
def api_profile(player_id):
    return profile(player_id)


@app.route("/profiles/me/myprofile", methods=["GET", "POST"])
def my_profile():
    player_id = (
        request.values.get("player_id")
        or request.values.get("profileId")
        or request.values.get("id")
    )

    if not player_id:
        player_id = str(uuid.uuid4())

    ensure_player(player_id)

    with closing(db()) as conn:
        row = conn.execute(
            "SELECT * FROM players WHERE id = ?",
            (player_id,),
        ).fetchone()

    return jsonify(
        {
            "status": 0,
            "result": "success",
            "profile": dict(row),
        }
    )


@app.route(
    "/profiles/me/myprofile/delete",
    methods=["GET", "POST"],
)
def delete_profile():
    player_id = (
        request.values.get("player_id")
        or request.values.get("profileId")
    )

    if not player_id:
        return json_error("player_id is required")

    with closing(db()) as conn:
        conn.execute(
            "DELETE FROM players WHERE id = ?",
            (player_id,),
        )
        conn.execute(
            "DELETE FROM scores WHERE player_id = ?",
            (player_id,),
        )
        conn.execute(
            "DELETE FROM room_players WHERE player_id = ?",
            (player_id,),
        )
        conn.commit()

    return jsonify(
        {
            "status": 0,
            "result": "success",
        }
    )


@app.route(
    "/profiles/me/myprofile/visibility",
    methods=["GET", "POST"],
)
def visibility():
    return jsonify(
        {
            "status": 0,
            "result": "success",
            "visibility": "public",
        }
    )


@app.route("/profiles/matchers/", methods=["GET", "POST"])
def matchers():
    return jsonify(
        {
            "status": 0,
            "result": "success",
            "matchers": [],
        }
    )


@app.route("/profiles/location/", methods=["GET", "POST"])
def profile_location():
    return jsonify(
        {
            "status": 0,
            "result": "success",
            "location": None,
        }
    )


# ---------------------------------------------------------
# Leaderboard
# ---------------------------------------------------------

@app.route("/api/leaderboard", methods=["GET", "POST"])
@app.route(
    "/game_api_leaderboard_WORLD_SERIES",
    methods=["GET", "POST"],
)
def leaderboard():
    with closing(db()) as conn:
        rows = conn.execute(
            """
            SELECT p.id, p.name, p.level,
                   MAX(s.score) AS score
            FROM players p
            LEFT JOIN scores s
                ON s.player_id = p.id
            GROUP BY p.id
            ORDER BY score DESC, p.name ASC
            LIMIT 50
            """
        ).fetchall()

    entries = []

    for rank, row in enumerate(rows, 1):
        entries.append(
            {
                "rank": rank,
                "player_id": row["id"],
                "name": row["name"],
                "level": row["level"],
                "score": row["score"] or 0,
            }
        )

    return jsonify(
        {
            "status": 0,
            "result": "success",
            "entries": entries,
        }
    )


@app.route("/api/leaderboard/score", methods=["POST"])
def submit_score():
    player_id = request.values.get("player_id")

    if not player_id:
        return json_error("player_id is required")

    try:
        score = int(request.values.get("score", 0))
    except (TypeError, ValueError):
        return json_error("score must be an integer")

    score = max(0, min(score, 2_000_000_000))
    ensure_player(player_id)

    with closing(db()) as conn:
        conn.execute(
            """
            INSERT INTO scores(
                player_id, score, created_at
            )
            VALUES (?, ?, ?)
            """,
            (player_id, score, now()),
        )
        conn.commit()

    return jsonify(
        {
            "status": 0,
            "result": "success",
            "score": score,
        }
    )


# ---------------------------------------------------------
# Rooms / test multiplayer
# ---------------------------------------------------------

def room_payload(conn, room_id):
    room = conn.execute(
        "SELECT * FROM rooms WHERE id = ?",
        (room_id,),
    ).fetchone()

    if room is None:
        return None

    players = conn.execute(
        """
        SELECT p.id, p.name, p.level
        FROM room_players rp
        JOIN players p
            ON p.id = rp.player_id
        WHERE rp.room_id = ?
        ORDER BY rp.joined_at ASC
        """,
        (room_id,),
    ).fetchall()

    return {
        "id": room["id"],
        "host_id": room["host_id"],
        "status": room["status"],
        "players": [dict(player) for player in players],
    }


@app.route("/rooms/", methods=["GET", "POST"])
@app.route("/rooms", methods=["GET", "POST"])
def rooms():
    if request.method == "GET":
        with closing(db()) as conn:
            rows = conn.execute(
                """
                SELECT * FROM rooms
                WHERE status = 'waiting'
                ORDER BY created_at ASC
                LIMIT 50
                """
            ).fetchall()

            result = [
                room_payload(conn, room["id"])
                for room in rows
            ]

        return jsonify(
            {
                "status": 0,
                "result": "success",
                "rooms": result,
            }
        )

    player_id = (
        request.values.get("player_id")
        or str(uuid.uuid4())
    )
    ensure_player(player_id)

    room_id = str(uuid.uuid4())

    with closing(db()) as conn:
        conn.execute(
            """
            INSERT INTO rooms(
                id, host_id, status, created_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (room_id, player_id, "waiting", now()),
        )

        conn.execute(
            """
            INSERT INTO room_players(
                room_id, player_id, joined_at
            )
            VALUES (?, ?, ?)
            """,
            (room_id, player_id, now()),
        )

        conn.commit()
        payload = room_payload(conn, room_id)

    return jsonify(
        {
            "status": 0,
            "result": "success",
            "room": payload,
        }
    )


@app.route("/rooms/<room_id>", methods=["GET"])
def get_room(room_id):
    with closing(db()) as conn:
        payload = room_payload(conn, room_id)

    if payload is None:
        return json_error("room not found", 404)

    return jsonify(
        {
            "status": 0,
            "result": "success",
            "room": payload,
        }
    )


@app.route("/rooms/<room_id>/join", methods=["GET", "POST"])
def join_room(room_id):
    player_id = request.values.get("player_id")

    if not player_id:
        return json_error("player_id is required")

    ensure_player(player_id)

    with closing(db()) as conn:
        room = conn.execute(
            "SELECT * FROM rooms WHERE id = ?",
            (room_id,),
        ).fetchone()

        if room is None:
            return json_error("room not found", 404)

        if room["status"] != "waiting":
            return json_error("room is not waiting", 409)

        conn.execute(
            """
            INSERT OR IGNORE INTO room_players(
                room_id, player_id, joined_at
            )
            VALUES (?, ?, ?)
            """,
            (room_id, player_id, now()),
        )

        count = conn.execute(
            """
            SELECT COUNT(*)
            FROM room_players
            WHERE room_id = ?
            """,
            (room_id,),
        ).fetchone()[0]

        if count >= 2:
            conn.execute(
                "UPDATE rooms SET status = 'ready' WHERE id = ?",
                (room_id,),
            )

        conn.commit()
        payload = room_payload(conn, room_id)

    return jsonify(
        {
            "status": 0,
            "result": "success",
            "room": payload,
        }
    )


@app.route("/rooms/<room_id>/leave", methods=["GET", "POST"])
def leave_room(room_id):
    player_id = request.values.get("player_id")

    if not player_id:
        return json_error("player_id is required")

    with closing(db()) as conn:
        conn.execute(
            """
            DELETE FROM room_players
            WHERE room_id = ? AND player_id = ?
            """,
            (room_id, player_id),
        )

        count = conn.execute(
            """
            SELECT COUNT(*)
            FROM room_players
            WHERE room_id = ?
            """,
            (room_id,),
        ).fetchone()[0]

        if count == 0:
            conn.execute(
                "DELETE FROM rooms WHERE id = ?",
                (room_id,),
            )
        else:
            conn.execute(
                "UPDATE rooms SET status = 'waiting' WHERE id = ?",
                (room_id,),
            )

        conn.commit()

    return jsonify(
        {
            "status": 0,
            "result": "success",
        }
    )


@app.route("/automatch/", methods=["GET", "POST"])
@app.route("/automatch", methods=["GET", "POST"])
def automatch():
    player_id = (
        request.values.get("player_id")
        or str(uuid.uuid4())
    )
    ensure_player(player_id)

    with closing(db()) as conn:
        row = conn.execute(
            """
            SELECT r.id
            FROM rooms r
            JOIN room_players rp
                ON rp.room_id = r.id
            WHERE r.status = 'waiting'
              AND rp.player_id != ?
            ORDER BY r.created_at ASC
            LIMIT 1
            """,
            (player_id,),
        ).fetchone()

        if row:
            room_id = row["id"]

            conn.execute(
                """
                INSERT OR IGNORE INTO room_players(
                    room_id, player_id, joined_at
                )
                VALUES (?, ?, ?)
                """,
                (room_id, player_id, now()),
            )

            conn.execute(
                "UPDATE rooms SET status = 'ready' WHERE id = ?",
                (room_id,),
            )
        else:
            room_id = str(uuid.uuid4())

            conn.execute(
                """
                INSERT INTO rooms(
                    id, host_id, status, created_at
                )
                VALUES (?, ?, 'waiting', ?)
                """,
                (room_id, player_id, now()),
            )

            conn.execute(
                """
                INSERT INTO room_players(
                    room_id, player_id, joined_at
                )
                VALUES (?, ?, ?)
                """,
                (room_id, player_id, now()),
            )

        conn.commit()
        payload = room_payload(conn, room_id)

    return jsonify(
        {
            "status": 0,
            "result": "success",
            "match": payload,
        }
    )


@app.route(
    "/world_series_find_room.php",
    methods=["GET", "POST"],
)
def world_series_find_room():
    return automatch()


# ---------------------------------------------------------
# Loading / ads
# ---------------------------------------------------------

@app.route("/hdloading.php", methods=["GET", "POST"])
@app.route("/ads", methods=["GET", "POST"])
def ads():
    return jsonify(
        {
            "status": 0,
            "result": "ok",
            "url": "",
        }
    )


# ---------------------------------------------------------
# Fallback
# ---------------------------------------------------------

@app.route("/<path:path>", methods=["GET", "POST"])
def catch_all(path):
    print(
        f"[fallback] /{path} "
        f"method={request.method} "
        f"query={dict(request.args)}"
    )

    return jsonify(
        {
            "status": 0,
            "result": "ok",
            "path": "/" + path,
        }
    )


# ---------------------------------------------------------
# Local / Render startup
# ---------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(
        host="0.0.0.0",
        port=port,
    )
