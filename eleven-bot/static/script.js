// Elements
const sendBtn     = document.getElementById("send-btn");
const chatInput   = document.getElementById("chat-input");
const messagesDiv = document.getElementById("messages");

// Create text or image message bubble; returns created element
function makeMessageDiv(sender, content, isImage = false) {
    const div = document.createElement("div");
    div.className = sender === "You" ? "msg user" : "msg bot";
    div.style.opacity = 0;

    if (isImage) {
        // create image element explicitly so we can handle onload/onerror
        const img = document.createElement("img");
        img.alt = "Plot";
        img.style.maxWidth = "100%";
        img.style.borderRadius = "10px";
        img.style.display = "block";

        // If content already looks like a data URL or absolute/relative path, use it
        img.src = content;

        // show a tiny loader placeholder while image loads
        const loader = document.createElement("div");
        loader.textContent = "Loading image…";
        loader.style.opacity = "0.6";
        loader.style.fontSize = "0.9rem";
        loader.style.color = "#bbb";

        div.appendChild(loader);
        messagesDiv.appendChild(div);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;

        // When image loads, replace loader with actual image
        img.onload = () => {
            div.removeChild(loader);
            div.appendChild(img);
            // fade in image (and bubble)
            requestAnimationFrame(() => {
                div.style.transition = "opacity 0.25s ease";
                div.style.opacity = 1;
                img.style.transition = "opacity 0.3s ease";
                img.style.opacity = 1;
            });
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        };

        img.onerror = () => {
            // replace loader with error message
            loader.textContent = "⚠️ Image failed to load.";
            console.error("Image failed to load:", content);
            div.style.transition = "opacity 0.25s ease";
            div.style.opacity = 1;
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        };

        return div; // already appended; onload will complete fade
    } else {
        // plain text
        div.textContent = content;
        messagesDiv.appendChild(div);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
        requestAnimationFrame(() => {
            div.style.transition = "opacity 0.25s ease";
            div.style.opacity = 1;
        });
        return div;
    }
}

// Typing bubble (returns bubble so caller can remove it)
function addTypingBubble() {
    const bubble = document.createElement("div");
    bubble.className = "msg bot typing";
    bubble.innerHTML = `
        <div class="typing-dots" aria-hidden="true">
            <span></span><span></span><span></span>
        </div>
    `;
    // tiny fade-in to avoid layout jump
    bubble.style.opacity = 0;
    messagesDiv.appendChild(bubble);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
    requestAnimationFrame(() => {
        bubble.style.transition = "opacity 0.18s ease";
        bubble.style.opacity = 1;
    });
    return bubble;
}

// Remove typing bubble safely
function removeTypingBubble(bubble) {
    if (!bubble) return;
    // fade-out then remove
    bubble.style.transition = "opacity 0.15s ease";
    bubble.style.opacity = 0;
    setTimeout(() => {
        if (bubble.parentNode) bubble.parentNode.removeChild(bubble);
    }, 160);
}

// Main send function
async function sendMessage() {
    const text = chatInput.value.trim();
    if (!text) return;

    makeMessageDiv("You", text);
    chatInput.value = "";


    const typingBubble = addTypingBubble();

    try {
        const res = await fetch("/chat", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ message: text })
        });

        // if backend returns JSON with reply and/or plot
        const data = await res.json();
        removeTypingBubble(typingBubble);

        if (data.reply) {
            makeMessageDiv("Melody", data.reply);
        }
        if (data.audio) {
            try {
                let audioSrc = data.audio;
                if (!audioSrc.startsWith("http") && !audioSrc.startsWith("/")) {
                    audioSrc = "/static" + audioSrc.replace(/^\/+/, "");
                }

                const audio = new Audio(audioSrc);
                audio.play().catch(err => console.warn("Audio playback failed:", err))
            }
            catch (err) {
                console.error("Audio playback error:", err)
            }
        }
        if (data.plot) {
            // data.plot may be either:
            // - a URL path ("/static/plots/foo.png"), or
            // - a base64 string (data URI or raw base64). We'll detect and adapt.
            let imgSrc = data.plot;

            // if backend returned raw base64 (no data: prefix), assume PNG
            if (/^[A-Za-z0-9+/=]+\s*$/.test(imgSrc) && imgSrc.length > 100) {
                imgSrc = "data:image/png;base64," + imgSrc;
            }

            // if backend returned just a relative path like "plots/foo.png", make it absolute under /static
            if (!imgSrc.startsWith("http") && !imgSrc.startsWith("data:") && !imgSrc.startsWith("/")) {
                imgSrc = "/static/" + imgSrc.replace(/^\/+/, "");
            }

            makeMessageDiv("Melody", imgSrc, true);
        }

    } catch (err) {
        removeTypingBubble(typingBubble);
        makeMessageDiv("System", "❌ Error: Unable to reach backend.");
        console.error(err);
    }
}

// wiring
if (sendBtn) sendBtn.addEventListener("click", sendMessage);
if (chatInput) chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") sendMessage();
});


// Keep track of already displayed plots
const displayedPlots = new Set();

async function showNewPlots() {
    const response = await fetch("/list-plots");
    const images = await response.json();

    // only show images we haven't displayed yet
    images.forEach(imgURL => {
        if (!displayedPlots.has(imgURL)) {
            makeMessageDiv("Melody", "New plot generated:");
            makeMessageDiv("Melody", imgURL, true);
            displayedPlots.add(imgURL);
        }
    });
}

const evtSource = new EventSource("/plot-stream");

evtSource.onmessage = (event) => {
    const filename = event.data.trim();
    if (!filename) return;

    const imgPath = `/static/plots/${filename}`;
    if (!displayedPlots.has(imgPath)) {
        makeMessageDiv("Melody", "🎨 New plot generated:");
        makeMessageDiv("Melody", imgPath, true);
        displayedPlots.add(imgPath);
    }
};

evtSource.onerror = (err) => {
    console.warn("Plot stream disconnected, retrying...", err);
};