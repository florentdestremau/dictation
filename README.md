# Dictation

Voice dictation tool for Ubuntu 24.04+ (Wayland/GNOME).

Press a keyboard shortcut, speak, and the transcribed text is copied to your clipboard.

## Installation

```bash
git clone git@github.com:florentdestremau/dictation.git
cd dictation
./install.sh
```

The script installs dependencies, creates the virtual environment and sets up the **Alt+D** keyboard shortcut.

Configuration is stored in `~/.config/dictation/config.json` (created automatically by `install.sh`).

By default, transcription runs locally via [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (model `small`). The model is downloaded automatically on first launch (~500 MB).

## Usage

1. **Alt+D**: opens the recording window
2. **Speak** into your microphone
3. **Enter**: stops recording and starts transcription
4. The text is displayed and can be edited
5. **Enter**: copies to clipboard and closes
6. **Escape**: closes without copying
7. **Alt+D** (while window is open): closes the window

## Using Groq instead of the local model

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
