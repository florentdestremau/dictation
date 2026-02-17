#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Dictation - Installation ==="

# Dependances systeme
echo "Installation des dependances systeme..."
sudo apt install -y python3-tk python3-venv wl-clipboard

# Environnement virtuel
echo "Creation de l'environnement virtuel..."
python3 -m venv "$SCRIPT_DIR/.venv"
"$SCRIPT_DIR/.venv/bin/pip" install -q -r "$SCRIPT_DIR/requirements.txt"

# Configuration
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/dictation"
mkdir -p "$CONFIG_DIR"
if [ ! -f "$CONFIG_DIR/config.json" ]; then
    echo "{}" > "$CONFIG_DIR/config.json"
    echo "Config creee : $CONFIG_DIR/config.json"
fi

# Raccourci clavier GNOME
echo "Configuration du raccourci clavier Alt+D..."
EXISTING=$(gsettings get org.gnome.settings-daemon.plugins.media-keys custom-keybindings)

# Trouver un slot libre
SLOT=0
while echo "$EXISTING" | grep -q "custom${SLOT}/"; do
    SLOT=$((SLOT + 1))
done

PATH_PREFIX="org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom${SLOT}/"
gsettings set "$PATH_PREFIX" name "Dictation"
gsettings set "$PATH_PREFIX" command "$SCRIPT_DIR/.venv/bin/python3 $SCRIPT_DIR/dictation.py"
gsettings set "$PATH_PREFIX" binding "<Alt>d"

# Ajouter le slot a la liste
if [ "$EXISTING" = "@as []" ]; then
    NEW_LIST="['/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom${SLOT}/']"
else
    NEW_LIST=$(echo "$EXISTING" | sed "s|]|, '/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom${SLOT}/']|")
fi
gsettings set org.gnome.settings-daemon.plugins.media-keys custom-keybindings "$NEW_LIST"

echo ""
echo "Installation terminee !"
echo "Raccourci : Alt+D"
echo "Premier lancement : le modele whisper sera telecharge (~500 Mo)"
