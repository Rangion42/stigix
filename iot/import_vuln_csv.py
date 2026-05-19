#!/usr/bin/env python3
"""
import_vuln_csv.py

Converts a Palo Alto IoT Security VULNERABILITY CSV export (one row per CVE per device)
into a Stigix IoT emulator JSON config file compatible with iot_emulator.py.

Unlike import_prisma_devices.py (which expects one row per device), this script
handles the vulnerability-centric format where each row represents one CVE on one device.

Aggregation strategy:
  - Group rows by (Device Name, IP Address, MAC Address)
  - Compute a composite "danger score" per device:
      = Risk Score (from CSV, 0–100)
      + Critical CVE count × 15
      + High CVE count × 8
      + Medium CVE count × 3
      + Unique APT group count × 5
      + ICS-CERT flag bonus × 10 (OT/ICS relevance)
  - Sort by danger score descending
  - Select top N devices

Usage:
  python import_vuln_csv.py --input vulns.csv --output devices.json
  python import_vuln_csv.py --input vulns.csv --output devices.json --max-devices 30
  python import_vuln_csv.py --input vulns.csv --output devices.json --max-devices 50 --enable-security
  python import_vuln_csv.py --input vulns.csv --output devices.json --security-percentage 60
  python import_vuln_csv.py --input vulns.csv --output devices.json --only-iot
"""

import csv
import json
import argparse
import random
import re
import sys
from collections import defaultdict
from pathlib import Path


# ─── Shared tables (same as import_prisma_devices.py) ─────────────────────────

CATEGORY_PROTOCOLS = {
    "Camera":                   ["dhcp", "arp", "lldp", "http", "rtsp", "dns", "ntp"],
    "Infusion System":          ["dhcp", "arp", "http", "dns"],
    "SCADA Server":             ["dhcp", "arp", "lldp", "http", "dns"],
    "Industrial Controller":    ["dhcp", "arp", "lldp", "http", "dns"],
    "Digital Signage":          ["dhcp", "arp", "http", "dns", "ntp"],
    "Network Equipment":        ["dhcp", "arp", "lldp", "http", "dns"],
    "Smartphone or Tablet":     ["dhcp", "arp", "http", "dns", "ntp"],
    "Personal Computer":        ["dhcp", "arp", "http", "dns", "ntp"],
    "Specialized PC":           ["dhcp", "arp", "http", "dns", "ntp"],
    "Workstation":              ["dhcp", "arp", "http", "dns", "ntp"],
    "Virtual Machine":          ["dhcp", "arp", "http", "dns"],
    "default":                  ["dhcp", "arp", "http", "dns"],
}

OS_DHCP_FINGERPRINTS = {
    "windows": {
        "vendor_class_id": "MSFT 5.0",
        "param_req_list": [1, 15, 3, 6, 44, 46, 47, 31, 33, 249, 43, 252],
    },
    "ios": {
        "vendor_class_id": "dhcpcd-9.4.1",
        "param_req_list": [1, 121, 3, 6, 15, 119, 252, 95, 44, 46],
    },
    "macos": {
        "vendor_class_id": "AAPLBSDPC/i386",
        "param_req_list": [1, 121, 3, 6, 15, 119, 252, 95, 44, 46],
    },
    "linux": {
        "vendor_class_id": "udhcp 1.30.0",
        "param_req_list": [1, 28, 2, 3, 15, 6, 119, 12, 44, 47],
    },
    "embedded": {
        "vendor_class_id": "udhcp 0.9.8",
        "param_req_list": [1, 3, 6, 12, 15, 28, 51, 58, 59],
    },
    "fortios": {
        "vendor_class_id": "FortiGate",
        "param_req_list": [1, 3, 6, 12, 15, 28, 51, 54, 58, 59],
    },
}

SEVERITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3, "": 4}

# Severity → bad behavior signal
HIGH_SEVERITY_BEHAVIORS = {"Critical", "High"}

# Profile Vertical → normalize IoT classification
IOT_VERTICALS = {"generic iot", "iot", "industrial", "medical", "operational technology"}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def safe(d, key, default=""):
    return (d.get(key) or "").strip()


