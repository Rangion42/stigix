# MCP Claude Desktop — Test Results BR8-Ubuntu
*Session: 29/05/2026 — Stigix MCP Server v1.4.0-patch.104*

---

## Endpoints Stigix (10 nœuds)

| Site Name | IP / Host | Capacités | Source | Vu récemment |
|---|---|---|---|---|
| Hetzner | 142.132.193.157 | voice, convergence, xfr, security, connectivity | managed | — |
| DC1 | 192.168.203.100 | voice, convergence, xfr, security, connectivity | managed | ✅ |
| target.stigix.io | target.stigix.io | security uniquement | managed | — |
| Mac-mini-de-jsuzanne-2 | 192.168.97.2 | voice, convergence, xfr, security, connectivity | managed | ✅ |
| DC7-Ubuntu | 192.168.205.10 | voice, convergence, xfr, security, connectivity | synthesized | ✅ |
| Raspi4-Ubuntu | 192.168.1.120 | voice, convergence, xfr, security, connectivity | synthesized | ✅ |
| BR2-Ubuntu | 192.168.206.10 | voice, convergence, xfr, security, connectivity | synthesized | ✅ |
| BR1-Ubuntu | 192.168.207.10 | voice, convergence, xfr, security, connectivity | synthesized | ✅ |
| ubuntubr5 | 192.168.217.5 | voice, convergence, xfr, security, connectivity | synthesized | ✅ |
| BR8-Ubuntu | 192.168.219.1 | voice, convergence, xfr, security, connectivity | synthesized | ✅ |

---

## Statut BR8-Ubuntu — READY ✅

| Catégorie | Détail |
|---|---|
| IP locale | 192.168.219.1 |
| Version | v1.4.0-patch.104 |
| Uptime | 300 secondes |
| Plateforme | Linux |
| Rôle | SPOKE |
| Mémoire | 27% (1.1 Go / 4.1 Go) |
| Disque | 50% (15.8 Go / 31.5 Go) |
| Trafic | ✅ En cours (1 client, interval 0.1s) |
| curl | ✅ /usr/bin/curl |
| python-scapy | ✅ v2.5.0 |
| DNS | ✅ nslookup |

---

## Traffic Stats BR8

- **Total requêtes** : 170
- **Applications simulées** : 55
- **Total erreurs** : 46
- **Client actif** : client-01-298

### Top apps (0 erreurs)
googleapis.com (10), outlook.office365.com (10), dropbox.com (9), sharepoint.com (9), login.microsoftonline.com (9), box.com (7)

### Apps en erreur 100%
onmicrosoft.com, microsoftonline-p.com, microsoftonline-p.net, lync.com, microsoftonline.net, googlevideo.com, ytimg.com, vimeo.com, youtube.com, spotify.com, netflix.com, boxcdn.net...

> **Note**: Backoff niveau 3 actif sur microsoftonline-p.net/com, googlevideo.com, ytimg.com — probablement bloqués par la politique NGFW du site.

---

## DEM Probes (55 probes)

- **Manuelles SaaS** : 10 (Cloudflare, Google, PayFit, Aircall, Salesforce, stigix.io...)
- **Cloud Stigix** : 8 (Info/Egress, Slow SaaS, Large Download, Flap, Wave, Random...)
- **Infra interne** : 8 (Hetzner ping, DC1 HTTP/UDP, MacMini...)
- **Discovery auto** : 29 dont 8 stale (BR4, BR_DANONE, Lyon, DC3-AWS-US, DC4-AZURE-FR, DC5-AZURE-UK...)

---

## Fabric Targets (10 targets)

- **Actives** : 8 (Hetzner, DC1, DC7, Raspi4, BR2, BR1, ubuntubr5, BR8)
- **Désactivées** : 2 (target.stigix.io, Mac-mini-de-jsuzanne-2)
- **Managed** : 3 | **Synthesized** : 7

---

