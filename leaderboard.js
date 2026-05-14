/* leaderboard.js */

const MY_UID = sessionStorage.getItem("uid");

async function loadLeaderboard() {
    try {
        const res  = await fetch("/api/leaderboard");
        const data = await res.json();

        const tbody = document.getElementById("lb-body");
        const badge = document.getElementById("player-count");
        const ts    = document.getElementById("last-updated");

        badge.textContent = data.length;
        ts.textContent    = new Date().toLocaleTimeString("en-GB", { hour12: false });

        if (data.length === 0) {
            tbody.innerHTML = `<tr><td colspan="8" class="lb-empty">No operatives on record.</td></tr>`;
            return;
        }

        const rankClass = (i) => i === 0 ? "gold" : i === 1 ? "silver" : i === 2 ? "bronze" : "";
        const rankLabel = (i) => i === 0 ? "⬡ 1" : i === 1 ? "⬡ 2" : i === 2 ? "⬡ 3" : `${i + 1}`;

        tbody.innerHTML = data.map((row, i) => {
            const isMe = row.uid === MY_UID;
            const total = row.total_games || (row.wins + row.losses + row.draws);
            return `
            <tr class="${isMe ? "me" : ""}">
                <td class="rank-cell ${rankClass(i)}">${rankLabel(i)}</td>
                <td class="name-cell">${esc(row.name)}${isMe ? ' <span style="color:var(--magenta);font-size:0.6rem">[YOU]</span>' : ""}</td>
                <td class="uid-cell">${esc(row.uid)}</td>
                <td class="elo-cell">${row.elo_rating}</td>
                <td class="win-cell">${row.wins}</td>
                <td class="loss-cell">${row.losses}</td>
                <td class="draw-cell">${row.draws}</td>
                <td class="num-cell">${total}</td>
            </tr>`;
        }).join("");

    } catch (err) {
        document.getElementById("lb-body").innerHTML =
            `<tr><td colspan="8" class="lb-empty">Failed to load data. Is the server running?</td></tr>`;
    }
}

function esc(s) {
    return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}

// Load on page open, then auto-refresh every 30s
loadLeaderboard();
setInterval(loadLeaderboard, 30000);