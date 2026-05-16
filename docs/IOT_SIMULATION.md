# 🤖 IoT Simulation & Device Management

The **SD-WAN Traffic Generator** includes a sophisticated IoT Simulation engine that allows network engineers to simulate a variety of IoT devices (cameras, sensors, smart plugs) on their network for testing security, segmentation, and failover.

## 🚀 Key Capabilities

### 📡 Layer-2/3 Simulation (Scapy)
Unlike standard traffic generators that use high-level HTTP libraries, our IoT engine uses **Scapy** to forge raw packets at the network layer.
- **DHCP Support**: Simulated devices can request and renew IP addresses from your real local DHCP server (Router/Core Switch).
- **DHCP Lease Persistence**: Each device's assigned IP is saved to disk. On container restart, the device uses [RFC 2131 INIT-REBOOT](https://www.rfc-editor.org/rfc/rfc2131#section-3.2) to reclaim the same IP — no DISCOVER needed if the server accepts.
- **ARP Handling**: Devices respond to ARP requests on the wire, making them appear "real" to networking equipment.
- **MAC Spoofing**: Each simulated device has its own unique, configurable MAC address.

## Platform Compatibility

### ✅ Full IoT Support (Host Mode - Linux Only)
IoT simulation with DHCP, ARP, and Layer 2 protocols requires **Host Mode networking**, which is only available on **native Linux installations**.

**Supported:**
- Ubuntu (bare metal or VM)
- Debian
- CentOS/RHEL
- Other native Linux distributions

**Requirements:**
- Native Linux (not WSL2)
- Docker installed
- Root/sudo access for network capabilities

### ⚠️ Limited IoT Support (Bridge Mode)
On macOS, Windows, and WSL2, IoT simulation runs in **Bridge Mode** with these limitations:

**Platforms:**
- macOS (Docker Desktop)
- Windows (Docker Desktop + WSL2)
- WSL2 (Windows Subsystem for Linux)

**Limitations:**
- ❌ No DHCP simulation
- ❌ No ARP spoofing
- ❌ No Layer 2 protocol simulation
- ✅ HTTP/HTTPS traffic simulation still works
- ✅ Voice/RTP simulation works (with reduced features)

**Why:** Docker's Host Mode networking is not supported on macOS and Windows. These platforms use a VM-based Docker engine that doesn't expose the host network stack directly.

## 🛠️ Use Cases

1. **SD-WAN Segmentation**: Verify that IoT traffic is correctly identified and placed into the "IoT VRF" or "Guest VLAN".
2. **Failover Testing**: See how IoT devices (which are often sensitive to jitter) behave when a circuit fails or a policy change occur.
3. **Security Validation**: Test your firewall rules against mock IoT traffic without having to purchase and wire up dozens of physical devices.

## 📝 Configuration

IoT devices are managed via the **IoT Tab** in the Dashboard. The configuration is stored in `config/iot-devices.json`.

*Device gallery displaying all simulated IoT hardware with their current network status:*
<img src="screenshots/05-IOT/04-iot-device-gallery.png" width="700" alt="IoT Device Gallery" />



### Technical JSON Format

Each device in the JSON array follows this structure:

```json
{
  "id": "hikvis_security_cameras_01",
  "name": "Hikvision DS-2CD2042FWD",
  "vendor": "Hikvision",
  "type": "Security Camera",
  "mac": "00:12:34:56:78:01",
  "ip_start": "192.168.207.100",
  "protocols": ["dhcp", "arp", "lldp", "http", "rtsp", "cloud", "dns", "ntp"],
  "enabled": true,
  "traffic_interval": 180,
  "description": "Hikvision DS-2CD2042FWD - Security Camera",
  "fingerprint": {
    "dhcp": {
      "hostname": "DS-2CD2042FWD",
      "vendor_class_id": "HIKVISION",
      "client_id_type": 1,
      "param_req_list": [1, 3, 6, 12, 15, 28, 42, 51, 54, 58, 59]
    }
  }
}
```

**Key Fields:**
- `fingerprint.dhcp` - DHCP fingerprint for device identification by Palo Alto IoT Security
- `hostname` - DHCP Option 12
- `vendor_class_id` - DHCP Option 60
- `param_req_list` - DHCP Option 55 (Parameter Request List)

*Configuration modal for defining device identity, MAC address, and supported protocols:*
<img src="screenshots/05-IOT/01-iot-edit-device-basic.png" width="700" alt="IoT Device Configuration Modal" />




### 🤖 Device Configuration Generation

You have **three methods** to generate realistic IoT device configurations:

#### 1. Python Script Generator (Recommended for Speed)
Use the `generate_iot_devices.py` script for fast, deterministic device generation with built-in DHCP fingerprints.

