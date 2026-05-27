#!/usr/bin/env bash
# stigix-cli installer — installs the CLI on the local host (no Docker needed)
#
# Usage:
#   bash install-cli.sh               # install from repo (local copy)
#   bash install-cli.sh --uninstall   # remove stigix-cli
#
# What it does:
#   1. Checks python3 is available
#   2. Installs requests + prompt_toolkit (pip / pip3)
#   3. Copies stigix-cli.py to /usr/local/lib/stigix/ (or ~/.local/lib/stigix/)
#   4. Creates a wrapper at /usr/local/bin/stigix-cli (or ~/.local/bin/)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLI_SRC="$SCRIPT_DIR/stigix-cli.py"

# ─── Uninstall ─────────────────────────────────────────────────────────────────
if [[ "${1:-}" == "--uninstall" ]]; then
  echo "Removing stigix-cli..."
  rm -f /usr/local/bin/stigix-cli ~/.local/bin/stigix-cli
  rm -rf /usr/local/lib/stigix ~/.local/lib/stigix
  echo "✓ stigix-cli removed"
  exit 0
fi

# ─── Check source file ─────────────────────────────────────────────────────────
if [[ ! -f "$CLI_SRC" ]]; then
  echo "[error] Cannot find stigix-cli.py at: $CLI_SRC"
  exit 1
fi

# ─── Check Python 3 ────────────────────────────────────────────────────────────
PYTHON=""
for candidate in python3 python; do
  if command -v "$candidate" &>/dev/null; then
    VER=$("$candidate" -c "import sys; print(sys.version_info.major)")
    if [[ "$VER" == "3" ]]; then
      PYTHON="$candidate"
      break
    fi
  fi
done

if [[ -z "$PYTHON" ]]; then
  echo "[error] python3 not found — install Python 3.8+ first"
  exit 1
fi

PYTHON_VER=$("$PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "→ Using $PYTHON ($PYTHON_VER)"

# ─── Determine install prefix (root or user) ───────────────────────────────────
if [[ $EUID -eq 0 ]] || sudo -n true 2>/dev/null; then
  # Has root / passwordless sudo
  USE_SUDO=true
  LIB_DIR="/usr/local/lib/stigix"
  BIN_DIR="/usr/local/bin"
else
  # No root — install to ~/.local (no sudo needed)
  USE_SUDO=false
  LIB_DIR="$HOME/.local/lib/stigix"
  BIN_DIR="$HOME/.local/bin"
  echo "→ No root access — installing to user prefix (~/.local/)"
fi

# ─── Install Python dependencies ───────────────────────────────────────────────
echo "→ Installing Python dependencies (requests, prompt_toolkit)..."

PIP=""
for candidate in pip3 pip; do
  if command -v "$candidate" &>/dev/null; then
    PIP="$candidate"
    break
  fi
done

if [[ -n "$PIP" ]]; then
  "$PIP" install --quiet --user requests prompt_toolkit 2>/dev/null || \
  "$PYTHON" -m pip install --quiet --user requests prompt_toolkit 2>/dev/null || \
  echo "[warn] Could not install dependencies — run manually: pip install requests prompt_toolkit"
else
  "$PYTHON" -m pip install --quiet --user requests prompt_toolkit 2>/dev/null || \
  echo "[warn] pip not found — run manually: pip install requests prompt_toolkit"
fi

# ─── Copy script ───────────────────────────────────────────────────────────────
echo "→ Installing stigix-cli to $LIB_DIR..."
mkdir -p "$LIB_DIR"
cp "$CLI_SRC" "$LIB_DIR/stigix-cli.py"

# ─── Create wrapper ────────────────────────────────────────────────────────────
mkdir -p "$BIN_DIR"
WRAPPER="$BIN_DIR/stigix-cli"

cat > "$WRAPPER" << WRAPPER_SCRIPT
#!/usr/bin/env bash
export STIGIX_URL="\${STIGIX_URL:-http://localhost:8080}"
exec $PYTHON $LIB_DIR/stigix-cli.py "\$@"
WRAPPER_SCRIPT

chmod +x "$WRAPPER"

# ─── PATH check ────────────────────────────────────────────────────────────────
echo ""
echo "✓ stigix-cli installed at $WRAPPER"
echo ""

if ! echo "$PATH" | grep -q "$BIN_DIR"; then
  echo "⚠  $BIN_DIR is not in your PATH."
  echo "   Add this to your shell profile (~/.zshrc or ~/.bashrc):"
  echo ""
  echo "     export PATH=\"\$PATH:$BIN_DIR\""
  echo ""
fi

# ─── Quick test ────────────────────────────────────────────────────────────────
if "$PYTHON" "$LIB_DIR/stigix-cli.py" --help &>/dev/null; then
  echo "✓ Installation verified"
else
  echo "[warn] Verification failed — check manually: $WRAPPER"
fi

echo ""
echo "Usage:"
echo "  stigix-cli                             # Interactive (localhost:8080)"
echo "  stigix-cli --url http://IP:8080        # Connect to remote instance"
echo "  stigix-cli --exec 'status'             # Single command, headless"
echo ""
echo "To remove:  bash install-cli.sh --uninstall"
