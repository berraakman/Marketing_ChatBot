// Use relative URLs - works on both localhost and production
const API_BASE = "";

/* ========= STATE ========= */
let history = [
    {
        role: "assistant",
        content:
            "Welcome 👋\n\nI'm FundEd's AI booth assistant.\n\nAre you here as an investor, startup founder, or potential partner?"
    }
];

const chatEl = document.getElementById("chat");
const inputEl = document.getElementById("input");
const sendBtn = document.getElementById("sendBtn");
const refreshBtn = document.getElementById("refreshCards");
const cardsEl = document.getElementById("info-cards");
const mainScrollEl = document.querySelector(".main-scroll");

/* ========= INIT ========= */
renderAll();
loadCards();

/* ========= EVENTS ========= */
sendBtn.addEventListener("click", send);
inputEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        send();
    }
});

refreshBtn.addEventListener("click", async () => {
    await fetch(`${API_BASE}/reload`, { method: "POST" });
    await loadCards(true);
});

/* ========= CHAT ========= */
async function send() {
    const q = inputEl.value.trim();
    if (!q) return;

    inputEl.value = "";

    history.push({ role: "user", content: q });
    renderMessage("user", q);
    scrollBottom();

    const typing = renderTyping();

    try {
        const cleanHistory = history.filter(
            (m) => m.role === "user" || m.role === "assistant"
        );

        const res = await fetch(`${API_BASE}/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                question: q,
                history: cleanHistory.slice(0, -1)
            })
        });

        if (!res.ok) {
            throw new Error("Backend error");
        }

        const data = await res.json();
        typing.remove();

        const reply =
            data.response ??
            data.answer ??
            data.message ??
            "Sorry, I couldn’t generate a response.";

        history.push({ role: "assistant", content: reply });
        renderMessage("assistant", reply);
        scrollBottom();
    } catch (e) {
        typing.remove();
        renderMessage(
            "assistant",
            "Sorry — something went wrong while contacting the booth system."
        );
    }
}

/* ========= RENDER ========= */
function renderAll() {
    chatEl.innerHTML = "";
    history.forEach((m) => renderMessage(m.role, m.content));
}

function renderMessage(role, text) {
    const row = document.createElement("div");
    row.className = `chat-row ${role === "user" ? "chat-right" : "chat-left"}`;

    const bubble = document.createElement("div");
    bubble.className = `chat-bubble ${role}`;

    const header = document.createElement("div");
    header.style.display = "flex";
    header.style.alignItems = "center";
    header.style.gap = "8px";
    header.style.marginBottom = "4px";

    const avatar = document.createElement("img");
    avatar.width = 22;
    avatar.height = 22;
    avatar.style.borderRadius = "50%";
    avatar.src =
        role === "user"
            ? "/assets/user.png"
            : "/assets/ai.png";

    const name = document.createElement("span");
    name.className = `chat-name ${role === "user" ? "user-name" : ""}`;
    name.textContent = role === "user" ? "You" : "FundEd‑AI";

    header.appendChild(avatar);
    header.appendChild(name);

    bubble.appendChild(header);
    bubble.insertAdjacentHTML(
        "beforeend",
        escapeHtml(text).replace(/\n/g, "<br>")
    );

    row.appendChild(bubble);
    chatEl.appendChild(row);
}

function renderTyping() {
    const row = document.createElement("div");
    row.className = "chat-row chat-left";

    const bubble = document.createElement("div");
    bubble.className = "chat-bubble assistant";
    bubble.innerHTML = `
    <div class="typing">
      FundEd‑AI is typing
      <span class="typing-dots">
        <span></span><span></span><span></span>
      </span>
    </div>
  `;

    row.appendChild(bubble);
    chatEl.appendChild(row);
    scrollBottom();
    return row;
}

function scrollBottom() {
    if (mainScrollEl) {
        mainScrollEl.scrollTop = mainScrollEl.scrollHeight;
    }
}

/* ========= CARDS ========= */
async function loadCards(force = false) {
    cardsEl.innerHTML = "";

    try {
        const res = await fetch(`${API_BASE}/cards`);
        const data = await res.json();
        const cards = Array.isArray(data) ? data : data.cards || [];

        cards.forEach((c, i) => {
            const card = document.createElement("div");
            card.className = "info-card";
            card.style.animationDelay = `${i * 0.15}s`;

            card.innerHTML = `
        <div class="card-title">${c.title}</div>
        <div class="card-content">${c.content}</div>
      `;
            cardsEl.appendChild(card);
        });
    } catch (e) {
        cardsEl.innerHTML =
            "<div class='card-content'>Quick tips are currently unavailable.</div>";
    }
}

function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}