def normalize_mac(mac_raw: str) -> str:
    if not mac_raw:
        return ""
    mac = mac_raw.strip().lower()
    mac = re.sub(r'-slot-\d+$', '', mac).strip()
    if re.match(r'^([0-9a-f]{2}:){5}[0-9a-f]{2}$', mac):
        return mac
    if re.match(r'^([0-9a-f]{2}-){5}[0-9a-f]{2}$', mac):
        return mac.replace('-', ':')
    hex_only = re.sub(r'[^0-9a-f]', '', mac)
    if len(hex_only) == 12:
        return ':'.join(hex_only[i:i+2] for i in range(0, 12, 2))
    return ""


def get_dhcp_fingerprint(os_str: str, vendor: str, hostname: str) -> dict:
    """OS-aware DHCP fingerprint, same logic as import_prisma_devices.py."""
    if os_str:
        os_lower = os_str.lower()
        for os_key, fp in OS_DHCP_FINGERPRINTS.items():
            if os_key in os_lower:
                return {
                    "hostname": hostname or f"{vendor or 'device'}-iot",
                    "vendor_class_id": fp["vendor_class_id"],
                    "client_id_type": 1,
                    "param_req_list": fp["param_req_list"],
                }
    return {
        "hostname": hostname or f"{vendor or 'device'}-iot",
        "vendor_class_id": f"{vendor or 'Generic'} IoT Device",
        "client_id_type": 1,
        "param_req_list": [1, 3, 6, 15, 28, 51, 58, 59],
    }


def make_device_id(name: str, ip: str, counter: int) -> str:
    slug = re.sub(r"[^a-z0-9]", "_", (name or ip or "dev").lower())[:12].strip("_")
    return f"{slug}_{counter:03d}"


def is_iot_vertical(vertical: str) -> bool:
    return vertical.lower().strip() in IOT_VERTICALS


MAC_RE = re.compile(r'^([0-9a-f]{2}[:\-]){5}[0-9a-f]{2}$', re.IGNORECASE)


def is_mac_like(s: str) -> bool:
    """Return True if the string looks like a MAC address (xx:xx:xx:xx:xx:xx)."""
    return bool(MAC_RE.match(s.strip())) if s else False


def resolve_device_name(raw_name: str, profile: str, vendor: str, model: str,
                        name_counters: dict) -> str:
    """
    If raw_name is a MAC address (or empty), generate a human-readable name
    from the device Profile, falling back to Vendor/Model or a generic label.
    Multiple devices sharing the same base name get an incrementing suffix:
      Raspberry Pi Device → Raspberry Pi Device #1, #2 ...
    """
    if raw_name and not is_mac_like(raw_name):
        return raw_name  # Name is already human-readable — keep it

    # Derive base name from profile / vendor / model
    if profile and profile.strip():
        base = profile.strip()
    elif vendor and model and model.lower() not in ("unknown model", ""):
        base = f"{vendor} {model}".strip()
    elif vendor and vendor not in ("Unknown", ""):
        base = f"{vendor} Device"
    else:
        base = "IoT Device"

    # Increment counter for this base name
    name_counters[base] = name_counters.get(base, 0) + 1
    return f"{base} #{name_counters[base]}"

def parse_apt_names(apt_str: str) -> list[str]:
    """Parse comma-separated APT names, ignoring empty/quoted empty strings."""
    if not apt_str or apt_str.strip() in ('', '""', "''"):
        return []
    return [a.strip() for a in apt_str.split(',') if a.strip() and a.strip() not in ('""', "''")]


# ─── Aggregation ──────────────────────────────────────────────────────────────

