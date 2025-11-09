from flask import Flask, render_template, Response, stream_with_context, request, jsonify, send_from_directory
import requests
import os, time
import uuid
import elevenlabs
from dotenv import load_dotenv
import asyncio
from client import process_message, init_mcp

load_dotenv()
app = Flask(__name__)

PLOTS_FOLDER = os.path.join(app.static_folder, "plots")
os.makedirs(PLOTS_FOLDER, exist_ok=True)

eleven_api = os.getenv("ELEVEN_API_KEY")
voice_id = "DtsPFCrhbCbbJkwZsb3d"

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

loop.run_until_complete(init_mcp())

def text_to_speech(text):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": eleven_api,
        "Content-Type": "application/json"
    }
    data = { "text": text }

    response = requests.post(url, headers=headers, json=data)

    filename = f"static/audio_{uuid.uuid4().hex}.mp3"
    if response.status_code == 200:
        with open(filename, "wb") as f:
            f.write(response.content)
        return filename
    return None

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_msg = request.json.get("message")

    # TEMP: chatbot just repeats back
    bot_reply = loop.run_until_complete(process_message(user_msg))

    # Convert to speech
    audio_path = text_to_speech(bot_reply)

    return jsonify({
        "reply": bot_reply,
        "audio": "/" + audio_path.replace("\\", "/"),
    })

@app.route("/plot-stream")
def plot_stream():
    def generate():
        seen = set(os.listdir(PLOTS_FOLDER))
        while True:
            time.sleep(1.5)  
            current = set(os.listdir(PLOTS_FOLDER))
            new_files = current - seen
            if new_files:
                for filename in sorted(new_files):
                    yield f"data:{filename}\n\n"
                seen = current
    return Response(stream_with_context(generate()), mimetype="text/event-stream")

@app.route("/api/speech-to-text", methods=["POST"])
def speech_to_text():
    import tempfile
    import subprocess
    from elevenlabs.client import ElevenLabs

    client = ElevenLabs(api_key=os.getenv("eleven_api"))

    # Save uploaded webm temporarily
    tmp_webm = tempfile.NamedTemporaryFile(delete=False, suffix=".webm")
    tmp_webm.write(request.data)
    tmp_webm.close()

    # Convert webm → wav
    wav_path = tmp_webm.name.replace(".webm", ".wav")
    subprocess.run([
        "ffmpeg", "-y", "-i", tmp_webm.name,
        "-ar", "16000", "-ac", "1",
        wav_path
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Send WAV to ElevenLabs speech-to-text
    with open(wav_path, "rb") as audio_file:
        transcript = client.speech_to_text.convert(
            file=audio_file,
            model_id="eleven_multilingual_v2"
        )

    text = transcript.text if transcript and transcript.text else ""

    print("Saved webm:", tmp_webm.name)
    print("Converted wav:", wav_path)
    print("Transcript object:", transcript)
    print("Transcript text:", transcript.text if hasattr(transcript, "text") else "NO TEXT")

    return jsonify({"text": text})

@app.route("/chat-ui")
def chat_ui():
    return render_template("chat.html")

@app.route("/saved")
def saved():
    plot_folder = os.path.join("static", "plots")
    plot_files = []

    # loop over files in the folder
    for f in os.listdir(plot_folder):
        if f.lower().endswith(".png"):  # only include PNGs
            plot_files.append("/static/plots/" + f)

    return render_template("saved.html", plots=plot_files)

@app.route("/about")
def about():
    return render_template("about.html")


@app.route('/plots/<filename>')
def serve_plot(filename):
    return send_from_directory(PLOTS_FOLDER, filename)

@app.route("/list-plots")
def list_plots():
    files = [
        f"/static/plots/{file}"
        for file in os.listdir(PLOTS_FOLDER)
        if file.lower().endswith(".png")
    ]
    return jsonify(files)

if __name__ == "__main__":
    app.run(debug=True)