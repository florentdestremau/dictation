#!/usr/bin/env python3
"""Dictée vocale pour Ubuntu/Wayland avec faster-whisper ou API Groq."""

import argparse
import json
import os
import signal
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd

PIDFILE = os.path.join(tempfile.gettempdir(), "dictation.pid")
CONFIG_DIR = (
    Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "dictation"
)
CONFIG_PATH = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "backend": "local",  # "local" or "groq"
    "local_model": "small",
    "groq_model": "whisper-large-v3",
}


def load_config() -> dict:
    config = DEFAULT_CONFIG.copy()
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            config.update(json.load(f))
    config.setdefault("groq_api_key", os.environ.get("GROQ_API_KEY", ""))
    return config


class AudioRecorder:
    SAMPLE_RATE = 16000
    CHANNELS = 1

    def __init__(self):
        self._frames: list[np.ndarray] = []
        self._recording = False
        self._stream = None

    def start(self):
        self._frames = []
        self._recording = True
        self._stream = sd.InputStream(
            samplerate=self.SAMPLE_RATE,
            channels=self.CHANNELS,
            dtype="int16",
            callback=self._callback,
        )
        self._stream.start()

    def _callback(self, indata, frames, time, status):
        if self._recording:
            self._frames.append(indata.copy())

    def stop(self) -> str:
        """Stop recording and return path to a temporary WAV file."""
        self._recording = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        audio = (
            np.concatenate(self._frames)
            if self._frames
            else np.zeros((0, 1), dtype="int16")
        )
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        with wave.open(tmp, "wb") as wf:
            wf.setnchannels(self.CHANNELS)
            wf.setsampwidth(2)  # int16
            wf.setframerate(self.SAMPLE_RATE)
            wf.writeframes(audio.tobytes())
        return tmp.name


class LocalTranscriber:
    def __init__(self, model_name: str = "small"):
        self._model = None
        self._model_name = model_name

    def _load_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(self._model_name, compute_type="int8")

    def transcribe(self, wav_path: str) -> str:
        self._load_model()
        segments, _ = self._model.transcribe(
            wav_path,
            language="fr",
            beam_size=5,
            vad_filter=True,
            initial_prompt="Transcription en français avec ponctuation.",
        )
        return " ".join(seg.text.strip() for seg in segments).strip()


class GroqTranscriber:
    def __init__(self, api_key: str, model: str = "whisper-large-v3"):
        self._api_key = api_key
        self._model = model

    def transcribe(self, wav_path: str) -> str:
        import httpx

        with open(wav_path, "rb") as f:
            resp = httpx.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                data={"model": self._model, "language": "fr"},
                files={"file": ("audio.wav", f, "audio/wav")},
                timeout=30,
            )
        resp.raise_for_status()
        return resp.json()["text"].strip()


def make_transcriber(config: dict):
    if config["backend"] == "groq":
        return GroqTranscriber(config["groq_api_key"], config["groq_model"])
    return LocalTranscriber(config["local_model"])


