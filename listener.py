import vosk
import pyaudio
import json
import subprocess
import wave
import piper
import threading
import time

# ─── CONFIG ───────────────────────────────────────────────────────────────────

VOSK_MODEL_PATH = "./models/vosk/vosk-model-small-en-us-0.15"
PIPER_ONNX_PATH = "./models/piper-voice.onnx"
PIPER_JSON_PATH = "./models/piper-voice.onnx.json"
TTS_WAV_PATH    = "/tmp/xian-tts.wav"
WAKE_WORD       = "xian"
LISTEN_TIMEOUT  = 6

VOCAB = '["terminal","tutup","xian","again","naik","down","mute","status","firefox","browser","close","sound","storage","sleep","[unk]"]'

# ─── RESPONSES ────────────────────────────────────────────────────────────────

RESPONSE = {
    "wake":             "aktif",
    "timeout":          "tidak aktif",
    "cancel":           "mode cancel",
    "unknown":          "input gagal",
    "again":            "mengulagi",

    "open_xian":        "xian aktif",
    "open_firefox":     "firefox aktif",
    "open_status":      "status sistem aktif",
    "open_storage":     "storage aktif",
    "open_terminal":    "terminal aktif",

    "close_xian":       "xian tidak aktif",
    "close_firefox":    "firefox tidak aktif",
    "close_status":     "status sistem tidak aktif",
    "close_storage":    "storage tidak aktif",

    "sound_mode":       "sound mode aktif",
    "close_mode":       "close mode aktif",

    "vol_up":           "menaikan volume",
    "vol_down":         "menurunkan volume",
    "mute":             "mute",
    "sleep":            "sleep",
}

# ─── INIT MODELS ──────────────────────────────────────────────────────────────

print("[XIAN] Loading model...")
model = vosk.Model(VOSK_MODEL_PATH)
rec   = vosk.KaldiRecognizer(model, 16000, VOCAB)
voice = piper.PiperVoice.load(PIPER_ONNX_PATH, config_path=PIPER_JSON_PATH)

p = pyaudio.PyAudio()
stream = p.open(
    format=pyaudio.paInt16,
    channels=1,
    rate=16000,
    input=True,
    frames_per_buffer=8000
)

# ─── STATE ────────────────────────────────────────────────────────────────────

state       = "idle"
last_action = None
timeout_timer: threading.Timer | None = None

# ─── HELPERS ──────────────────────────────────────────────────────────────────

def speak(text: str):
    with wave.open(TTS_WAV_PATH, "wb") as f:
        voice.synthesize_wav(text, f)
    subprocess.Popen(["pw-play", TTS_WAV_PATH])

def run(*cmd):
    subprocess.Popen(list(cmd))

def hypr(app_cmd: str):
    run("hyprctl", "dispatch", "exec", app_cmd)

# ─── TIMEOUT ──────────────────────────────────────────────────────────────────

def reset_timeout():
    global timeout_timer
    if timeout_timer:
        timeout_timer.cancel()
    timeout_timer = threading.Timer(LISTEN_TIMEOUT, go_idle)
    timeout_timer.daemon = True
    timeout_timer.start()

def go_idle():
    global state
    if state != "idle":
        print("[XIAN] Timeout — balik standby.")
        speak(RESPONSE["timeout"])
        state = "idle"

def cancel_timeout():
    global timeout_timer
    if timeout_timer:
        timeout_timer.cancel()
        timeout_timer = None

# ─── ACTIONS ──────────────────────────────────────────────────────────────────

def open_xian():
    hypr("foot bash -c 'cd /home/xina/xian && source venv/bin/activate && python xian.py; read'")

def open_firefox():
    hypr("firefox")

def open_btop():
    hypr("foot btop")

def open_thunar():
    hypr("thunar")

def open_terminal():
    hypr("foot")

def close_xian():
    run("pkill", "-f", "xian.py")

def close_firefox():
    run("pkill", "firefox")

def close_btop():
    run("pkill", "btop")

