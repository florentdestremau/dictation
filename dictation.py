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
import wave
from pathlib import Path

import notify2
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


class NotificationManager:
    """Gestionnaire de notification unique qui se met à jour."""

    def __init__(self):
        self.notification = None
        try:
            notify2.init("Dictée")
        except Exception:
            pass

    def show(self, title: str, message: str = "", icon: str = ""):
        """Affiche ou met à jour la notification."""
        try:
            if self.notification is None:
                self.notification = notify2.Notification(title, message, icon)
                self.notification.set_timeout(5000)  # 5 secondes par défaut
            else:
                self.notification.update(title, message, icon)
            self.notification.show()
        except Exception:
            pass

    def close(self):
        """Ferme la notification."""
        try:
            if self.notification:
                self.notification.close()
                self.notification = None
        except Exception:
            pass


# Instance globale du gestionnaire de notification
_notification_mgr = NotificationManager()


def notify(title: str, message: str = "", icon: str = ""):
    """Met à jour la notification unique."""
    _notification_mgr.show(title, message, icon)


class QuickModeRecorder:
    """Headless mode with notifications, no window, preserves focus."""

    def __init__(self, config: dict):
        self.config = config
        self.recorder = AudioRecorder()
        self.transcriber = make_transcriber(config)
        self._recording = False
        self._stop_event = threading.Event()
        self._transcription_thread: threading.Thread | None = None

    def start(self):
        """Start recording in headless mode."""
        self._recording = True
        self._stop_event.clear()
        notify("🎤 Dictée", "Enregistrement démarré", "microphone-sensitivity-high")
        self.recorder.start()

    def stop_and_transcribe(self):
        """Stop recording, transcribe, and copy to clipboard."""
        if not self._recording:
            return

        notify("⏳ Dictée", "Transcription en cours...", "dialog-information")

        wav_path = self.recorder.stop()
        self._recording = False

        def transcribe_thread():
            try:
                text = self.transcriber.transcribe(wav_path)
                if text and not text.startswith("["):
                    # Copier dans le presse-papier
                    subprocess.Popen(
                        ["wl-copy", "--", text],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    notify(
                        "✅ Dictée",
                        f"Texte copié : {text[:50]}...",
                        "dialog-information",
                    )
                else:
                    notify("❌ Dictée", "Aucun texte détecté", "dialog-error")
            except Exception as e:
                notify("❌ Dictée", f"Erreur : {str(e)[:50]}", "dialog-error")
            finally:
                _notification_mgr.close()
                try:
                    os.unlink(wav_path)
                except Exception:
                    pass

        self._transcription_thread = threading.Thread(target=transcribe_thread)
        self._transcription_thread.start()


_quick_recorder: QuickModeRecorder | None = None


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
    config = load_config()

    # Mode headless avec notifications (seul mode disponible)
    # Vérifier si une instance tourne déjà
    try:
        with open(PIDFILE) as f:
            pid = int(f.read().strip())
        if _is_our_process(pid):
            # Toggle: envoyer signal pour arrêter
            try:
                os.kill(pid, signal.SIGUSR1)
                sys.exit(0)
            except ProcessLookupError:
                pass
    except (FileNotFoundError, ValueError):
        pass

    # Démarrer nouvelle instance
    _write_pid()

    recorder = QuickModeRecorder(config)
    global _quick_recorder
    _quick_recorder = recorder

    def handle_toggle(signum, frame):
        recorder.stop_and_transcribe()
        # Ne pas exit ici, laisser la boucle principale attendre la fin de la transcription

    signal.signal(signal.SIGUSR1, handle_toggle)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))

    recorder.start()

    # Maintenir le process en vie jusqu'à ce que la transcription soit terminée
    try:
        while recorder._recording:
            import time

            time.sleep(0.1)
        # Attendre que la transcription soit terminée
        if recorder._transcription_thread:
            recorder._transcription_thread.join(timeout=30)
    except KeyboardInterrupt:
        pass
    finally:
        _cleanup_pid()


if __name__ == "__main__":
    main()
