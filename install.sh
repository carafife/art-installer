#!/bin/bash
# =====================================================================
# Installateur ART — mise en place du programme dans le menu
#
#   ./install.sh            installe l'Installateur ART pour l'utilisateur
#   ./install.sh --remove   le retire (ne touche jamais à ART lui-même)
#
# Tout reste dans l'espace utilisateur : ~/.local/share, ~/.local/bin.
# =====================================================================
set -euo pipefail

APP_ID="io.github.carafife.ArtInstaller"
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="$HOME/.local/share/art-installer"
BIN="$HOME/.local/bin/art-installer"
DESKTOP="$HOME/.local/share/applications/$APP_ID.desktop"
ICON="$HOME/.local/share/icons/hicolor/scalable/apps/$APP_ID.svg"

if [ "${1:-}" = "--remove" ]; then
    rm -rf "$DEST"
    rm -f "$BIN" "$DESKTOP" "$ICON"
    echo "Installateur ART retiré. (ART lui-même n'a pas été touché.)"
    exit 0
fi

# Dépendances : Python + GTK4 + libadwaita (déjà présentes sur Fedora Workstation)
if ! python3 -c "import gi; gi.require_version('Gtk','4.0'); gi.require_version('Adw','1')" 2>/dev/null; then
    echo "Il manque GTK4 / libadwaita pour Python. Sur Fedora, lance :"
    echo
    echo "    sudo dnf install python3-gobject gtk4 libadwaita"
    echo
    echo "puis relance ./install.sh"
    exit 1
fi

mkdir -p "$DEST/data" "$(dirname "$BIN")" "$(dirname "$DESKTOP")" "$(dirname "$ICON")"
cp -f "$SRC/art-installer.py" "$SRC/core.py" "$DEST/"
cp -f "$SRC/data/$APP_ID.svg" "$SRC/data/$APP_ID.png" "$DEST/data/"
cp -f "$SRC/data/$APP_ID.svg" "$ICON"
chmod +x "$DEST/art-installer.py"
ln -sf "$DEST/art-installer.py" "$BIN"

sed "s|@EXEC@|$BIN|" "$SRC/data/$APP_ID.desktop.in" > "$DESKTOP"
command -v update-desktop-database >/dev/null && update-desktop-database "$(dirname "$DESKTOP")" >/dev/null 2>&1 || true
command -v gtk-update-icon-cache >/dev/null && gtk-update-icon-cache -q -t "$HOME/.local/share/icons/hicolor" >/dev/null 2>&1 || true

echo "Installateur ART installé."
echo "Lance-le depuis le menu des applications, ou avec la commande : art-installer"
