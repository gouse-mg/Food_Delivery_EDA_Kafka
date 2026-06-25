// ── CONFIG — change this before deploying ─────────────────────────────────────

// ─────────────────────────────────────────────────────────────────────────────

const token = localStorage.getItem("token");
if (!token) window.location.href = "/";

// ── JWT helper ────────────────────────────────────────────────────────────────
function parseJwt(token) {
    try {
        const base64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
        return JSON.parse(atob(base64));
    } catch {
        return null;
    }
}

// ── WEBSOCKET / ORDERS ────────────────────────────────────────────────────────
let socket;
function connect() {
    const payload = parseJwt(token);
    if (!payload || !payload.sub) {
        alert("Invalid session. Please log in again.");
        localStorage.removeItem("token");
        window.location.href = "/";
        return;
    }

    const partner_id = payload.sub;
    socket = new WebSocket(`/api/PartManager/communicate/ws?partner_id=${partner_id}&token=${token}`);

    socket.onopen = () => console.log(`Connected as restaurant ${partner_id}`);

    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.flag === "Connected") {
            document.getElementById("partnerName").textContent = `🍽️ ${data.name}`;
        } 
    };

    socket.onerror = (err) => console.error("WebSocket error:", err);

    socket.onclose = (event) => {
        console.log(`Disconnected (code: ${event.code})`);
        if (event.code === 1008) {
            alert("Session expired or unauthorized. Please log in again.");
            localStorage.removeItem("token");
            window.location.href = "/";
        }
    };
}

connect();
