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

![Stigix CLI Interactive Console](/Users/jsuzanne/Github/stigix/docs/assets/stigix-cli-interactive.png)

| Shortcut | Action |
|---|---|
| **`F1`** | Instantly displays the main help screen |
| **`F5`** | Forces a status update / refresh of the bottom toolbar |
| **`Ctrl + L`** | Clears the terminal screen |
| **`Ctrl + C`** / `exit` / `quit` | Clars current input / Exits the shell |

---

## ⚙️ Automation & Headless Options

You can automate tasks by passing arguments directly to the docker execution command:

*   **Override Backend URL**: Connect to a remote Stigix instance.
    ```bash
    docker exec -it stigix stigix-cli --url http://192.168.1.100:8080
    ```
*   **Execute & Exit**: Run a command without opening the interactive prompt.
    ```bash
    docker exec -it stigix stigix-cli --exec "security suite"
    ```
*   **Run Script File**: Execute a text file containing commands (one command per line).
    ```bash
    docker exec -it stigix stigix-cli --script test-plan.txt
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

### 8. Digital Experience Management (`experience`)
*   `experience list` — List targets configured for connectivity/DEM probes.
*   `experience add --name <name> --host <ip/domain> --type <http/ping/dns>` — Add a new probe target.
*   `experience remove <id>` — Remove a probe target.
*   `experience probe` — Force execute a connectivity probe against all targets.
*(Note: the `target` command is supported as a backward-compatible alias for `experience`)*

---

### 9. Peer Targets (`peer`)
Manually manage Stigix peer nodes (which host echo responders, VoIP targets, and speedtest servers).

*   `peer list` — List all configured Stigix peer targets, their capabilities, and online status.
*   `peer add --name <name> --host <ip/domain>` — Add a new peer target manually. Optional flags: `--voice {true|false}`, `--convergence {true|false}`, `--xfr {true|false}`, `--security {true|false}`, `--connectivity {true|false}`.
*   `peer remove <id>` — Delete a peer target by ID.
*   `peer enable <id>` / `peer disable <id>` — Toggle a peer target's status.

---

### 10. Bandwidth Speedtests (`speedtest`)
Run iPerf3/XFR speedtests to evaluate path bandwidth, latency, and packet loss.

*   `speedtest list` or `speedtest history` — View the history of speedtest jobs and their results.
*   `speedtest run <host>` — Launch a default speedtest to a target peer host.
*   `speedtest run <host> [options]` — Launch a custom speedtest to a target host.
    *   **Options**: `--port <9000>`, `--protocol {tcp|udp|quic}`, `--direction {client-to-server|server-to-client|bidirectional}`, `--duration <sec>`, `--bitrate <rate>`, `--streams <num>`, `--psk <pwd>`.
    *   This command streams real-time performance updates (Tx/Rx throughput, RTT, and loss) directly in the console.

---

### 11. System Administration (`system`)
*   `system info` — Show backend CPU, memory, disk utilization, and uptime.
*   `system interfaces` — List network interfaces on the Stigix host.
*   `system logs` — Print the last 30 lines of general backend logs.
*   `system restart` — Restart the Stigix containers.
*   `system upgrade` — Pull the latest Docker images and upgrade Stigix.

---

## 📊 Command Output Examples

Here are some examples of CLI commands run via Docker against a live Stigix instance:

### 1. Check Global Instance Status
```bash
docker exec -it stigix stigix-cli --exec "status"
```
**Output:**
```text
━━ Stigix Status ━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Backend    [READY]  uptime ?s
→ Version    v1.4.0-patch.36
Traffic    [RUNNING]
→ Public IP  2.13.195.58
```

### 2. List Connectivity/DEM Probes
```bash
docker exec -it stigix stigix-cli --exec "experience list"
```
**Output:**
```text
  ID  Name                  Host/URL  Type   On
  ──  ────────────────────  ────────  ─────  ──
  ?   Cloudflare ICMP       ?         PING   ✓ 
  ?   Google ICMP           ?         PING   ✓ 
  ?   Google DNS Res        ?         DNS    ✓ 
  ?   Google Search         ?         HTTP   ✓ 
  ?   Hetzner ICMP          ?         PING   ✓ 
  ?   Hetzner Slow          ?         HTTP   ✓ 
  ?   Info / Egress         ?         CLOUD  ✓ 
  ?   Slow SaaS             ?         CLOUD  ✓ 
  ...
```

### 3. List Configured Stigix Peer Nodes
```bash
docker exec -it stigix stigix-cli --exec "peer list"
```
**Output:**
```text
  ID            Name        Host             Capabilities                                     On  Source     
  ────────────  ──────────  ───────────────  ───────────────────────────────────────────────  ──  ───────────
  30dbb12a-c6e  Hetzner     142.132.193.157  voice, convergence, xfr, security, connectivity  ✓   managed    
  syn-security  DC1-Ubuntu  192.168.203.100  voice, convergence, xfr, security, connectivity  ✓   synthesized
  reg-DC7-Ubun  DC7-Ubuntu  192.168.205.10   voice, convergence, xfr, security, connectivity  ✓   synthesized
  reg-BR8-Ubun  BR8-Ubuntu  192.168.219.1    voice, convergence, xfr, security, connectivity  ✓   synthesized
```

### 4. Run an Interactive Speedtest with Real-time Streaming
```bash
docker exec -it stigix stigix-cli --exec "speedtest run 142.132.193.157 --duration 10"
```
**Output:**
```text
→ Starting speedtest to 142.132.193.157:9000 (TCP / client-to-server)...
✓ Speedtest job XFR-0022 accepted.
→ Streaming real-time performance metrics (Ctrl+C to stop)...
  Tx: 0.0 Mbps   Rx: 0.0 Mbps   RTT: 0.0ms   Loss: 0.0%
  Tx: 0.7 Mbps   Rx: 0.0 Mbps   RTT: 230.5ms   Loss: 0.0%
  Tx: 1.3 Mbps   Rx: 0.0 Mbps   RTT: 234.7ms   Loss: 0.0%
  Tx: 1.7 Mbps   Rx: 0.0 Mbps   RTT: 231.5ms   Loss: 0.0%
  Tx: 1.6 Mbps   Rx: 0.0 Mbps   RTT: 235.4ms   Loss: 0.0%
  Tx: 1.1 Mbps   Rx: 0.0 Mbps   RTT: 230.9ms   Loss: 0.0%
  Tx: 1.3 Mbps   Rx: 0.0 Mbps   RTT: 229.5ms   Loss: 0.0%
  Tx: 0.9 Mbps   Rx: 0.0 Mbps   RTT: 234.1ms   Loss: 0.0%
  Tx: 1.2 Mbps   Rx: 0.0 Mbps   RTT: 233.0ms   Loss: 0.0%
  Tx: 1.0 Mbps   Rx: 0.0 Mbps   RTT: 235.4ms   Loss: 0.0%

✓ Speedtest COMPLETED successfully!
```
