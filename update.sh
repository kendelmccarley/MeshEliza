#!/usr/bin/env bash
# update.sh — pull latest MeshEliza code and reinstall
#
# Usage:
#   bash update.sh
#
# Run from the MeshEliza repo directory as your normal user.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$HOME/.venv/mesheliza"

echo "=== MeshEliza Updater ==="

# ------------------------------------------------------------------ #
# 1. Pull latest code                                                  #
# ------------------------------------------------------------------ #
echo ">>> Pulling latest changes from origin..."
git -C "$SCRIPT_DIR" pull origin main

# ------------------------------------------------------------------ #
# 2. Clear Python bytecode caches                                      #
# ------------------------------------------------------------------ #
echo ">>> Flushing Python bytecode caches..."
find "$SCRIPT_DIR" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find "$SCRIPT_DIR" -name "*.pyc" -delete 2>/dev/null || true

# ------------------------------------------------------------------ #
# 3. Reinstall into the virtualenv                                     #
# ------------------------------------------------------------------ #
if [[ ! -f "$VENV_DIR/bin/activate" ]]; then
    echo ""
    echo "ERROR: virtualenv not found at $VENV_DIR"
    echo "Please run install.sh first."
    exit 1
fi

echo ">>> Reinstalling package into virtualenv..."
source "$VENV_DIR/bin/activate"
pip install -e "$SCRIPT_DIR" --no-cache-dir --quiet

# ------------------------------------------------------------------ #
# 4. Confirm what is now installed                                     #
# ------------------------------------------------------------------ #
echo ""
echo "=== Update complete ==="
echo ""
echo "Installed commit:"
git -C "$SCRIPT_DIR" log --oneline -1
echo ""
echo "Package version:"
pip show mesheliza | grep -E "^(Name|Version|Location):"
echo ""
echo "To launch: ./mesheliza.sh"
