"""
lobby_server.py – Shared in-memory state and pure helper functions.

WebSocket route handlers live in server.py directly on the FastAPI `app`
instance so that Starlette's SessionMiddleware does not intercept the
HTTP → WS upgrade before FastAPI can process it.
"""

import json
from typing import Optional
from fastapi import WebSocket


# ---------------------------------------------------------------------------
# In-memory state  (imported by server.py)
# ---------------------------------------------------------------------------

# uid -> WebSocket (lobby connections)
lobby_connections: dict[str, WebSocket] = {}

# room_id -> room dict
game_rooms: dict[str, dict] = {}

# uid -> room_id
player_room: dict[str, str] = {}


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------

def _empty_board() -> list[Optional[str]]:
    return [None] * 9


def _check_winner(board: list) -> Optional[str]:
    wins = [
        (0, 1, 2), (3, 4, 5), (6, 7, 8),
        (0, 3, 6), (1, 4, 7), (2, 5, 8),
        (0, 4, 8), (2, 4, 6),
    ]
    for a, b, c in wins:
        if board[a] and board[a] == board[b] == board[c]:
            return board[a]
    return None


async def _broadcast_lobby(mysql_db) -> None:
    """Push the current online-user list to every connected lobby socket."""
    online_users = mysql_db.get_online_users()
    payload = json.dumps({"type": "lobby_update", "users": online_users})
    dead = []
    for uid, ws in lobby_connections.items():
        try:
            await ws.send_text(payload)
        except Exception:
            dead.append(uid)
    for uid in dead:
        lobby_connections.pop(uid, None)


async def _send(ws: WebSocket, data: dict) -> None:
    try:
        await ws.send_text(json.dumps(data))
    except Exception:
        pass