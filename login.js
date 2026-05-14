/* login.js */
const video     = document.getElementById("video");
const canvas    = document.getElementById("canvas");
const loginBtn  = document.getElementById("login-btn");
const statusEl  = document.getElementById("status");
const sdot      = document.getElementById("sdot");
const procOvl   = document.getElementById("proc-overlay");

function setStatus(msg, state = "ready") {
    statusEl.textContent = msg;
    sdot.className = `sdot ${state}`;
}

async function startCamera() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        video.srcObject = stream;
        video.onloadedmetadata = () => {
            video.play();
            setStatus("Camera ready — position face and authenticate.", "ready");
            loginBtn.disabled = false;
        };
    } catch (err) {
        setStatus("Camera access denied. Check browser permissions.", "error");
    }
}

async function captureAndLogin() {
    loginBtn.disabled = true;
    procOvl.classList.add("active");
    setStatus("Scanning biometric data…", "busy");

    const ctx = canvas.getContext("2d");
    ctx.save();
    ctx.scale(-1, 1);
    ctx.drawImage(video, -canvas.width, 0, canvas.width, canvas.height);
    ctx.restore();

    const imageData = canvas.toDataURL("image/jpeg").split(",")[1];

    try {
        const res = await fetch("/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ image: imageData }),
        });
        const result = await res.json();

        if (res.ok) {
            sessionStorage.setItem("uid", result.uid);
            setStatus(`Identity confirmed: ${result.uid}. Redirecting…`, "ok");
            setTimeout(() => { window.location.href = "/lobby"; }, 700);
        } else {
            setStatus(result.detail || "Authentication failed. Try again.", "error");
            loginBtn.disabled = false;
            procOvl.classList.remove("active");
        }
    } catch {
        setStatus("Server unreachable. Is the backend running?", "error");
        loginBtn.disabled = false;
        procOvl.classList.remove("active");
    }
}

loginBtn.addEventListener("click", captureAndLogin);
startCamera();