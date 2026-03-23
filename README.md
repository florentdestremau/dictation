# Dictation

Voice dictation tool for Ubuntu 24.04+ (Wayland/GNOME).

Two modes available:
- **Classic mode**: Dictate, review/edit, then copy
- **Quick mode**: Dictate and automatically paste at cursor position

## Installation

```bash
git clone git@github.com:florentdestremau/dictation.git
cd dictation
./install.sh
```

The script will ask you which mode you want:
1. **Classic** (Alt+D) - With review/editing step
2. **Quick** (Alt+D) - Direct copy, no editing
3. **Both** - Alt+D classic, Alt+Shift+D quick

Configuration is stored in `~/.config/dictation/config.json`.

By default, transcription runs locally via [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (model `small`). The model is downloaded automatically on first launch (~500 MB).

## Mode 1: Classic (Alt+D)

Best for when you want to review/edit text before using it.

1. **Alt+D**: opens the recording window
2. **Speak** into your microphone
3. **Enter**: stops recording and starts transcription
4. The text is displayed and can be edited
5. **Enter**: copies to clipboard and closes
6. **Escape**: closes without copying
7. **Alt+D** (while window is open): closes the window

## Mode 2: Quick (Alt+D or Alt+Shift+D)

Best for quick dictation when you trust the transcription.

1. **Alt+D** (or **Alt+Shift+D** if using both modes): opens small recording window
2. **Speak** into your microphone
3. **Enter**: stops recording, transcribes, and **automatically pastes** at cursor position
4. Window closes immediately

**Automatic paste**: The tool will try to paste the text automatically using `ydotool` or `wtype` (if installed). If neither is available, the text is copied to clipboard and you paste manually with Ctrl+V.

**Optional dependencies for auto-paste:**
```bash
# Option 1: ydotool
sudo apt install ydotool

# Option 2: wtype
sudo apt install wtype
```

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
# Mode classique (avec édition)
python3 dictation.py

# Mode rapide (copie directe)
python3 dictation.py --quick
```

**Note**: When using the keyboard shortcuts (Alt+D, Alt+Shift+D), the `dictation_launcher.sh` script is used instead. This launcher automatically handles permissions for `ydotool` without requiring logout/login.

## Requirements

- Ubuntu 24.04+ with Wayland
- Python 3.11+
- wl-clipboard (for clipboard access)
- libnotify-bin (for notifications)

**Optional (for automatic paste):**
- ydotool or wtype (to paste text automatically at cursor position)
