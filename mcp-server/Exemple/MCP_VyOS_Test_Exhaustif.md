# MCP VyOS — Script de test exhaustif Claude Desktop
*Version patch.111+*

---

## Topologie (pour info — ne pas mentionner dans les prompts)

```
Claude Desktop → stigix-br8 (MCP) → Stigix BR8-Ubuntu
                                          │
                                          ├─ vyosrouter  → Router VyOS → BR1
                                          │     eth1 — BR1-MPLS-197
                                          │     eth3 — BR1-INET-227
                                          │
                                          └─ vyoslandc1  → Router VyOS → DC1
```

> ⚠️ **Ne pas dire "On BR8" dans les prompts** — Claude confond avec le nœud Stigix.
> L'intégration `stigix-br8` est implicite. Référencer les interfaces par leur description
> (`BR1 internet`, `BR1 MPLS`, `DC1`) et laisser Claude résoudre via `get_vyos_interfaces`.

---

## Prérequis — Découverte

```
What are the VyOS routers and their interfaces?
```
> ✅ Attendu : `vyosrouter` avec `eth1 (BR1-MPLS-197)` et `eth3 (BR1-INET-227)`.

---

## 🔵 TEST 1 — Latence simple (internet BR1)

**Appliquer**
```
Add 100ms latency on the BR1 internet link
```

**Nettoyer**
```
Clear all QoS on the BR1 internet interface
```

---

## 🔵 TEST 2 — Packet loss seul (internet BR1)

**Appliquer**
```
Add 5% packet loss on the BR1 internet link
```

**Nettoyer**
```
Remove QoS impairments on the BR1 internet interface
```

---

## 🔵 TEST 3 — Latence + loss combinés (internet BR1)

**Appliquer**
```
Apply 150ms latency and 3% packet loss simultaneously on the BR1 internet link
```
> Claude doit passer les deux paramètres dans un seul appel.

**Nettoyer**
```
Clear QoS on the BR1 internet interface
```

---

## 🔵 TEST 4 — Rate limiting (internet BR1)

**Appliquer**
```
Limit the BR1 internet link bandwidth to 10 Mbps
```

**Nettoyer**
```
Remove the bandwidth limit on the BR1 internet interface
```

---

## 🔵 TEST 5 — Shutdown / restore (MPLS BR1)

*On utilise le MPLS — moins impactant que l'internet pour un shutdown.*

**Appliquer**
```
Shut down the BR1 MPLS interface
```
> ⚠️ Action destructive — confirmer explicitement.

**Nettoyer**
```
Bring the BR1 MPLS interface back up
```

---

## 🔵 TEST 6 — Blocage IP (DC1)

**Appliquer**
```
Block IP address 1.2.3.4 on the DC1 router
```

**Vérifier**
```
Show currently blocked IPs on the DC1 router
```

**Nettoyer**
```
Unblock IP 1.2.3.4 on the DC1 router
```

---

## 🔵 TEST 7 — Multi-blocage + clear all (DC1)

**Appliquer**
```
Block IP 10.99.0.1 on the DC1 router
```
```
Block IP 10.99.0.2 on the DC1 router
```

**Vérifier**
```
List all blocked IPs on the DC1 router
```
> ✅ Attendu : 10.99.0.1 et 10.99.0.2.

**Nettoyer**
```
Clear all IP blocks on the DC1 router
```

---

## 🔵 TEST 8 — Audit history final

```
Show the last 10 VyOS actions with their status
```
> ✅ Toutes les actions du test avec `status=success` et `cli_equivalent`.

```
Were there any failed VyOS actions in the history?
```

---

## ✅ Checklist

| # | Test | VyOS Router | Interface | Action → Cleanup | ☐ |
|---|---|---|---|---|---|
| 1 | Latence 100ms | vyosrouter | eth3 / BR1-INET | set-impairment → clear-qos | ☐ |
| 2 | Loss 5% | vyosrouter | eth3 / BR1-INET | set-impairment → clear-qos | ☐ |
| 3 | Latence 150ms + Loss 3% | vyosrouter | eth3 / BR1-INET | set-impairment → clear-qos | ☐ |
| 4 | Rate limit 10 Mbps | vyosrouter | eth3 / BR1-INET | set-impairment → clear-qos | ☐ |
| 5 | Shutdown/restore | vyosrouter | eth1 / BR1-MPLS | interface-down → interface-up | ☐ |
| 6 | Block IP single | vyoslandc1 | — | deny-traffic → allow-traffic | ☐ |
| 7 | Multi-block + clear | vyoslandc1 | — | deny×2 → clear-all-blocks | ☐ |
| 8 | History audit | — | — | — | ☐ |
