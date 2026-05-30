#!/bin/bash

# Stigix MCP Bridge Setup Script
# This script automates the creation of a local Python environment to run the Claude MCP bridge.

set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MCP_DIR="$REPO_DIR/mcp-server"
VENV_PATH="$MCP_DIR/.venv"

echo "🚀 Setting up Stigix MCP Bridge in $MCP_DIR..."

if [ ! -d "$MCP_DIR" ]; then
    echo "❌ Error: mcp-server directory not found at $MCP_DIR"
    exit 1
fi

cd "$MCP_DIR"

# 1. Detect a Python executable that is >= 3.10
PYTHON_CMD=""
for cmd in python3.13 python3.12 python3.11 python3.10 python3 python; do
    if command -v "$cmd" &> /dev/null; then
        MAJOR=$("$cmd" -c 'import sys; print(sys.version_info.major)' 2>/dev/null || echo 0)
        MINOR=$("$cmd" -c 'import sys; print(sys.version_info.minor)' 2>/dev/null || echo 0)
        if [ "$MAJOR" -eq 3 ] && [ "$MINOR" -ge 10 ]; then
            PYTHON_CMD="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    DETECTED_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo "unknown")
    echo "❌ Error: Python 3.10 or higher is required (default python3 is version $DETECTED_VER)."
    echo "Please install a newer version of Python. On macOS, you can do this easily via Homebrew:"
    echo "    brew install python@3.11"
    echo ""
    echo "Once installed, run this script again."
    exit 1
fi

echo "🐍 Using Python executable: $(command -v "$PYTHON_CMD") ($($PYTHON_CMD -V))"

# 2. Create Virtualenv if missing
if [ ! -d "$VENV_PATH" ]; then
    echo "📦 Creating virtual environment..."
    "$PYTHON_CMD" -m venv "$VENV_PATH"
fi

# 3. Install/Update Dependencies
echo "📥 Installing dependencies..."
"$VENV_PATH/bin/pip" install --upgrade pip
"$VENV_PATH/bin/pip" install -r "$MCP_DIR/requirements.txt"

echo ""
echo "✅ Setup Complete!"
echo "--------------------------------------------------------"
echo "To use this bridge in Claude Desktop, use these paths:"
echo ""
echo "Python: $VENV_PATH/bin/python3"
echo "Bridge: $MCP_DIR/bridge.py"
echo "--------------------------------------------------------"
echo "Example Test Command:"
echo "$VENV_PATH/bin/python3 $MCP_DIR/bridge.py http://<NODE_IP>:3100/sse"