def close_thunar():
    run("pkill", "thunar")

def suspend():
    run("systemctl", "suspend")

def vol_up():
    run("wpctl", "set-volume", "@DEFAULT_SINK@", "10%+")

def vol_down():
    run("wpctl", "set-volume", "@DEFAULT_SINK@", "10%-")

def toggle_mute():
    run("wpctl", "set-mute", "@DEFAULT_SINK@", "toggle")

action_map = {
    "open_xian":        open_xian,
    "open_firefox":     open_firefox,
    "open_status":      open_btop,
    "open_terminal":    open_terminal,
    "vol_up":           vol_up,
    "vol_down":         vol_down,
    "mute":             toggle_mute,
}

# ─── COMMAND HANDLER ──────────────────────────────────────────────────────────

def handle_active(text: str):
    global state, last_action

    reset_timeout()

    if "again" in text and last_action:
        speak(RESPONSE["again"])
        action_map[last_action]()
        return

    if "terminal" in text:
        last_action = "open_terminal"
        speak(RESPONSE["open_terminal"])
        open_terminal()
        state = "idle"; cancel_timeout()

    elif "status" in text:
        last_action = "open_status"
        speak(RESPONSE["open_status"])
        open_btop()
        state = "idle"; cancel_timeout()

    elif "storage" in text:
        last_action = "open_storage"
        speak(RESPONSE["open_storage"])
        open_thunar()
        state = "idle"; cancel_timeout()

    elif "browser" in text or "firefox" in text:
        last_action = "open_firefox"
        speak(RESPONSE["open_firefox"])
        open_firefox()
        state = "idle"; cancel_timeout()

    elif WAKE_WORD in text:
        last_action = "open_xian"
        speak(RESPONSE["open_xian"])
        open_xian()
        state = "idle"; cancel_timeout()

    elif "sleep" in text:
        suspend()
        state = "idle"; cancel_timeout()

    elif "sound" in text:
        speak(RESPONSE["sound_mode"])
        state = "sound"
        reset_timeout()

    elif "close" in text or "tutup" in text:
        speak(RESPONSE["close_mode"])
        state = "close"
        reset_timeout()

    else:
        speak(RESPONSE["unknown"])


def handle_sound(text: str):
    global state, last_action

    if "naik" in text:
        last_action = "vol_up"
        speak(RESPONSE["vol_up"])
        vol_up()
    elif "down" in text:
        last_action = "vol_down"
        speak(RESPONSE["vol_down"])
        vol_down()
    elif "mute" in text:
        last_action = "mute"
        speak(RESPONSE["mute"])
        toggle_mute()
    else:
        speak(RESPONSE["cancel"])

    state = "idle"
    cancel_timeout()


def handle_close(text: str):
    global state

    if WAKE_WORD in text:
        speak(RESPONSE["close_xian"])
        close_xian()
    elif "browser" in text or "firefox" in text:
        speak(RESPONSE["close_firefox"])
        close_firefox()
    elif "status" in text:
        speak(RESPONSE["close_status"])
        close_btop()
    elif "storage" in text:
        speak(RESPONSE["close_storage"])
        close_thunar()
    else:
        speak(RESPONSE["cancel"])

    state = "idle"
    cancel_timeout()

# ─── MAIN LOOP ────────────────────────────────────────────────────────────────

print(f'[XIAN] Standby — bilang "{WAKE_WORD}" buat aktifin gw.')

while True:
    data = stream.read(8000, exception_on_overflow=False)

    if not rec.AcceptWaveform(data):
        continue

    text = json.loads(rec.Result()).get("text", "").lower()
    if not text:
        continue

    print(f"[{state.upper()}] heard: {text}")

    if state == "idle":
        if WAKE_WORD in text:
            speak(RESPONSE["wake"])
            state = "active"
            reset_timeout()

    elif state == "active":
        handle_active(text)

    elif state == "sound":
        handle_sound(text)

    elif state == "close":
        handle_close(text)