**Features:**
- ✅ Instant generation (< 1 second)
- ✅ 13 device categories, 50+ vendors, 200+ models
- ✅ DHCP fingerprinting support
- ✅ Presets: Small (30), Medium (65), Large (110), Enterprise (170)
- ✅ Offline - no API calls required

**Quick Start:**
```bash
# Generate medium lab (65 devices)
python iot/generate_iot_devices.py --preset medium

# Custom configuration
python iot/generate_iot_devices.py --custom "Security Cameras:10,Sensors:20,Smart Lighting:15"
```

📖 **Full Documentation:** [IOT_DEVICE_GENERATOR.md](IOT_DEVICE_GENERATOR.md)

---

#### 2. LLM-Based Generation (Recommended for Custom Scenarios)
Use ChatGPT, Claude, or Gemini to generate industry-specific device configurations with contextual narratives.

**Features:**
- ✅ Industry-specific device mixes (Healthcare, Manufacturing, Utilities, etc.)
- ✅ Customer-tailored configurations
- ✅ Realistic vendor diversity
- ✅ DHCP fingerprints included

**Quick Start:**
Copy the prompt template from `iot/IOT_PROMPT.txt` and customize for your use case.

📖 **Full Documentation:** [IOT_LLM_GENERATION.md](IOT_LLM_GENERATION.md)

---

#### 3. Device Security Asset Import (Recommended for Real Environments)

If your customer already has **Palo Alto IoT Security** or **Prisma Access** deployed, you can export a real device inventory CSV and convert it directly into a Stigix emulator config. This produces the most accurate simulation because it is based on real devices observed on the customer's network.

