const params   = new URLSearchParams(location.search);
const ROOM_ID  = params.get("room_id") || sessionStorage.getItem("room_id");
const MY_UID   = params.get("uid")     || sessionStorage.getItem("uid");

if (!ROOM_ID || !MY_UID) {
    location.href = "/lobby";
}

document.getElementById("room-display").textContent = ROOM_ID;

const WS_URL = `ws://${location.host}/ws/game/${encodeURIComponent(ROOM_ID)}?uid=${encodeURIComponent(MY_UID)}`;

// ---- DOM refs ----
const boardEl      = document.getElementById("board");
const statusBar    = document.getElementById("status-bar");
const resultOverlay = document.getElementById("result-overlay");
const resultText   = document.getElementById("result-text");
const rematchBtn   = document.getElementById("rematch-btn");
const eloInfo      = document.getElementById("elo-info");
const dcModal      = document.getElementById("dc-modal");
const panelX       = document.getElementById("panel-x");
const panelO       = document.getElementById("panel-o");
const nameX        = document.getElementById("name-x");
const nameO        = document.getElementById("name-o");

// ---- State ----
let mySymbol   = null;
let gameOver   = false;
let symbols    = {};     // uid -> X|O
let playerUIDs = [];     // [uid_x, uid_o]
let ws;

// ---- Build board cells ----
const cells = [];
for (let i = 0; i < 9; i++) {
    const cell = document.createElement("div");
    cell.className = "cell disabled";
    cell.dataset.index = i;
    cell.addEventListener("click", () => onCellClick(i));
    boardEl.appendChild(cell);
    cells.push(cell);
}

// ---- WebSocket ----
function connect() {
    ws = new WebSocket(WS_URL);

    ws.onopen = () => {
        statusBar.textContent = "ESTABLISHING LINK…";
    };

    ws.onmessage = (evt) => {
        const msg = JSON.parse(evt.data);
        handleMessage(msg);
    };

    ws.onclose = () => {
        if (!gameOver) {
            statusBar.textContent = "CONNECTION SEVERED";
        }
    };

    ws.onerror = () => {
        statusBar.textContent = "NETWORK ERROR";
    };
}

function send(obj) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(obj));
    }
}

// ---- Message handler ----
function handleMessage(msg) {
    switch (msg.type) {

        case "game_state":
            mySymbol   = msg.symbols[MY_UID];
            symbols    = msg.symbols;
            playerUIDs = msg.players;

            updatePlayerPanels(msg);
            renderBoard(msg.board, msg.turn, msg.winner, msg.draw, msg.symbols);

            if (msg.winner) {
                showResult(msg.winner === MY_UID ? "⚡ VICTORY" : "✗ DEFEATED", msg.winner === MY_UID ? "cyan" : "red");
                highlightWinningCells(msg.board, msg.symbols[msg.winner]);
                gameOver = true;
            } else if (msg.draw) {
                showResult("— DRAW —", "yellow");
                gameOver = true;
            } else {
                gameOver = false;
                resultOverlay.classList.add("hidden");
                const isMyTurn = msg.turn === MY_UID;
                statusBar.textContent = isMyTurn ? "▶ YOUR TURN" : "WAITING FOR OPPONENT…";
            }
            break;

        case "opponent_left_lobby":
            // Opponent chose to return to lobby cleanly — show them a prompt
            gameOver = true;
            statusBar.textContent = "OPPONENT RETURNED TO LOBBY";
            resultText.textContent = "OPPONENT LEFT";
            resultText.style.color = "var(--dim)";
            if (eloInfo) eloInfo.style.display = "none";
            resultOverlay.classList.remove("hidden");
            break;

        case "opponent_disconnected":
            dcModal.classList.remove("hidden");
            gameOver = true;
            break;

        case "error":
            // flash status bar briefly
            const prev = statusBar.textContent;
            statusBar.style.color = "var(--red)";
            statusBar.textContent = `⚠ ${msg.message}`;
            setTimeout(() => {
                statusBar.style.color = "";
                statusBar.textContent = prev;
            }, 1500);
            break;
    }
}

// ---- Update player name panels ----
function updatePlayerPanels(state) {
    const [uidX, uidO] = state.players;
    nameX.textContent = uidX || "—";
    nameO.textContent = uidO || "—";
}

// ---- Render board ----
const WINS = [[0,1,2],[3,4,5],[6,7,8],[0,3,6],[1,4,7],[2,5,8],[0,4,8],[2,4,6]];

function renderBoard(board, turn, winner, draw, symMap) {
    const myTurn = !winner && !draw && turn === MY_UID;

    cells.forEach((cell, i) => {
        const val = board[i];
        cell.textContent = val || "";
        cell.className = "cell";

        if (val) {
            cell.classList.add("taken", val);   // "X" or "O"
        }

        if (!val && myTurn) {
            // playable
        } else {
            cell.classList.add("disabled");
        }
    });

    // Turn highlight on player panels
    if (!winner && !draw) {
        panelX.classList.toggle("active-turn", turn === playerUIDs[0]);
        panelO.classList.toggle("active-turn", turn === playerUIDs[1]);
    } else {
        panelX.classList.remove("active-turn");
        panelO.classList.remove("active-turn");
    }
}

function highlightWinningCells(board, winSymbol) {
    for (const combo of WINS) {
        if (combo.every(i => board[i] === winSymbol)) {
            combo.forEach(i => cells[i].classList.add("winning"));
            break;
        }
    }
}

// ---- Cell click ----
function onCellClick(index) {
    if (gameOver) return;
    if (cells[index].classList.contains("taken")) return;
    if (cells[index].classList.contains("disabled")) return;
    // Send move to server — server validates
    send({ type: "move", cell: index });
}

// ---- Show result ----
function showResult(text, color) {
    resultText.textContent = text;
    resultText.style.color = color === "cyan" ? "var(--cyan)"
                           : color === "red"  ? "var(--red)"
                           : "var(--yellow)";
    resultOverlay.classList.remove("hidden");
    statusBar.textContent = "MATCH COMPLETE";
}

// ---- Rematch ----
rematchBtn.addEventListener("click", () => {
    gameOver = false;
    resultOverlay.classList.add("hidden");
    cells.forEach(c => { c.className = "cell disabled"; c.textContent = ""; });
    statusBar.textContent = "REMATCH REQUESTED…";
    send({ type: "rematch" });
});

// ---- Return to lobby ----
// Intercept ALL lobby links — send a clean "leave" message first so the
// server keeps us online and broadcasts immediately, THEN navigate.
document.querySelectorAll('a[href="/lobby"]').forEach(link => {
    link.addEventListener("click", (e) => {
        e.preventDefault();
        send({ type: "leave" });
        setTimeout(() => { window.location.href = "/lobby"; }, 80);
    });
});

// ---- Boot ----
connect();