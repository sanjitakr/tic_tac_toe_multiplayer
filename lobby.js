// Read uid from sessionStorage (set during login)
const MY_UID = sessionStorage.getItem("uid") || new URLSearchParams(location.search).get("uid");

if (!MY_UID) {
    location.href = "/login-page";
}

document.getElementById("my-uid").textContent = MY_UID;

const WS_URL = `ws://${location.host}/ws/lobby?uid=${encodeURIComponent(MY_UID)}`;
let ws;

let pendingChallengeFrom = null;

// ---- DOM refs ----
const userGrid        = document.getElementById("user-grid");
const userCount       = document.getElementById("user-count");
const emptyState      = document.getElementById("empty-state");
const logEl           = document.getElementById("log");

const challengeModal  = document.getElementById("challenge-modal");
const challengeText   = document.getElementById("challenge-text");
const acceptBtn       = document.getElementById("accept-btn");
const declineBtn      = document.getElementById("decline-btn");

const waitingModal    = document.getElementById("waiting-modal");

// ---- Logging ----
function addLog(msg, type = "normal") {
    const ts = new Date().toLocaleTimeString("en-GB", { hour12: false });
    const entry = document.createElement("div");
    entry.className = `log-entry ${type === "event" ? "event" : type === "warn" ? "warn" : ""}`;
    entry.innerHTML = `<span class="ts">${ts}</span>${msg}`;
    logEl.prepend(entry);
    // Keep max 80 entries
    while (logEl.children.length > 80) logEl.removeChild(logEl.lastChild);
}

// ---- WebSocket ----
function connect() {
    ws = new WebSocket(WS_URL);

    ws.onopen = () => {
        addLog("Connection established.", "event");
    };

    ws.onmessage = (evt) => {
        const msg = JSON.parse(evt.data);
        handleMessage(msg);
    };

    ws.onclose = () => {
        addLog("Connection lost. Reconnecting…", "warn");
        setTimeout(connect, 3000);
    };

    ws.onerror = () => {
        addLog("WebSocket error.", "warn");
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

        case "lobby_update":
            renderUsers(msg.users);
            break;

        case "incoming_challenge":
            pendingChallengeFrom = msg.from_uid;
            challengeText.textContent =
                `${msg.from_name} (${msg.from_uid}) wants to challenge you to a match.`;
            challengeModal.classList.remove("hidden");
            addLog(` Challenge received from ${msg.from_name}.`, "warn");
            break;

        case "challenge_accepted":
            waitingModal.classList.add("hidden");
            addLog(` Challenge accepted. Entering arena…`, "event");
            sessionStorage.setItem("room_id", msg.room_id);
            sessionStorage.setItem("my_symbol", msg.symbol);
            location.href = `/game?room_id=${encodeURIComponent(msg.room_id)}&uid=${encodeURIComponent(MY_UID)}`;
            break;

        case "challenge_declined":
            waitingModal.classList.add("hidden");
            addLog(` Challenge declined by ${msg.from_uid}.`, "warn");
            break;

        case "error":
            addLog(` ${msg.message}`, "warn");
            waitingModal.classList.add("hidden");
            break;
    }
}

// ---- Render online users ----
function renderUsers(users) {
    userGrid.innerHTML = "";
    const others = users.filter(u => u.uid !== MY_UID);
    const self   = users.find(u => u.uid === MY_UID);

    userCount.textContent = users.length;

    // Self card first
    if (self) {
        userGrid.appendChild(buildCard(self, true));
    }

    if (others.length === 0) {
        emptyState.classList.add("visible");
    } else {
        emptyState.classList.remove("visible");
        others.forEach(u => userGrid.appendChild(buildCard(u, false)));
    }
}

function buildCard(user, isSelf) {
    const card = document.createElement("div");
    card.className = `user-card${isSelf ? " self" : ""}`;
    card.innerHTML = `
        <div class="card-uid">${user.uid}</div>
        <div class="card-name">${escHtml(user.name)}</div>
        <div class="card-badge">${isSelf ? "YOU" : "ONLINE"}</div>
        ${!isSelf ? `<div class="card-challenge">▶ CHALLENGE</div>` : ""}
    `;
    if (!isSelf) {
        card.addEventListener("click", () => sendChallenge(user.uid, user.name));
    }
    return card;
}

// ---- Challenge flow ----
function sendChallenge(targetUid, targetName) {
    addLog(` Challenge sent to ${targetName}…`);
    send({ type: "challenge", target_uid: targetUid });
    waitingModal.classList.remove("hidden");
}

acceptBtn.addEventListener("click", () => {
    if (!pendingChallengeFrom) return;
    challengeModal.classList.add("hidden");
    send({ type: "challenge_response", from_uid: pendingChallengeFrom, accepted: true });
    addLog(" Challenge accepted. Awaiting room…", "event");
    pendingChallengeFrom = null;
});

declineBtn.addEventListener("click", () => {
    if (!pendingChallengeFrom) return;
    challengeModal.classList.add("hidden");
    send({ type: "challenge_response", from_uid: pendingChallengeFrom, accepted: false });
    addLog(" Challenge declined.");
    pendingChallengeFrom = null;
});

// ---- Helpers ----
function escHtml(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// ---- Boot ----
connect();
addLog("NEXUS LOBBY initialised. Awaiting operative data…");