def paste_text():
    """Try to paste text at cursor position using available tools."""
    # Try ydotool first (with input group if available)
    try:
        # First try direct execution (works after logout/login)
        subprocess.run(
            ["ydotool", "key", "29:1", "47:1", "47:0", "29:0"],
            capture_output=True,
            timeout=2,
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Try with sg (switch group) for current session
        try:
            subprocess.run(
                ["sg", "input", "-c", "ydotool key 29:1 47:1 47:0 29:0"],
                capture_output=True,
                timeout=2,
                check=True,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

    # Try wtype
    try:
        subprocess.run(
            ["wtype", "-M", "ctrl", "-k", "v", "-m", "ctrl"],
            capture_output=True,
            timeout=2,
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    return False


class DictationWindow:
    STATE_RECORDING = "recording"
    STATE_TRANSCRIBING = "transcribing"
    STATE_RESULT = "result"

    def __init__(self, config: dict, quick_mode: bool = False):
        self.recorder = AudioRecorder()
        self.transcriber = make_transcriber(config)
        self.result_text = ""
        self.quick_mode = quick_mode

        self.root = tk.Tk()
        self.root.title("Dictée")
        self.root.attributes("-topmost", True)
        self.root.protocol("WM_DELETE_WINDOW", self._close)

        # Poll for SIGTERM flag
        self._should_close = False
        self._poll_close()

        if quick_mode:
            # Petite fenêtre en mode quick
            width, height = 400, 150
            sx = self.root.winfo_screenwidth() // 2 - width // 2
            sy = self.root.winfo_screenheight() // 2 - height // 2
            self.root.geometry(f"{width}x{height}+{sx}+{sy}")

            self.label = tk.Label(
                self.root, text="", font=("Sans", 16), justify="center"
            )
            self.label.pack(expand=True, padx=16, pady=16)

            self.text = None  # Pas de zone de texte en mode quick
            self.hint = tk.Label(self.root, text="", font=("Sans", 10), fg="gray")
            self.hint.pack(side="bottom", pady=(0, 8))
        else:
            # Fenêtre normale avec édition
            width, height = 1000, 400
            sx = self.root.winfo_screenwidth() // 2 - width // 2
            sy = self.root.winfo_screenheight() // 2 - height // 2
            self.root.geometry(f"{width}x{height}+{sx}+{sy}")

            self.label = tk.Label(
                self.root, text="", font=("Sans", 14), justify="center"
            )
            self.label.pack(padx=16, pady=16)

            self.text = tk.Text(self.root, font=("Sans", 13), wrap="word", height=6)
            self.text.pack(expand=True, fill="both", padx=16, pady=(0, 8))
            self.text.pack_forget()  # hidden initially

            # Ctrl+Arrow / Ctrl+Backspace word navigation
            self.text.bind(
                "<Control-Left>",
                lambda e: (
                    self.text.mark_set("insert", "insert-1c wordstart"),
                    "break",
                ),
            )
            self.text.bind(
                "<Control-Right>",
                lambda e: (self.text.mark_set("insert", "insert wordend"), "break"),
            )
            self.text.bind(
                "<Control-BackSpace>",
                lambda e: (self.text.delete("insert-1c wordstart", "insert"), "break"),
            )

            self.hint = tk.Label(self.root, text="", font=("Sans", 10), fg="gray")
            self.hint.pack(side="bottom", pady=(0, 8))

        self.root.bind("<Return>", self._on_enter)
        self.root.bind("<Escape>", self._on_escape)

        self._set_state(self.STATE_RECORDING)
        self.recorder.start()

    def _poll_close(self):
        if self._should_close:
            self._close()
        else:
            self.root.after(100, self._poll_close)

    def _close(self):
        try:
            self.root.quit()
            self.root.destroy()
        except tk.TclError:
            pass

    def _set_state(self, state: str):
        self.state = state
        if state == self.STATE_RECORDING:
            if self.text:
                self.text.pack_forget()
            self.label.pack(padx=16, pady=16)
            self.label.config(text="\U0001f3a4 Enregistrement...")
            if self.quick_mode:
                self.hint.config(text="[Entrée] arrêter et copier  •  [Échap] annuler")
            else:
                self.hint.config(text="[Entrée] arrêter  •  [Échap] annuler")
        elif state == self.STATE_TRANSCRIBING:
            self.label.config(text="\u23f3 Transcription...")
            self.hint.config(text="")
        elif state == self.STATE_RESULT:
            if self.quick_mode:
                # En mode quick, on copie automatiquement et on essaie de coller
                if self.result_text and not self.result_text.startswith("[Erreur]"):
                    subprocess.run(["wl-copy", "--", self.result_text], check=True)
                    # Petit délai pour que le presse-papier soit prêt
                    import time

                    time.sleep(0.1)
                    # Essayer de coller automatiquement
                    if not paste_text():
                        # Si le collage échoue, on laisse le texte dans le presse-papier
                        print("Texte copié dans le presse-papier (collez avec Ctrl+V)")
                self._close()
            else:
                # Mode normal avec édition
                self.label.pack_forget()
                self.text.pack(expand=True, fill="both", padx=16, pady=(0, 8))
                self.text.config(state="normal")
                self.text.delete("1.0", "end")
                self.text.insert("1.0", self.result_text)
                self.text.focus_set()
                self.hint.config(text="[Entrée] copier  •  [Échap] annuler")

    def _on_enter(self, event):
        if self.state == self.STATE_RECORDING:
            wav_path = self.recorder.stop()
            self._set_state(self.STATE_TRANSCRIBING)
            threading.Thread(
                target=self._transcribe, args=(wav_path,), daemon=True
            ).start()
        elif self.state == self.STATE_RESULT:
            subprocess.Popen(["wl-copy", "--", self.text.get("1.0", "end-1c").strip()])
            self._close()

    def _on_escape(self, event):
        if self.state == self.STATE_RECORDING:
            self.recorder.stop()
        self._close()

    def _transcribe(self, wav_path: str):
        try:
            self.result_text = self.transcriber.transcribe(wav_path)
        except Exception as e:
            self.result_text = f"[Erreur] {e}"
        self.root.after(0, self._set_state, self.STATE_RESULT)

    def run(self):
        self.root.mainloop()


def _is_our_process(pid: int) -> bool:
    """Check if the PID is actually a running dictation.py process."""
    try:
        cmdline = Path(f"/proc/{pid}/cmdline").read_bytes().decode(errors="replace")
        return "dictation.py" in cmdline
    except (FileNotFoundError, PermissionError):
        return False


def _kill_existing() -> bool:
    """Kill a running instance if any. Returns True if one was killed."""
    try:
        with open(PIDFILE) as f:
            pid = int(f.read().strip())
        if not _is_our_process(pid):
            os.remove(PIDFILE)
            return False
        os.kill(pid, signal.SIGTERM)
        os.remove(PIDFILE)
        return True
    except (FileNotFoundError, ValueError, ProcessLookupError, PermissionError):
        try:
            os.remove(PIDFILE)
        except (FileNotFoundError, PermissionError):
            pass
        return False


def _write_pid():
    with open(PIDFILE, "w") as f:
        f.write(str(os.getpid()))


def _cleanup_pid(*_):
    try:
        os.remove(PIDFILE)
    except FileNotFoundError:
        pass


def main():
    parser = argparse.ArgumentParser(description="Dictée vocale")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Mode rapide : dicte et copie directement sans édition",
    )
    args = parser.parse_args()

    if _kill_existing():
        sys.exit(0)
    _write_pid()
    config = load_config()
    window = DictationWindow(config, quick_mode=args.quick)
    signal.signal(signal.SIGTERM, lambda *_: setattr(window, "_should_close", True))
    try:
        window.run()
    finally:
        _cleanup_pid()


if __name__ == "__main__":
    main()