**Features:**
- ✅ Uses real MAC addresses, hostnames, and vendor profiles from the customer network
- ✅ Extracts protocols from observed `Applications` telemetry (Prisma's real column name)
- ✅ **OS-aware DHCP fingerprinting** — overrides generic vendor defaults with actual OS signatures:
  - Windows → `MSFT 5.0` + Windows-specific Option 55
  - iOS → `dhcpcd-9.4.1` + iOS Option 55
  - Linux / Embedded → `udhcp` variants
  - Enea OSE (medical infusion pumps) → `Enea OSE`
  - FortiOS → `FortiGate`
  - macOS → `AAPLBSDPC/i386`
- ✅ **Asset Criticality** used as secondary bad-behavior signal (when `ml_risk_level` is missing)
- ✅ Automatically enables `bad_behavior` for `Critical` and `High` risk devices
- ✅ Sorts devices by risk level (Critical first) for `--max-devices` filtering
- ✅ Generates credible DHCP fingerprints per vendor (Hikvision, Axis, Apple, Rockwell…)
- ✅ Filters IoT-only devices (excludes PCs, VMs, tablets with `--only-iot`)
- ✅ Enriched `description` field: profile | OS | Risk level | Criticality | Wire/Wireless | VLAN

**Import via UI (Recommended):**

The dashboard provides a unified **Import** dropdown to restore configurations or ingest third-party assets.

<img src="screenshots/05-IOT/05-iot-import-dropdown.png" width="450" alt="Import Dropdown" />

1. Go to **IoT Simulation** -> click the **Import** button in the header toolbar.
2. Select **Device Security Assets** to import from a Palo Alto IoT Security CSV export.
3. In the modal, drag & drop your CSV file and configure your conversion options (max devices, risk level fallback, etc.).

<img src="screenshots/05-IOT/06-iot-import-assets-modal.png" width="500" alt="Device Security Assets Modal" />

4. Click **Convert & Import** to populate your simulation lab.

> The UI validates the CSV format client-side before sending to the server, rejecting non-compatible files immediately.

**Or via CLI:**
```bash
# Export device list from Prisma IoT Security dashboard as CSV, then:
python iot/import_prisma_devices.py -i "iot device bad sources.csv" -o devices.json

# IoT devices only, top 30 riskiest
python iot/import_prisma_devices.py -i "iot device bad sources.csv" -o devices.json --only-iot --max-devices 30

# Force bad behavior on 40% of devices
python iot/import_prisma_devices.py -i "iot device bad sources.csv" -o devices.json --security-percentage 40
```

📖 **Full Documentation:** [IOT_DEVICE_GENERATOR.md → Prisma CSV Import](IOT_DEVICE_GENERATOR.md#-prisma--iot-security-csv-import)

---

**Then (CLI workflow only):**
1. Copy the generated JSON
2. Go to the **IoT Tab** in the dashboard
3. Click **Import Json**
4. Paste the JSON
5. Start simulating!



### Protocol Support Details
- **`dhcp`**: Triggers a Scapy-based DHCP state machine (Discover → Offer → Request → Ack) with RFC 2131 INIT-REBOOT lease persistence (see below).
- **`arp`**: Listens for ARP Who-Has requests and responds with the spoofed MAC.
- **`cloud`**: Simulates periodic outbound "heartbeat" traffic to a vendor-specific FQDN.
- **`mqtt`**: Simulates periodic telemetry updates to an MQTT broker.

---

## 📋 DHCP Lease Persistence (RFC 2131 INIT-REBOOT)

By default, a DHCP server with no MAC reservations may assign a **different IP** to a device after a container restart. To solve this, the IoT emulator persists each device's assigned IP in a lease file that survives restarts.

### How it works

```
Boot device (MAC: aa:bb:cc:dd:ee:ff)
      │
      ▼
 config/dhcp_leases.json exists for this MAC?
      │
    YES ──► Last known IP: 192.168.1.42
      │           │
      │           ▼
      │    DHCP REQUEST broadcast (INIT-REBOOT, no DISCOVER)
      │    Option 50: requested_addr = 192.168.1.42
      │           │
      │         ACK ──► ✅ Same IP confirmed (~4s, fast path)
      │         NAK ──► 🔄 Subnet changed → full DISCOVER
      │     timeout ──► 🔄 No response   → full DISCOVER
      │
     NO ──► Full DISCOVER → OFFER → REQUEST → ACK (normal flow)
```

### Lease file location

Leases are stored in **`/app/config/dhcp_leases.json`**, which maps to the `./config/` directory of your Stigix installation — a persistent Docker volume.

```json
{
  "00:12:34:56:78:01": {
    "ip": "192.168.1.100",
    "gateway": "192.168.1.1",
    "timestamp": 1747386000.0
  },
  "ec:b5:fa:00:01:01": {
    "ip": "192.168.1.105",
    "gateway": "192.168.1.1",
    "timestamp": 1747386060.0
  }
}
```

> **Override:** Set the `DHCP_LEASE_FILE` environment variable to use a different path.

### Key behaviours

| Scenario | Result |
|---|---|
| Normal boot, saved lease, server ACKs | ✅ Same IP reclaimed instantly |
| Server NAKs (subnet changed, IP taken) | 🔄 Automatic fallback to full DISCOVER |
| Server doesn't respond to INIT-REBOOT | 🔄 Automatic fallback to full DISCOVER |
| Device never had an IP (first boot) | ➡️ Normal DISCOVER, no lease to restore |
| DHCP fails completely (no OFFER) | 🔕 Device stays silent, lease **not erased** (retry on next boot) |

---

## 🛡️ Security Testing (Bad Behavior)

The IoT engine includes a **Security Testing** mode designed to validate malicious behavior detection (e.g., Palo Alto Networks IoT Security). 

When **Bad Behavior** is enabled, the simulated device will generate traffic patterns matching known attack profiles:
- **DNS Flood**: Rapid DNS queries to various domains.
- **C2 Beacon**: Periodic "heartbeat" connections to simulated Command & Control domains.
- **Port Scan**: Internal scanning of the local subnet.
- **Data Exfil**: Simulated large data transfers to external IPs.
- **PAN Test Domains**: Generates traffic to official Palo Alto test domains for guaranteed detection.

*Security testing dashboard for triggering malicious traffic patterns and C2 beaconing:*
<img src="screenshots/05-IOT/02-iot-edit-device-bad-behavior.png" width="700" alt="IoT Bad Behavior Configuration" />



### JSON Security Configuration

To enable bad behavior, include the `security` object in your device configuration.

#### 1. Palo Alto Networks Test Domains (Recommended for Validation)
Guaranteed to be detected by PAN-OS DNS Security and URL Filtering.
```json
"security": {
  "bad_behavior": true,
  "behavior_type": ["pan_test_domains"]
}
```

#### 2. C2 Beaconing
Simulates a classic malware heartbeat every 10 seconds.
```json
"security": {
  "bad_behavior": true,
  "behavior_type": ["beacon"]
}
```

#### 3. DNS Flood
Rapid burst of DNS queries for malicious domains.
```json
"security": {
  "bad_behavior": true,
  "behavior_type": ["dns_flood"]
}
```

#### 4. Port Scan
Internal reconnaissance scanning local gateway and neighbors.
```json
"security": {
  "bad_behavior": true,
  "behavior_type": ["port_scan"]
}
```

#### 5. Data Exfiltration
Large TCP uploads to known malicious external IPs.
```json
"security": {
  "bad_behavior": true,
  "behavior_type": ["data_exfil"]
}
```

#### 6. Parallel Attack (Random Mix)
Launches multiple attack threads simultaneously for high complexity.
```json
"security": {
  "bad_behavior": true,
  "behavior_type": ["random", "dns_flood", "beacon"]
}
```

## 📊 Visual Diagnostics & Logs

When a device starts, you can monitor the "Real-on-the-Wire" interaction in the UI logs via the **Real-time Analysis** modal:

*Real-time analysis logs showing low-level Scapy packet interaction and DHCP handshakes:*
<img src="screenshots/05-IOT/03-iot-realtime-logs-dhcp.png" width="700" alt="IoT Real-time Analysis Logs" />



When a device starts, you can monitor the "Real-on-the-Wire" interaction in the UI logs:

### DHCP — First boot (full sequence)
```text
🚀 Starting device simulation: Smart Bulb (bulb-01) [DHCP: auto]
🆔 MAC addr: ec:b5:fa:00:01:01
🔄 DHCP attempt 1 (mode: auto)...
📤 DHCP DISCOVER (xid: 0x1a2b3c4d, MAC: ec:b5:fa:00:01:01)
⏳ Waiting for DHCP OFFER (timeout: 4s)...
✅ DHCP OFFER from 192.168.1.1 (offered: 192.168.1.105)
📤 DHCP REQUEST for offered IP 192.168.1.105
⏳ Waiting for DHCP ACK (timeout: 4s)...
✅ DHCP ACK: 192.168.1.105 from 192.168.1.1
📣 Gratuitous ARP: 192.168.1.105 is-at ec:b5:fa:00:01:01
✅ DHCP complete (IP: 192.168.1.105, GW: 192.168.1.1)
```

### DHCP — Container restart (INIT-REBOOT fast path)
```text
🚀 Starting device simulation: Smart Bulb (bulb-01) [DHCP: auto]
🆔 MAC addr: ec:b5:fa:00:01:01
📋 Saved DHCP lease found: 192.168.1.105 — attempting INIT-REBOOT (RFC 2131)
📤 DHCP INIT-REBOOT REQUEST for 192.168.1.105 (xid: 0x5e6f7a8b)
✅ INIT-REBOOT success — same IP confirmed: 192.168.1.105
🌐 Gateway from DHCP: 192.168.1.1
📣 Gratuitous ARP: 192.168.1.105 is-at ec:b5:fa:00:01:01
```

### DHCP — INIT-REBOOT rejected (subnet changed)
```text
📋 Saved DHCP lease found: 10.0.0.50 — attempting INIT-REBOOT (RFC 2131)
📤 DHCP INIT-REBOOT REQUEST for 10.0.0.50 (xid: 0x3c4d5e6f)
⚠️ DHCP NAK for saved IP 10.0.0.50 (subnet changed?)
🔄 INIT-REBOOT rejected by server — falling back to full DISCOVER
🔄 DHCP attempt 1 (mode: auto)...
📤 DHCP DISCOVER ...
✅ DHCP complete (IP: 192.168.1.200, GW: 192.168.1.1)
```

### ARP Interaction
```text
🔍 [IOT] ARP Request from Router (192.168.1.1): Who has 192.168.1.105?
📤 [IOT] ARP Reply: 192.168.1.105 is at ec:b5:fa:00:01:01
```

## 📥 Import / Export
You can easily migrate your IoT lab setup between different generator instances using the **Import/Export** buttons. The system ensures data integrity and automatically creates backups of your configuration.

---

## 💾 State Persistence

Stigix preserves your IoT simulation state across container reboots and upgrades. This is controlled via **Settings → System Info → State Persistence**.

### How it works

| Action | Immediate effect | Persisted in JSON | Effect on next boot |
|---|---|---|---|
| **Start** a device | Process starts | `enabled: true` | ✅ Device resumes |
| **Stop** a device | Process stops | `enabled: false` | ⛔ Device stays off |
| **Start-all** | All processes start | `enabled: true` for each | ✅ All resume |
| **Stop-all** | All processes stop | `enabled: false` for each | ⛔ All stay off |

> **Only devices that were running before the reboot will automatically restart.** If you started device A and left devices B and C stopped, after a reboot only device A will resume.

### Enable / Disable State Persistence

Go to **Settings → System Info → State Persistence** and toggle **IoT Simulation**:
- **ON** (default: OFF) — IoT devices restore their pre-reboot state 15 seconds after the container boots.
- **OFF** — No IoT devices start automatically; you start them manually from the IoT tab.

> The IoT toggle is only clickable if at least one device is configured. If your `iot-devices.json` is empty, the toggle remains grayed out with a configuration prompt.

---
*For more technical details on networking, see [SMART_NETWORKING.md](SMART_NETWORKING.md).*
