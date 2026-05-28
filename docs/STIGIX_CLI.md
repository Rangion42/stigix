# Stigix CLI Reference Guide

`stigix-cli` is an interactive console and automation tool for managing Stigix instances. It connects directly to the Stigix backend API, allowing you to trigger tests, view real-time traffic statistics, run security audits, control simulated IoT devices, and monitor router failover convergence.

---

## 🚀 Getting Started

Depending on how you have deployed Stigix, there are two ways to run the CLI.

### Option A: Via Docker (Recommended for Container Deployments)
If Stigix is installed via container, the CLI and all dependencies are pre-installed inside the container. You can run it directly from the host machine with:

```bash
# Start the interactive console
docker exec -it stigix stigix-cli

# Run a single command headless and exit
docker exec -it stigix stigix-cli --exec "status"
```

### Option B: From the Host Machine (Local Development)
To run the CLI directly from your local host machine, ensure python dependencies are installed first:

```bash
# 1. Install dependencies (requests and prompt_toolkit)
pip install requests prompt_toolkit

# 2. Run the interactive console
python Scripts/stigix-cli.py
```
*(Or use `.venv/bin/python Scripts/stigix-cli.py` if using the repository's virtual environment)*

---

## ⌨️ Interactive UI & Shortcuts

When running the interactive console, the CLI features auto-completion, command history, and a status toolbar at the bottom.

| Shortcut | Action |
|---|---|
| **`F1`** | Instantly displays the main help screen |
| **`F5`** | Forces a status update / refresh of the bottom toolbar |
| **`Ctrl + L`** | Clears the terminal screen |
| **`Ctrl + C`** / `exit` / `quit` | Clars current input / Exits the shell |

---

## ⚙️ Automation & Headless Options

You can automate tasks using arguments when launching the script:

*   **Override Backend URL**: Connect to a remote Stigix instance.
    ```bash
    stigix-cli --url http://192.168.1.100:8080
    ```
*   **Execute & Exit**: Run a command without opening the interactive prompt.
    ```bash
    stigix-cli --exec "security suite"
    ```
*   **Run Script File**: Execute a text file containing commands (one command per line).
    ```bash
    stigix-cli --script test-plan.txt
    ```

---

## 📚 Command Reference

### 1. Connection & Session (`connect`, `auth`)
The CLI automatically saves your active connection URL and authenticated JWT token in `~/.stigix-cli.json` for future sessions.

*   `auth login` — Authenticate with Stigix using username and password.
*   `auth status` — Check current session authentication status.
*   `auth logout` — Log out and clear saved JWT token.
*   `connect` — View current URL status and saved connection profiles.
*   `connect <ip>` — Switch the active connection to another Stigix IP.
*   `connect save <profile-name> [url]` — Save a named connection profile.
*   `connect list` — List all saved profiles.
*   `connect forget <profile-name>` — Remove a saved profile.

---

### 2. Traffic Generator (`traffic`)
*   `traffic start` — Start generating background traffic.
*   `traffic stop` — Stop generating traffic.
*   `traffic status` — Check if traffic generator is running or stopped.
*   `traffic stats` — View real-time counters and traffic metrics.
*   `traffic logs` — Print the latest log entries from the traffic generator.
*   `traffic reset` — Reset statistics counters to zero.
*   `traffic watch [interval]` — Launch a live dashboard refreshing every *N* seconds (default: 3s).

---

### 3. Security Audits (`security`)
Simulates traffic corresponding to security capabilities of Palo Alto Networks SASE (Prisma Access) to test blocking behavior.

*   `security status` — Show aggregate metrics of blocked/allowed queries.
*   `security suite` — **Run a complete automated security audit** (URL batch, DNS batch, and Threat prevention).
*   `security url <url>` — Perform a single URL Filtering test.
*   `security url-batch` — Test all URL categories enabled in the current configuration.
*   `security dns <domain>` — Perform a single DNS security test.
*   `security dns-batch` — Test all DNS domains enabled in the config.
*   `security eicar [endpoint]` — Perform an EICAR Threat Prevention test against a specific target.
*   `security results [n]` — View the last *N* security logs (default: 20).
*   `security clear` — Clear all security test results from the history database.

---

### 4. Convergence & Failover (`convergence`)
Used to measure packet loss and network recovery time during link/routing failovers.

*   `convergence status` — Show if a blackout test is currently running.
*   `convergence start --target <ip> --pps <pps> --label <label>` — Start sending probe packets to measure failover.
*   `convergence stop` — Stop the active blackout test.
*   `convergence history [n]` — View past failover test results and blackout times.
*   `convergence endpoints` — List configured probe targets.
*   `convergence watch [interval]` — Watch real-time probe loss and latency metrics.

---

### 5. Router Actions (`vyos`)
Control and trigger sequence configurations on VyOS routers.

*   `vyos list` — List all connected VyOS routers.
*   `vyos sequences` — List available automation sequences.
*   `vyos run <sequence-id>` — Trigger a sequence (e.g., block/unblock WAN links).
*   `vyos stop <sequence-id>` — Terminate a running sequence.
*   `vyos history [n]` — Show past command sequence execution history.

---

### 6. IoT Simulation (`iot`)
Manage simulated IoT devices and view vulnerability findings.

*   `iot list` — List all simulated IoT devices and their states.
*   `iot start [device-id]` — Start simulation for one or all IoT devices.
*   `iot stop [device-id]` — Stop simulation for one or all IoT devices.
*   `iot stats` — Show total sent packages and simulation bandwidth.
*   `iot vulns [n]` — View vulnerability scan logs (CVE findings, severity, and device mappings).

---

### 7. VoIP Testing (`voice`)
Measure VoIP link quality using Mean Opinion Score (MOS).

*   `voice status` — Show if a voice test is currently active.
*   `voice start --target <ip> --codec <codec> --duration <sec>` — Start a VoIP test. Codecs: `g711`, `g729`, `opus`.
*   `voice stop` — Terminate a running VoIP test.
*   `voice stats` — View MOS score, Jitter, Packet Loss, and RTT.

---

### 8. Target Management (`target`)
*   `target list` — List targets configured for connectivity probes.
*   `target add --name <name> --host <ip/domain> --type <http/ping/dns>` — Add a new custom target.
*   `target remove <id>` — Remove a custom target.
*   `target probe` — Force execute a connectivity probe against all targets.

---

### 9. System Administration (`system`)
*   `system info` — Show backend CPU, memory, disk utilization, and uptime.
*   `system interfaces` — List network interfaces on the Stigix host.
*   `system logs` — Print the last 30 lines of general backend logs.
*   `system restart` — Restart the Stigix containers.
*   `system upgrade` — Pull the latest Docker images and upgrade Stigix.