def aggregate_devices(rows: list[dict]) -> list[dict]:
    """
    Aggregate one-row-per-CVE into one-entry-per-device.
    Returns a list of aggregated device dicts sorted by danger_score descending.
    """
    # Key: (device_name, ip, mac) → avoid MAC collisions across different devices
    buckets: dict[tuple, dict] = defaultdict(lambda: {
        # Identity
        "name": "", "ip": "", "mac": "", "vendor": "", "model": "",
        "os": "", "profile": "", "vertical": "", "site_name": "",
        "risk_score": 0, "risk_level": "",
        # CVE aggregation
        "cves": [],           # list of {cve, cvss, severity, ics_cert, status, apt_names, first_detected}
        "apt_groups": set(),  # unique APT group names across all CVEs
        "has_ics": False,     # any ICS-CERT entry
        # Computed scoring
        "danger_score": 0,
    })

    for row in rows:
        name = safe(row, "Device Name")
        ip   = safe(row, "IP Address")
        mac  = normalize_mac(safe(row, "MAC Address"))
        if not mac or mac == "00:00:00:00:00:00":
            mac = ""

        key = (name, ip, mac)
        d = buckets[key]

        # Device-level fields (set from first row for this device)
        if not d["name"]:
            d["name"]       = name
            d["ip"]         = ip
            d["mac"]        = mac
            d["vendor"]     = safe(row, "Vendor")
            d["model"]      = safe(row, "Model")
            d["os"]         = safe(row, "OS")
            d["profile"]    = safe(row, "Profile")
            d["vertical"]   = safe(row, "Profile Vertical")
            d["site_name"]  = safe(row, "Site Name")
            # Risk score: keep as int, default 0
            try:
                d["risk_score"] = int(float(safe(row, "Risk Score") or "0"))
            except (ValueError, TypeError):
                d["risk_score"] = 0
            d["risk_level"] = safe(row, "Risk Level")

        # CVE-level fields
        cve       = safe(row, "CVE")
        ics_cert  = safe(row, "ICS-Cert")
        severity  = safe(row, "Severity")
        status    = safe(row, "Status")
        apt_str   = safe(row, "APT Names")
        first_det = safe(row, "First Detected Time")

        try:
            cvss = float(safe(row, "CVSS") or "0")
        except (ValueError, TypeError):
            cvss = 0.0

        apts = parse_apt_names(apt_str)

        if cve:
            d["cves"].append({
                "cve":      cve,
                "cvss":     cvss,
                "severity": severity,
                "ics_cert": ics_cert,
                "status":   status,
                "apt_names": apts,
                "first_detected": first_det,
            })
            d["apt_groups"].update(apts)
            if ics_cert:
                d["has_ics"] = True

    # Compute danger scores
    aggregated = []
    for d in buckets.values():
        crit = sum(1 for c in d["cves"] if c["severity"] == "Critical")
        high = sum(1 for c in d["cves"] if c["severity"] == "High")
        med  = sum(1 for c in d["cves"] if c["severity"] == "Medium")
        apt_count  = len(d["apt_groups"])
        ics_bonus  = 10 if d["has_ics"] else 0
        max_cvss   = max((c["cvss"] for c in d["cves"]), default=0.0)

        danger = (
            d["risk_score"]          # 0–100 from Prisma
            + crit * 15              # Critical CVEs are most impactful
            + high * 8
            + med  * 3
            + apt_count * 5          # APT association = elevated threat intel
            + ics_bonus              # ICS-CERT = OT/ICS relevance
            + int(max_cvss * 2)      # CVSS 10 = +20 bonus
        )
        d["danger_score"] = danger
        d["cve_count"]    = len(d["cves"])
        d["critical_count"] = crit
        d["high_count"]   = high
        d["apt_count"]    = apt_count
        d["max_cvss"]     = max_cvss
        d["apt_groups"]   = sorted(d["apt_groups"])  # convert set → sorted list
        aggregated.append(d)

    aggregated.sort(key=lambda x: x["danger_score"], reverse=True)
    return aggregated


# ─── Device builder (Stigix JSON format) ──────────────────────────────────────