## Apps simulées (17 catégories)

| Catégorie | Poids |
|---|---|
| Microsoft 365 Suite | 35 |
| Google Workspace | 35 |
| Cloud Storage (box, dropbox, icloud...) | 22 |
| Project Management (jira) | 22 |
| Communication (slack, webex, skype...) | 7 |
| Autres (CRM, DevOps, Finance, HR, BI...) | 7 |

---

## Security Score BR8 (2 840 tests, ~18h)

| Statut | Nombre | % |
|---|---|---|
| Bloqué | 775 | 27,3% |
| Sinkholed | 551 | 19,4% |
| Autorisé | 1 480 | 52,1% |
| Erreur | 0 | 0% |

**Taux de blocage effectif : ~46,7%**

| Type | Tests |
|---|---|
| URL Filtering | 2 032 |
| DNS Security | 696 |
| Threat Prevention | 112 |

---

## Convergence History (10 tests)

| Test ID | Cible | Verdict | RTT moy. | Blackout max |
|---|---|---|---|---|
| CONV-0127 | Raspi4-Ubuntu | 🟡 GOOD | 241 ms | 730 ms |
| CONV-0126 | Hetzner | 🟢 PERFECT | 49 ms | 0 ms |
| CONV-0125 | Hetzner | 🟢 PERFECT | 49 ms | 0 ms |
| CONV-0124 | Raspi4-Ubuntu | 🟡 GOOD | 203 ms | 117 ms |
| CONV-0122→0119 | Hetzner/DC1 | 🟢 PERFECT | 13–33 ms | 0 ms |

---

## Last 10 Security Results (DNS batch sched-dns-1780072118432)

| # | Test | Statut |
|---|---|---|
| 2840 | DNS Misconfiguration (Claimable) | 🔵 resolved |
| 2839 | Subdomain Reputation | 🟣 sinkholed |
| 2838 | Cybersquatting | 🟣 sinkholed |
| 2837 | Stockpile | 🟣 sinkholed |
| 2836 | Ransomware | 🟢 blocked |
| 2835 | CNAME Cloaking | 🟣 sinkholed |
| 2834 | Ad Tracking | 🟣 sinkholed |
| 2833 | Compromised DNS | 🟢 blocked |
| 2832 | Strategically-Aged | 🟣 sinkholed |
| 2831 | Wildcard Abuse | 🟣 sinkholed |

**9/10 menaces neutralisées** (blocked + sinkholed)

---

## Full Security Audit — Résultats globaux

| Phase | Score |
|---|---|
| URL Filtering | 20/70 bloqués (28,6%) |
| DNS Security | 23/24 neutralisés (95,8%) |
| Threat Prevention EICAR | ❌ Erreur 400 — corrigé en patch.105 |

### URL Filtering — Catégories bloquées (20)
Adult Content, Dynamic DNS, Extremism, Gambling, Games, Government, Hacking, Insufficient Content, Job Search, Malware, Phishing, Sex Education, Social Networking, Streaming Media, Unknown, Weapons, C2, Malware RT, Phishing RT, Grayware RT

### URL Filtering — Catégories autorisées notables (48)
Nudity, Peer-to-Peer, Cryptocurrency, Dating, Copyright Infringement, **Proxy Avoidance**, **Newly Registered Domains**

---

## Bugs identifiés et corrections

| Bug | Trouvé en | Corrigé en |
|---|---|---|
| EICAR 400 Bad Request (`endpoints` → `endpoint`) | patch.104 | ✅ patch.105 |
| `_fetch_node_snapshot` double appel `r.json()` | patch.102 | ✅ patch.103 |
| `generate_report` `__import__('datetime')` | patch.102 | ✅ patch.103 |
| `run_eicar_test` dict guard non-dict response | patch.102 | ✅ patch.103 |
| `stigix-upgrader` reste après upgrade | patch.104 | ✅ patch.104 |
