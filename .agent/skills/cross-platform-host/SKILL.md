---
name: cross-platform-host
description: >
  Cross-platform awareness guide for commands targeting external hosts.
  Use this skill whenever you are about to generate a shell command, script,
  or file path intended for a host whose OS is unknown or could be
  Windows, Linux, or macOS.
---

# Cross-Platform Host Awareness Skill

Use this skill **before generating any command, script, file path, or configuration
intended for an external or user-managed host** — including setup instructions, 
installation steps, diagnostic commands, or automation scripts.

## Core Principle

**Never assume the host OS.** Unless the user has explicitly stated their OS
or it is evident from context (e.g., a Docker container is always Linux),
always identify the OS before proposing commands, or provide platform-specific
variants for all supported OSes.

Stigix is deployed across:
- 🐧 **Linux** — most common (Debian/Ubuntu servers, Raspberry Pi, VMs)
- 🪟 **Windows** — common for MCP bridge hosts and developer machines
- 🍎 **macOS** — common for developer machines and MCP bridge hosts

---

## Step 1 — Identify the Target OS

### If the user has not stated their OS, ask:

> "What OS is the target host running? (Linux / Windows / macOS)"

Or propose detection commands:
```bash
# Linux/macOS
uname -s

# Windows (PowerShell)
[System.Environment]::OSVersion.Platform

# Universal (Python)
python3 -c "import platform; print(platform.system())"
```