def build_stigix_device(d: dict, counter: int, enable_security: bool,
                        security_percentage: int | None,
                        name_counters: dict) -> dict:
    """Convert an aggregated device entry into a Stigix IoT device JSON object."""

    raw_name = d["name"]
    vendor   = d["vendor"] or "Unknown"
    model    = d["model"] or ""
    os_str   = d["os"]
    profile  = d["profile"]
    mac      = d["mac"]

    # Resolve human-readable name (replace MAC-like names)
    name = resolve_device_name(raw_name, profile, vendor, model, name_counters)

    # Ensure a valid MAC
    if not mac or mac == "00:00:00:00:00:00":
        mac = ":".join(f"{random.randint(0, 255):02x}" for _ in range(6))

    # Device type from profile, fallback generic
    device_type = profile or "IoT Device"

    # Protocols from profile
    protocols = list(set(CATEGORY_PROTOCOLS.get(profile, CATEGORY_PROTOCOLS["default"])))
    if any(k in (profile or "").lower() for k in ["camera", "industrial", "scada", "plc", "controller"]):
        if "lldp" not in protocols:
            protocols.append("lldp")

    # DHCP fingerprint (OS-aware)
    dhcp_fp = get_dhcp_fingerprint(os_str, vendor, name)

    # Unique device ID
    device_id = make_device_id(name, d["ip"], counter)

    # Rich description: top CVEs + APT groups
    top_cves = sorted(d["cves"], key=lambda c: (-c["cvss"], SEVERITY_ORDER.get(c["severity"], 4)))[:5]
    cve_str = ", ".join(
        f"{c['cve']} (CVSS {c['cvss']:.1f} {c['severity']})" + (f" [{c['ics_cert']}]" if c['ics_cert'] else "")
        for c in top_cves
    )
    apt_str = ", ".join(d["apt_groups"][:8]) if d["apt_groups"] else ""

    desc_parts = [
        f"OS: {os_str}" if os_str else None,
        f"Risk: {d['risk_level']} ({d['risk_score']}/100)" if d["risk_level"] else None,
        f"CVEs: {d['cve_count']} total — {d['critical_count']} critical / {d['high_count']} high | Max CVSS: {d['max_cvss']:.1f}",
        f"Top CVEs: {cve_str}" if cve_str else None,
        f"APT Groups ({d['apt_count']}): {apt_str}" if apt_str else None,
        f"Site: {d['site_name']}" if d["site_name"] else None,
        "⚠️ ICS-CERT alert" if d["has_ics"] else None,
        f"Danger Score: {d['danger_score']}",
    ]
    description = " | ".join(p for p in desc_parts if p)

    device = {
        "id":               device_id,
        "name":             name,
        "vendor":           vendor,
        "type":             device_type,
        "mac":              mac,
        "protocols":        sorted(set(protocols)),
        "enabled":          True,
        "traffic_interval": random.randint(60, 240),
        "description":      description,
        "fingerprint":      {"dhcp": dhcp_fp},
        # Metadata preserved for reference (not used by emulator but visible in UI)
        "_vuln_meta": {
            "ip":            d["ip"],
            "os":            os_str,
            "risk_score":    d["risk_score"],
            "risk_level":    d["risk_level"],
            "danger_score":  d["danger_score"],
            "cve_count":     d["cve_count"],
            "critical_cves": d["critical_count"],
            "high_cves":     d["high_count"],
            "max_cvss":      d["max_cvss"],
            "apt_groups":    d["apt_groups"],
            "has_ics_cert":  d["has_ics"],
            "top_cves":      [c["cve"] for c in top_cves],
            "site":          d["site_name"],
        }
    }

    # MQTT topic if applicable
    if "mqtt" in protocols:
        slug = re.sub(r"[^a-z0-9]", "_", device_type.lower())
        device["mqtt_topic"] = f"iot/{slug}/{device_id}"

    # Bad behavior decision
    # Trigger if: any Critical/High CVE present, or ICS-CERT, or APT groups linked
    has_high_threat = (
        d["critical_count"] > 0
        or d["high_count"] > 0
        or d["has_ics"]
        or d["apt_count"] > 0
    )

    is_bad = False
    if security_percentage is not None:
        is_bad = random.randint(1, 100) <= security_percentage
    elif enable_security:
        is_bad = True
    elif has_high_threat:
        is_bad = True

    if is_bad:
        # Choose behaviors based on threat profile
        behaviors = []
        if d["apt_count"] > 0:
            behaviors.append("beacon")    # APT linked = C2 beacon is realistic
        if d["has_ics"]:
            behaviors.append("port_scan") # ICS = lateral movement / scan
        if d["critical_count"] > 0 or d["high_count"] > 0:
            behaviors.append("pan_test_domains")  # Known-bad domains for guaranteed PAN detection
        if not behaviors:
            behaviors = ["random"]
        device["security"] = {
            "bad_behavior":  True,
            "behavior_type": behaviors,
        }

    return device


# ─── Main conversion ──────────────────────────────────────────────────────────

