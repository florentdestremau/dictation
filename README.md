# Dictation

Voice dictation tool for Ubuntu 24.04+ (Wayland/GNOME).

Quick mode: Alt+D to start/stop recording, text is automatically copied to clipboard.

## Installation

```bash
git clone git@github.com:florentdestremau/dictation.git
cd dictation
./install.sh
```

The installer sets up a single keyboard shortcut:
- **Alt+D** - Toggle recording, text copied to clipboard automatically

Configuration is stored in `~/.config/dictation/config.json`.

By default, transcription runs locally via [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (model `small`). The model is downloaded automatically on first launch (~500 MB).

## Usage

1. **Alt+D**: starts recording (notification appears)
2. **Speak** into your microphone
3. **Alt+D** again: stops recording and starts transcription
4. Notification shows the result and auto-closes
5. **Ctrl+V** to paste at cursor position

The app uses notifications only - no window opens, so your focus stays where it was.

## Using Groq instead of local model

For faster transcription via the [Groq](https://console.groq.com) API (free):

1. Create an API key at [console.groq.com](https://console.groq.com)
2. Edit `~/.config/dictation/config.json`:

```json
{
  "backend": "groq",
  "groq_api_key": "gsk_your_key_here",
  "groq_model": "whisper-large-v3-turbo"
}
```

## Requirements

- Ubuntu 24.04+ with Wayland
- Python 3.11+
- wl-clipboard (for clipboard access)
- libnotify-bin (for notifications)

Automatically installed by `install.sh`.

## Troubleshooting

**The shortcut doesn't work:**
- Check if the shortcut is configured: `gsettings get org.gnome.settings-daemon.plugins.media-keys custom-keybindings`
- Try running the command manually: `/home/florent/dev/dictation/dictation_launcher.sh`

**No sound recorded:**
- Check your microphone is working: `arecord -d 5 test.wav && aplay test.wav`
- Check system permissions for microphone access

**Text not appearing:**
- After the "Text copied" notification, use Ctrl+V to paste
- Check clipboard: `wl-paste`

**Model download fails:**
- First launch downloads ~500MB. Check your internet connection.
- Or switch to Groq API for cloud transcription (no local model needed)
