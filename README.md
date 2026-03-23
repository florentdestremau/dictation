# Dictation

Voice dictation tool for Ubuntu 24.04+ (Wayland/GNOME).

Two modes available:
- **Quick mode** (Alt+D): Notifications only, direct copy to clipboard
- **Classic mode** (Alt+Shift+D): Window with review/editing step

## Installation

```bash
git clone git@github.com:florentdestremau/dictation.git
cd dictation
./install.sh
```

The script will ask you which mode you want:
1. **Quick** (Alt+D) - Notifications only, copy to clipboard
2. **Classic** (Alt+Shift+D) - With review/editing step
3. **Both** (recommended) - Alt+D quick, Alt+Shift+D classic

Configuration is stored in `~/.config/dictation/config.json`.

By default, transcription runs locally via [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (model `small`). The model is downloaded automatically on first launch (~500 MB).

## Mode 1: Quick (Alt+D)

Best for quick dictation when you trust the transcription.

1. **Alt+D**: starts recording (notification appears)
2. **Speak** into your microphone
3. **Alt+D** again: stops recording and starts transcription
4. Notification "Text copied" appears
5. **Ctrl+V** to paste at cursor position

The quick mode uses notifications only - no window opens, so your focus stays where it was.

## Mode 2: Classic (Alt+Shift+D)

Best for when you want to review/edit text before using it.

1. **Alt+Shift+D**: opens the recording window
2. **Speak** into your microphone
3. **Enter**: stops recording and starts transcription
4. The text is displayed and can be edited
5. **Enter**: copies to clipboard and closes
6. **Escape**: closes without copying
7. **Alt+Shift+D** (while window is open): closes the window

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

## Command Line Options

```bash
# Quick mode (notifications only, direct copy)
python3 dictation.py --quick

# Classic mode (with editing window)
python3 dictation.py
```

**Note**: When using the keyboard shortcuts (Alt+D, Alt+Shift+D), the `dictation_launcher.sh` script is used instead. This launcher handles permissions properly.

## Requirements

- Ubuntu 24.04+ with Wayland
- Python 3.11+
- wl-clipboard (for clipboard access)
- libnotify-bin (for notifications)

Automatically installed by `install.sh`.

## Troubleshooting

**The shortcut doesn't work:**
- Check if the shortcut is configured: `gsettings get org.gnome.settings-daemon.plugins.media-keys custom-keybindings`
- Try running the command manually: `/home/florent/dev/dictation/dictation_launcher.sh --quick`

**No sound recorded:**
- Check your microphone is working: `arecord -d 5 test.wav && aplay test.wav`
- Check system permissions for microphone access

**Text not appearing:**
- After the "Text copied" notification, use Ctrl+V to paste
- Check clipboard: `wl-paste`

**Model download fails:**
- First launch downloads ~500MB. Check your internet connection.
- Or switch to Groq API for cloud transcription (no local model needed)
