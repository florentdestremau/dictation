#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python3"

echo "=== Dictation - Installation ==="

# Dependances systeme
echo "Installation des dependances systeme..."
sudo apt install -y python3-venv wl-clipboard libnotify-bin

# Outils pour collage automatique
echo ""
echo "=== Outils de collage automatique ==="
echo "Pour coller automatiquement le texte à la fin de la dictée,"
echo "vous pouvez installer ydotool (simule Ctrl+V)"
echo ""

# Verifier si ydotool est deja installe
if command -v ydotool &> /dev/null; then
    echo "✓ ydotool est déjà installé"
else
    read -p "Installer ydotool pour le collage automatique ? (o/n) [o]: " install_ydotool
    install_ydotool=${install_ydotool:-o}
    
    if [[ "$install_ydotool" =~ ^[Oo]$ ]]; then
        echo "Installation de ydotool..."
        sudo apt install -y ydotool || {
            echo "⚠️  ydotool non disponible dans les dépôts"
            echo "Tentative d'installation via snap..."
            sudo snap install ydotool || echo "⚠️  Installation via snap échouée"
        }
        
        if command -v ydotool &> /dev/null; then
            echo "✓ ydotool installé"
            
            # Ajouter l'utilisateur au groupe input pour ydotool
            sudo usermod -a -G input "$USER"
            echo "✓ Ajouté au groupe 'input' (nécessite une reconnexion)"
        else
            echo "⚠️  ydotool n'a pas pu être installé automatiquement"
            echo "Le texte sera copié dans le presse-papier, vous collerez avec Ctrl+V"
        fi
    else
        echo "Installation de ydotool ignorée"
        echo "Le texte sera copié dans le presse-papier, vous collerez avec Ctrl+V"
    fi
fi

echo ""

# Environnement virtuel
echo "Creation de l'environnement virtuel..."
if [ ! -d "$SCRIPT_DIR/.venv" ]; then
    python3 -m venv "$SCRIPT_DIR/.venv"
fi
"$VENV_PYTHON" -m pip install -q -r "$SCRIPT_DIR/requirements.txt"

# Configuration
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/dictation"
mkdir -p "$CONFIG_DIR"
if [ ! -f "$CONFIG_DIR/config.json" ]; then
    echo "{}" > "$CONFIG_DIR/config.json"
    echo "Config creee : $CONFIG_DIR/config.json"
fi

# Fonction pour ajouter un raccourci GNOME
add_gnome_shortcut() {
    local name="$1"
    local command="$2"
    local binding="$3"
    
    EXISTING=$(gsettings get org.gnome.settings-daemon.plugins.media-keys custom-keybindings)
    
    # Trouver un slot libre
    SLOT=0
    while echo "$EXISTING" | grep -q "custom${SLOT}/"; do
        SLOT=$((SLOT + 1))
    done
    
    PATH_PREFIX="org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom${SLOT}/"
    gsettings set "$PATH_PREFIX" name "$name"
    gsettings set "$PATH_PREFIX" command "$command"
    gsettings set "$PATH_PREFIX" binding "$binding"
    
    # Ajouter le slot a la liste
    if [ "$EXISTING" = "@as []" ]; then
        NEW_LIST="['/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom${SLOT}/']"
    else
        NEW_LIST=$(echo "$EXISTING" | sed "s|]|, '/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom${SLOT}/']|")
    fi
    gsettings set org.gnome.settings-daemon.plugins.media-keys custom-keybindings "$NEW_LIST"
    
    echo "Raccourci configure : $binding -> $name"
}

# Choix du mode
echo ""
echo "=== Installation du mode rapide ==="
echo ""
echo "Raccourci : Alt+D"
echo ""
echo "Usage :"
echo "  - Alt+D : Démarre l'enregistrement"
echo "  - Parlez, puis Alt+D pour arrêter"
echo "  - Le texte est copié automatiquement"
echo "  - Ctrl+V pour coller"
echo ""

# Rendre le launcher exécutable
chmod +x "$SCRIPT_DIR/dictation_launcher.sh"

# Mode rapide uniquement
add_gnome_shortcut "Dictation Rapide" "$SCRIPT_DIR/dictation_launcher.sh --quick" "<Alt>d"

echo ""
echo "Installation terminée !"
echo ""
echo "Raccourci configuré : Alt+D"

echo ""
echo "Premier lancement : le modele whisper sera telecharge (~500 Mo si mode local)"
echo ""
echo "Configuration : $CONFIG_DIR/config.json"
