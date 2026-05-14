from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware

from db.mysql_db import MySQLDB
from db.mongo_db import MongoDB
from utils.facial_recognition_module import build_encodings_cache, find_closest_match
from lobby_server import (
    lobby_connections, game_rooms, player_room,
    _broadcast_lobby, _send, _empty_board, _check_winner,
)

import json

app = FastAPI()

app.add_middleware(
    SessionMiddleware,
    secret_key="phase2_biometric_secret"
)

mysql_db = MySQLDB()
mongo_db = MongoDB()
encodings_cache = {}

# In server.py
@app.on_event("startup")
async def startup():
    global encodings_cache
    print("[STARTUP] Fetching images from MongoDB...")
    db_images_dict = mongo_db.get_all_images()
    
    if not db_images_dict:
        print("[STARTUP] ERROR: No images retrieved. Check your MongoDB collection.")
        return

    # pass retrieved images to the recognition module [cite: 59, 60]
    print(f"[STARTUP] Heavy Lifting: Encoding {len(db_images_dict)} images. PLEASE WAIT...")
    
    # This line will block the terminal for a while. 
    # face-recognition typically takes 0.5 - 2.0 seconds PER image.
    encodings_cache = build_encodings_cache(db_images_dict) 
    
    print(f"[STARTUP] Done! {len(encodings_cache)} records in cache. Server ready.")

class LoginRequest(BaseModel):
    image: str


# ── HTTP routes ───────────────────────────────────────────────────────────────

@app.get("/login-page", response_class=HTMLResponse)
def login_page():
    return FileResponse("login.html")

@app.get("/login.js")
def get_js():
    return FileResponse("login.js")

@app.get("/login.css")
def serve_login_css():
    return FileResponse("login.css")

@app.get("/lobby", response_class=HTMLResponse)
def serve_lobby():
    return FileResponse("lobby.html")

@app.get("/lobby.js")
def serve_lobby_js():
    return FileResponse("lobby.js")

@app.get("/game", response_class=HTMLResponse)
def game_page():
    return FileResponse("game.html")

@app.get("/game.js")
def game_js():
    return FileResponse("game.js")

@app.get("/game.css")
def serve_css():
    return FileResponse("game.css")

@app.get("/leaderboard", response_class=HTMLResponse)
def leaderboard_page():
    return FileResponse("leaderboard.html")

@app.get("/leaderboard.js")
def serve_leaderboard_js():
    return FileResponse("leaderboard.js")

@app.get("/api/leaderboard")
def api_leaderboard():
    return mysql_db.get_leaderboard()


@app.post("/login")
def login(data: LoginRequest, request: Request):
    login_image_data = data.image

    matched_uid = find_closest_match(login_image_data, encodings_cache)

    if matched_uid is None:
        raise HTTPException(status_code=401, detail="Face not recognized")

    user = mysql_db.get_user_by_uid(matched_uid)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    request.session["uid"] = matched_uid
    mysql_db.set_online_status(matched_uid, True)
    return {"message": "Login successful", "uid": matched_uid}


# ── Elo resolution helper ─────────────────────────────────────────────────────

async def _resolve_game(room: dict, winner_uid: str | None, is_draw: bool = False, forfeit: bool = False):
    if room.get("elo_settled"):
        return
    room["elo_settled"] = True

    players = room["players"]
    loser_uid = next((p for p in players if p != winner_uid), None) if winner_uid else None

    elo_result = {}
    if is_draw and len(players) == 2:
        elo_result = mysql_db.update_elo_and_record(players[0], players[1], is_draw=True)
    elif winner_uid and loser_uid:
        elo_result = mysql_db.update_elo_and_record(winner_uid, loser_uid, is_draw=False)

    payload = {
        "type": "game_over",
        "winner": winner_uid,
        "draw": is_draw,
        "forfeit": forfeit,
        "elo": elo_result,
        "board": room["board"],
        "symbols": room["symbols"],
        "players": room["players"],
    }
    for p_uid, p_ws in room["sockets"].items():
        await _send(p_ws, {**payload, "your_uid": p_uid})


# ── Lobby WebSocket (/ws/lobby?uid=...) ──────────────────────────────────────

@app.websocket("/ws/lobby")
async def ws_lobby(websocket: WebSocket, uid: str):
    old_ws = lobby_connections.get(uid)
    if old_ws and old_ws is not websocket:
        try:
            await old_ws.close()
        except Exception:
            pass

    await websocket.accept()
    lobby_connections[uid] = websocket
    mysql_db.set_online_status(uid, True)
    await _broadcast_lobby(mysql_db)

    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)

            if msg["type"] == "challenge":
                target_uid = msg["target_uid"]
                challenger = mysql_db.get_user_by_uid(uid)
                challenger_name = challenger["name"] if challenger else uid

                if target_uid in lobby_connections:
                    await _send(lobby_connections[target_uid], {
                        "type": "incoming_challenge",
                        "from_uid": uid,
                        "from_name": challenger_name,
                    })
                else:
                    await _send(websocket, {"type": "error", "message": "Target user is not in the lobby."})

            elif msg["type"] == "challenge_response":
                challenger_uid = msg["from_uid"]
                accepted = msg["accepted"]

                if not accepted:
                    if challenger_uid in lobby_connections:
                        await _send(lobby_connections[challenger_uid], {
                            "type": "challenge_declined",
                            "from_uid": uid,
                        })
                    continue

                room_id = f"{challenger_uid}_vs_{uid}"
                game_rooms[room_id] = {
                    "players": [challenger_uid, uid],
                    "board": _empty_board(),
                    "turn": challenger_uid,
                    "symbols": {challenger_uid: "X", uid: "O"},
                    "sockets": {},
                    "winner": None,
                    "draw": False,
                    "elo_settled": False,
                }
                player_room[challenger_uid] = room_id
                player_room[uid] = room_id

                for target, ws_target in [
                    (challenger_uid, lobby_connections.get(challenger_uid)),
                    (uid, websocket),
                ]:
                    if ws_target:
                        await _send(ws_target, {
                            "type": "challenge_accepted",
                            "room_id": room_id,
                            "symbol": game_rooms[room_id]["symbols"][target],
                        })

    except (WebSocketDisconnect, Exception):
        pass
    finally:
        if lobby_connections.get(uid) is websocket:
            lobby_connections.pop(uid, None)
            mysql_db.set_online_status(uid, False)
            await _broadcast_lobby(mysql_db)


