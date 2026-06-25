// ── CONFIG — change this before deploying ─────────────────────────────────────
const BASE_URL = "http://localhost:8000";   // e.g. "https://api.yourapp.com"
const WS_URL   = BASE_URL.replace(/^http/, "ws"); // derives ws:// or wss:// automatically
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
restaurantName
// ── DISHES ────────────────────────────────────────────────────────────────────
async function loadDishes() {
    try {
        const res = await fetch(`/api/ResManager/dishes`, {
            headers: { "Authorization": `Bearer ${token}` }
        });
        if (!res.ok) throw new Error("Failed to load dishes");
        const dishes = await res.json();
        renderDishes(dishes);
    } catch (e) {
        document.getElementById("dishes-empty").textContent = "Could not load dishes.";
    }
}

function renderDishes(dishes) {
    const list = document.getElementById("dish-list");
    const empty = document.getElementById("dishes-empty");
    list.innerHTML = "";

    if (!dishes.length) {
        empty.textContent = "No dishes yet. Add one below.";
        return;
    }

    empty.textContent = "";
    dishes.forEach(d => {
        const card = document.createElement("div");
        card.className = "dish-card";
        card.innerHTML = `
            <div class="dish-name">${d.name}</div>
            <div class="dish-price">₹${d.price}</div>
            <div class="dish-desc">${d.description || ""}</div>
        `;
        list.appendChild(card);
    });
}

async function addDish(e) {
    e.preventDefault();
    const msg = document.getElementById("dish-msg");
    const name = document.getElementById("dish-name").value.trim();
    const price = document.getElementById("dish-price").value.trim();
    const description = document.getElementById("dish-description").value.trim();

    if (!name || !price) {
        msg.textContent = "Name and price are required.";
        msg.className = "err";
        return;
    }

    try {
        const res = await fetch(`/api/ResManager/dishes/create-dish`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({ "name":name, "price": parseFloat(price), "description":description })
        });

        if (!res.ok) throw new Error("Failed to add dish");

        msg.textContent = "Dish added!";
        msg.className = "ok";
        document.getElementById("dish-name").value = "";
        document.getElementById("dish-price").value = "";
        document.getElementById("dish-description").value = "";
        loadDishes();
    } catch {
        msg.textContent = "Error adding dish.";
        msg.className = "err";
    }
}

document.getElementById("add-dish-form").addEventListener("submit", addDish);
loadDishes();

// ── WEBSOCKET / ORDERS ────────────────────────────────────────────────────────
let socket;
let confirmedOrders = {};

function connect() {
    const payload = parseJwt(token);
    if (!payload || !payload.sub) {
        alert("Invalid session. Please log in again.");
        localStorage.removeItem("token");
        window.location.href = "/";
        return;
    }

    const restaurant_id = payload.sub;
    socket = new WebSocket(`/api/ResManager/communicate/ws?restaurant_id=${restaurant_id}&token=${token}`);

    socket.onopen = () => console.log(`Connected as restaurant ${restaurant_id}`);

    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.flag === "Connected") {
            document.getElementById("restaurantName").textContent = `🍽️ ${data.name}`;
        } else if (data.flag === "Order") {
            handleNewOrder(data);
        } else if (data.flag === "Confirm") {
            console.log("Confirm",data.oid)
            handleConfirmedOrder(data);
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

function handleNewOrder(data) {
    const li = document.createElement("li");
    li.id = `order-${data.oid}`;
    li.textContent = `Order #${data.oid}: ${data.menu}`;

    const confirmBtn = document.createElement("button");
    confirmBtn.textContent = "Confirm";
    confirmBtn.onclick = () => confirmOrder(data.oid, data.menu, li);

    const rejectBtn = document.createElement("button");
    rejectBtn.textContent = "Reject";
    rejectBtn.onclick = () => rejectOrder(data.oid, li);

    li.appendChild(confirmBtn);
    li.appendChild(rejectBtn);
    document.getElementById("messages").appendChild(li);
}

function confirmOrder(oid, menu, li) {
    confirmedOrders[oid] = menu;
    updateConfirmedDisplay();
    li.remove();
    updateOrderStatus(oid, "accepted");
}

function rejectOrder(oid, li) {
    li.remove();
    updateOrderStatus(oid, "rejected");
}
function sendMessage(data) {
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify(data));
    } else {
        console.warn("Socket not open, cannot send");
    }
}

async function updateOrderStatus(oid, status) {
    sendMessage({ flag: status, oid: oid });
}
//mesage with flag:Confirmed or Rejected with oid

function handleConfirmedOrder(data) {
    const oid = Number(data.oid);
    if (confirmedOrders[data.oid]) {
        delete confirmedOrders[data.oid];
        updateConfirmedDisplay();
    }
    const li = document.getElementById(`order-${oid}`);
    const element = document.createElement("button")
    element.textContent = `Prepare-${oid} ${data.menu}`;
    document.getElementById("messages").appendChild(element);

    if (li) li.remove();
}

function updateConfirmedDisplay() {
    document.getElementById("confirmedOrders").textContent = JSON.stringify(confirmedOrders, null, 2);
}

connect();
