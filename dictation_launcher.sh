#!/bin/bash
# Launcher for dictation with input group permissions
# This allows ydotool to work without logout/login

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python3"

# Check if user is in input group
if groups | grep -q "\binput\b"; then
    # User is in input group, use sg to run with input group permissions
    # This avoids the need for logout/login
    exec sg input -c "$VENV_PYTHON $SCRIPT_DIR/dictation.py $*"
else
    # User not in input group, run normally (paste will use clipboard only)
    exec $VENV_PYTHON $SCRIPT_DIR/dictation.py "$@"
fi
