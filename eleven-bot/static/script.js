// Elements
const sendBtn     = document.getElementById("send-btn");
const chatInput   = document.getElementById("chat-input");
const messagesDiv = document.getElementById("messages");
const outputArea  = document.getElementById("output-area");
const micBtn      = document.getElementById("mic-btn");
const statusEl    = document.getElementById("status");

// Fade-in effect for messages
function makeMessageDiv(sender, text) {
    const div = document.createElement("div");
    div.className = sender === "You" ? "msg user" : "msg bot";
    div.style.opacity = 0;               // start transparent
    div.innerHTML = text;

    messagesDiv.appendChild(div);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;

    // smooth fade-in
    setTimeout(() => {
        div.style.transition = "opacity 0.3s ease";
        div.style.opacity = 1;
    }, 10);
}

// Bot typing indicator bubble
function addTypingBubble() {
    const bubble = document.createElement("div");
    bubble.className = "msg bot typing";
    bubble.innerHTML = `
        <div class="typing-dots">
            <span></span><span></span><span></span>
        </div>
    `;
    messagesDiv.appendChild(bubble);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
    return bubble; // so we can remove later
}

async function sendMessage() {
    const text = chatInput.value.trim();
    if (!text) return;

    makeMessageDiv("You", text);
    chatInput.value = "";

    // ✅ Mock plot logic
    if (text.toLowerCase().includes("plot")) {
        setTimeout(() => {
            makeMessageDiv("Melody", "Here's your plot!");
            expandLayout();           // <-- move chat left and show right panel
            showMockPlot();           // <-- show the image
        }, 800);
        return; // stop further fetch to backend
    }


    // Bot thinking animation
    const typingBubble = addTypingBubble();

    try {
        const res = await fetch("/chat", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ message: text })
        });
        const data = await res.json();

        typingBubble.remove();  // remove bubble
        makeMessageDiv("Melody", data.reply);

        if (data.audio) {
            new Audio(data.audio).play();
        }
        if (data.plot) {
            outputArea.innerHTML = `<img src="${data.plot}" />`;
        }

    } catch (err) {
        typingBubble.remove();
        makeMessageDiv("System", "❌ Error: Unable to reach backend.");
        console.error(err);
    }
}

function showMockPlot() {
    const output = document.getElementById("output-area");
    output.innerHTML = ""; // clear previous

    const plotDiv = document.createElement("div");
    plotDiv.className = "mock-plot";
    plotDiv.style.opacity = 0;
    plotDiv.style.transform = "translateX(-30px)";
    plotDiv.style.transition = "all 0.6s ease";
    plotDiv.innerHTML = `<img src="MelodyAI/gemini-mcp-backend/plots/Scatter-Plot_thumb-01.png" />`;

    output.appendChild(plotDiv);

    requestAnimationFrame(() => {
        plotDiv.style.opacity = 1;
        plotDiv.style.transform = "translateX(0)";
    });
}


function expandLayout() {
    const chatPanel = document.getElementById("chat-panel");
    const rightPanel = document.getElementById("right-panel");

    if (!chatPanel || !rightPanel) return;

    chatPanel.style.transition = "flex 0.5s ease";
    chatPanel.style.flex = "1"; // left panel smaller
    rightPanel.style.display = "block";
    requestAnimationFrame(() => {
        rightPanel.style.opacity = 1;
    });
}




// Event Listeners
if (sendBtn) sendBtn.addEventListener("click", sendMessage);
if (chatInput) {
    chatInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") sendMessage();
    });
}


// ✅ Microphone UX polish
if (micBtn) {
    micBtn.addEventListener("click", async () => {
        statusEl.innerText = "🎙 Listening...";

        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
        const chunks = [];

        recorder.ondataavailable = (e) => chunks.push(e.data);
        recorder.start();

        setTimeout(() => recorder.stop(), 4000);

        recorder.onstop = async () => {
            statusEl.innerText = "Processing audio…";
            const blob = new Blob(chunks, { type: "audio/webm" });
            const formData = new FormData();
            formData.append("audio", blob, "audio.webm");

            // same loading animation
            const bubble = addTypingBubble();

            try {
                const res = await fetch("/api/speech-to-text", {
                    method: "POST",
                    body: formData
                });
                const data = await res.json();
                statusEl.innerText = "";

                bubble.remove();
                if (data.text) {
                    makeMessageDiv("You", data.text);
                    processTextFromSpeech(data.text);
                }
            } catch (err) {
                bubble.remove();
                statusEl.innerText = "Speech error";
            }
        };
    });
}

async function processTextFromSpeech(text) {
    const bubble = addTypingBubble();

    const res = await fetch("/chat", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ message: text })
    });
    const data = await res.json();

    bubble.remove();
    makeMessageDiv("Melody", data.reply);

    if (data.audio) new Audio(data.audio).play();
    if (data.plot) {
        outputArea.innerHTML = `<img src="${data.plot}" />`;
    }
}