### OS Clues to look for in context:
- Mentions of `C:\`, `%AppData%`, `cmd.exe`, `.bat`, `.ps1` → Windows
- Mentions of `apt`, `systemctl`, `/etc/`, `/home/`, `sudo` → Linux
- Mentions of `brew`, `/Users/`, `launchctl`, `zsh` → macOS
- Docker containers are **always Linux** — even if the Docker host is Windows/macOS
- The Stigix backend container is **always Linux**

---

## Step 2 — Critical Differences by Category

### 📁 File Paths

| Concern | Linux/macOS | Windows |
|---|---|---|
| Separator | `/` | `\` (or `/` in PowerShell/WSL) |
| Home dir | `~` or `/home/user` | `%USERPROFILE%` or `C:\Users\user` |
| Temp dir | `/tmp` | `%TEMP%` or `C:\Windows\Temp` |
| App data | `~/.config` | `%AppData%` |
| Absolute paths | `/absolute/path` | `C:\absolute\path` |

### 🖥️ Shell / Command Syntax

| Concern | Linux/macOS (bash/zsh) | Windows (cmd) | Windows (PowerShell) |
|---|---|---|---|
| Env variable | `$VAR` | `%VAR%` | `$env:VAR` |
| Set env var | `export VAR=value` | `set VAR=value` | `$env:VAR = "value"` |
| Command chaining | `cmd1 && cmd2` | `cmd1 && cmd2` | `cmd1; cmd2` |
| Redirect to file | `cmd > file.txt` | `cmd > file.txt` | `cmd > file.txt` |
| Read file | `cat file.txt` | `type file.txt` | `Get-Content file.txt` |
| List directory | `ls -la` | `dir` | `Get-ChildItem` |
| Copy file | `cp src dst` | `copy src dst` | `Copy-Item src dst` |
| Delete file | `rm file` | `del file` | `Remove-Item file` |
| Create directory | `mkdir -p path` | `mkdir path` | `New-Item -ItemType Directory` |
| Background process | `command &` | `start /B command` | `Start-Process -NoNewWindow` |
| Line endings | LF (`\n`) | CRLF (`\r\n`) | CRLF (`\r\n`) |

### 📦 Package Management

| Task | Debian/Ubuntu | RHEL/CentOS | macOS | Windows |
|---|---|---|---|---|
| Install package | `apt install pkg` | `dnf install pkg` | `brew install pkg` | `choco install pkg` or `winget install pkg` |
| Update packages | `apt update && apt upgrade` | `dnf update` | `brew update && brew upgrade` | `choco upgrade all` |
| Install Python | `apt install python3` | `dnf install python3` | `brew install python3` | Download from python.org |
| Install pip pkg | `pip3 install pkg` | `pip3 install pkg` | `pip3 install pkg` | `pip install pkg` (or `pip3`) |

### 🔧 Service Management

| Task | Linux (systemd) | macOS | Windows |
|---|---|---|---|
| Start service | `systemctl start svc` | `launchctl load ...` or `brew services start svc` | `Start-Service svc` or `sc start svc` |
| Stop service | `systemctl stop svc` | `launchctl unload ...` | `Stop-Service svc` |
| Enable on boot | `systemctl enable svc` | `launchctl enable ...` | `Set-Service -StartupType Automatic` |
| View logs | `journalctl -u svc -f` | `log show` | `Get-EventLog` |

### 🐍 Python Virtual Environments

| Action | Linux/macOS | Windows (cmd) | Windows (PowerShell) |
|---|---|---|---|
| Create venv | `python3 -m venv .venv` | `python -m venv .venv` | `python -m venv .venv` |
| Activate | `source .venv/bin/activate` | `.venv\Scripts\activate.bat` | `.venv\Scripts\Activate.ps1` |
| Deactivate | `deactivate` | `deactivate` | `deactivate` |
| Run with venv | `.venv/bin/python3 script.py` | `.venv\Scripts\python.exe script.py` | `.venv\Scripts\python.exe script.py` |

### 🐳 Docker

Docker commands are **identical** across all platforms — Docker normalizes the interface.
However, watch out for:
- **Volume mounts**: Use `/` on Linux/macOS, but Windows paths need escaping or use WSL paths
  - Linux/macOS: `-v /host/path:/container/path`
  - Windows (PowerShell): `-v C:\host\path:/container/path`
  - Windows (cmd): `-v C:/host/path:/container/path`
- **Line endings in scripts**: Dockerfiles and shell scripts copied into containers must use **LF**, not CRLF. Files created on Windows can break Linux containers.
- **Permissions**: `chmod` commands in Dockerfiles always target the **Linux container** — they work regardless of host OS.

---

## Step 3 — Writing Cross-Platform Instructions

When writing setup steps or documentation for Stigix (MCP bridge, CLI, etc.), always:

### ✅ DO
- Provide separate code blocks per OS, labeled clearly:
  ```bash
  # Linux / macOS
  source .venv/bin/activate
  ```
  ```powershell
  # Windows (PowerShell)
  .venv\Scripts\Activate.ps1
  ```
- Note when a step is OS-independent (e.g., `pip install` works the same everywhere)
- Prefer Python or Docker commands where possible — they work the same on all platforms
- Use forward slashes `/` in Docker-related paths (always Linux target)

### ❌ DON'T
- Assume `python` means Python 3 (Linux often requires `python3`; Windows may have `py`)
- Assume bash is available (Windows doesn't have it by default — use PowerShell or cmd)
- Use bash-isms (`$(...)`, `source`, `export`) in scripts intended for Windows
- Use `cat` on Windows cmd (use `type` instead)
- Use `&&` for chaining in PowerShell (use `;` instead)
- Forget that `%VAR%` in Windows cmd is `$env:VAR` in PowerShell

---

## Step 4 — Stigix-Specific Context

| Component | Runs on | Notes |
|---|---|---|
| Stigix backend | **Linux** (Docker) | Always Linux, even if host is Windows |
| Stigix web dashboard | **Linux** (Docker) | Same |
| Stigix MCP bridge (`bridge.py`) | **User's machine** — any OS | Most common: macOS or Linux, sometimes Windows |
| Stigix CLI (`stigix-cli.py`) | **User's machine** — any OS | Python 3 required; venv path differs by OS |
| Stigix VyOS router | **Linux** (VyOS VM) | Always Linux |
| MCP bridge `.venv` | **User's machine** | Activation command varies by OS (see above) |

### MCP Bridge — OS-specific `claude_desktop_config.json`

The path to the Python interpreter in the Claude Desktop config must match the OS:

```json
// Linux / macOS
{
  "command": "/path/to/stigix/mcp-server/.venv/bin/python3",
  "args": ["/path/to/stigix/mcp-server/bridge.py", "http://YOUR_NODE_IP:3100/sse"]
}
```

```json
// Windows
{
  "command": "C:\\path\\to\\stigix\\mcp-server\\.venv\\Scripts\\python.exe",
  "args": ["C:\\path\\to\\stigix\\mcp-server\\bridge.py", "http://YOUR_NODE_IP:3100/sse"]
}
```

---

## Quick Decision Checklist

Before generating any host-targeting command, ask yourself:

- [ ] Do I know the target OS? If not, ask or provide variants for all 3.
- [ ] Is this a Docker command? → OS-independent (use Linux paths for volumes).
- [ ] Does this use shell syntax (`$`, `&&`, `source`)? → Need Windows alternative.
- [ ] Does this involve a file path? → Use platform separator or use Python `os.path`.
- [ ] Does this involve Python venv? → Activation path differs by OS.
- [ ] Does this script get shipped in a Docker image? → Must use LF line endings.