def convert(
    input_path: str,
    output_path: str,
    max_devices: int | None = None,
    only_iot: bool = False,
    enable_security: bool = False,
    security_percentage: int | None = None,
    merge: bool = False,
):
    with open(input_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"📂 Read {len(rows)} vulnerability rows from CSV")

    # Optional IoT filter
    if only_iot:
        before = len(rows)
        rows = [r for r in rows if is_iot_vertical(safe(r, "Profile Vertical"))]
        print(f"🔍 IoT-only filter: {before} → {len(rows)} rows")

    # Aggregate by device
    aggregated = aggregate_devices(rows)
    print(f"📱 Aggregated into {len(aggregated)} unique devices")

    # Apply top-N limit (already sorted by danger_score desc)
    if max_devices is not None:
        aggregated = aggregated[:max_devices]
        print(f"🔢 Limited to top {max_devices} most dangerous devices")

    # Build Stigix devices
    devices = []
    name_counters: dict[str, int] = {}  # base_name → count, for MAC-name dedup
    for i, d in enumerate(aggregated, 1):
        device = build_stigix_device(d, i, enable_security, security_percentage, name_counters)
        devices.append(device)


    # Handle merge vs replace
    if merge and Path(output_path).exists():
        with open(output_path, encoding="utf-8") as f:
            existing = json.load(f)
        existing_devices = existing.get("devices", [])
        existing_ids = {d["id"] for d in existing_devices}
        new_devices = [d for d in devices if d["id"] not in existing_ids]
        devices = existing_devices + new_devices
        print(f"🔄 Merge: {len(existing_devices)} existing + {len(new_devices)} new = {len(devices)} total")

    output = {"devices": devices}

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    bad_count = sum(1 for d in devices if d.get("security", {}).get("bad_behavior"))
    ics_count = sum(1 for d in aggregated if d.get("has_ics"))

    print(f"✅ Exported {len(devices)} devices → {output_path}")
    print(f"   💀 Bad-behavior devices: {bad_count}")
    print(f"   ⚠️  ICS-CERT devices:     {ics_count}")
    if aggregated:
        print(f"   📊 Top danger score: {aggregated[0]['danger_score']} ({aggregated[0]['name']})")
    return devices


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Convert Palo Alto IoT Security Vulnerability CSV to Stigix IoT emulator JSON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Column mapping (CSV → aggregated device):
  Device Name, IP Address, MAC Address  → device identity
  Risk Score, Risk Level                → base threat level
  Profile, Profile Vertical             → type / IoT classification
  Vendor, Model, OS                     → fingerprinting
  CVE, CVSS, Severity, ICS-Cert         → vulnerability details (per row)
  APT Names                             → threat actor attribution

Danger Score formula (per device):
  Risk Score + (Critical×15) + (High×8) + (Medium×3)
  + (Unique APT groups × 5) + (ICS-CERT × 10) + (Max CVSS × 2)

Examples:
  python import_vuln_csv.py -i vulns.csv -o devices.json
  python import_vuln_csv.py -i vulns.csv -o devices.json --max-devices 30
  python import_vuln_csv.py -i vulns.csv -o devices.json --max-devices 50 --only-iot
  python import_vuln_csv.py -i vulns.csv -o devices.json --security-percentage 80
  python import_vuln_csv.py -i vulns.csv -o devices.json --enable-security
        """,
    )
    parser.add_argument("-i", "--input",  required=True, help="Vulnerability CSV file (one row per CVE)")
    parser.add_argument("-o", "--output", required=True, help="Output Stigix JSON file")
    parser.add_argument("--max-devices", type=int, default=None,
                        help="Max devices to export, selected by danger score (default: all)")
    parser.add_argument("--only-iot", action="store_true",
                        help="Only include devices with Generic IoT / Industrial / Medical Profile Vertical")
    parser.add_argument("--enable-security", action="store_true",
                        help="Enable bad behavior for ALL exported devices")
    parser.add_argument("--security-percentage", type=int, default=None,
                        help="Enable bad behavior for N%% of devices (0–100)")
    parser.add_argument("--merge", action="store_true",
                        help="Merge with existing output file instead of replacing it")
    args = parser.parse_args()

    if not Path(args.input).exists():
        print(f"❌ File not found: {args.input}")
        sys.exit(1)

    convert(
        input_path=args.input,
        output_path=args.output,
        max_devices=args.max_devices,
        only_iot=args.only_iot,
        enable_security=args.enable_security,
        security_percentage=args.security_percentage,
        merge=args.merge,
    )


if __name__ == "__main__":
    main()