# ── Game WebSocket (/ws/game/{room_id}?uid=...) ───────────────────────────────

@app.websocket("/ws/game/{room_id}")
async def ws_game(websocket: WebSocket, room_id: str, uid: str):
    await websocket.accept()

    room = game_rooms.get(room_id)
    if not room or uid not in room["players"]:
        await websocket.close(code=4003)
        return

    room["sockets"][uid] = websocket
    leave_to_lobby = False  # set True on clean "leave" message

    async def broadcast_state():
        state = {
            "type": "game_state",
            "board": room["board"],
            "turn": room["turn"],
            "winner": room["winner"],
            "draw": room["draw"],
            "symbols": room["symbols"],
            "players": room["players"],
        }
        for p_uid, p_ws in room["sockets"].items():
            await _send(p_ws, {**state, "your_uid": p_uid})

    await _send(websocket, {
        "type": "game_state",
        "board": room["board"],
        "turn": room["turn"],
        "winner": room["winner"],
        "draw": room["draw"],
        "symbols": room["symbols"],
        "players": room["players"],
        "your_uid": uid,
    })

    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)

            if msg["type"] == "move":
                if room["winner"] or room["draw"]:
                    await _send(websocket, {"type": "error", "message": "Game is already over."})
                    continue
                if room["turn"] != uid:
                    await _send(websocket, {"type": "error", "message": "Not your turn."})
                    continue

                cell = msg.get("cell")
                if not isinstance(cell, int) or not (0 <= cell <= 8):
                    await _send(websocket, {"type": "error", "message": "Invalid cell."})
                    continue
                if room["board"][cell] is not None:
                    await _send(websocket, {"type": "error", "message": "Cell already taken."})
                    continue

                symbol = room["symbols"][uid]
                room["board"][cell] = symbol

                winner_symbol = _check_winner(room["board"])
                if winner_symbol:
                    room["winner"] = next(p for p, s in room["symbols"].items() if s == winner_symbol)
                    await broadcast_state()
                    await _resolve_game(room, winner_uid=room["winner"], is_draw=False)
                elif all(c is not None for c in room["board"]):
                    room["draw"] = True
                    await broadcast_state()
                    await _resolve_game(room, winner_uid=None, is_draw=True)
                else:
                    room["turn"] = next(p for p in room["players"] if p != uid)
                    await broadcast_state()

            elif msg["type"] == "rematch":
                room["board"] = _empty_board()
                room["winner"] = None
                room["draw"] = False
                room["elo_settled"] = False
                room["players"].reverse()
                room["turn"] = room["players"][0]
                room["symbols"] = {room["players"][0]: "X", room["players"][1]: "O"}
                await broadcast_state()

            elif msg["type"] == "leave":
                # Player is returning to lobby cleanly — not a forfeit, stay online
                leave_to_lobby = True
                break

    except (WebSocketDisconnect, Exception):
        pass
    finally:
        room["sockets"].pop(uid, None)
        player_room.pop(uid, None)

        if leave_to_lobby:
            # Clean lobby return — keep online, tell opponent they can go back too
            mysql_db.set_online_status(uid, True)
            for other_ws in room["sockets"].values():
                await _send(other_ws, {"type": "opponent_left_lobby"})
        else:
            # Unclean disconnect — mark offline, check forfeit
            mysql_db.set_online_status(uid, False)
            if not room.get("elo_settled") and not room["winner"] and not room["draw"]:
                surviving = [p for p in room["players"] if p in room["sockets"]]
                if surviving:
                    room["winner"] = surviving[0]
                    await _resolve_game(room, winner_uid=surviving[0], forfeit=True)
            for other_ws in room["sockets"].values():
                await _send(other_ws, {"type": "opponent_disconnected"})

        await _broadcast_lobby(mysql_db)

"""
@app.get("/debug-login/{uid}")
def debug_login(uid: str, request: Request):
    user = mysql_db.get_user_by_uid(uid)
    if not user:
        mysql_db.insert_user(uid, f"Debug {uid}")
    request.session["uid"] = uid
    mysql_db.set_online_status(uid, True)
    return HTMLResponse(f"/""
        <script>
            sessionStorage.setItem('uid', '{uid}');
            window.location.href = '/lobby';
        </script>
    "/"")

"""

