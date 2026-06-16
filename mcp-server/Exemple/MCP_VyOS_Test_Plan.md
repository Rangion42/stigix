# 🧪 Stigix MCP — VyOS Test Plan

> **Goal**: Validate all VyOS MCP tools progressively, from read-only discovery  
> to impairments to destructive actions.
>
> **Version tested**: _(fill in: `docker exec stigix cat /app/VERSION`)_  
> **Date**: _(fill in)_  
> **Notation**: ✅ Pass | ❌ Fail | ⚠️ Partial

---

## 📖 How to Use

- Copy each prompt **exactly** as written into Claude Desktop.
- Mark each test ✅ / ❌ / ⚠️ in the Results table at the bottom.
- Sections build on each other — run them in order.
- Start a **fresh conversation** at the beginning of each session.

---

## 🗺️ Lab Reference Topology

```
Claude Desktop
     │
     └─ MCP Server (any Stigix node)
           │
           └─ Controller node  (e.g. BR8-Ubuntu or Raspi4-Ubuntu)
                  │
                  ├─ vyosrouter  ← underlay router — carries ALL branch WAN links
                  │     eth1 — BR1-MPLS-197      eth7 — BR2-INET-226
                  │     eth3 — BR1-INET-227      eth8 — BR2-MPLS-196
                  │     eth10 — DC1-INET-221     eth11 — DC1-MPLS-191
                  │
                  ├─ vyoslandc1  ← DC1 LAN router
                  └─ vyoslandc2new ← DC2 LAN router

Branch Stigix nodes (BR1-Ubuntu, BR2-Ubuntu…) each manage their OWN local VyOS router.
Those local routers do NOT carry WAN/underlay interfaces for other sites.
→ "BR1 internet" = eth3 on vyosrouter (controller), NOT BR1-Ubuntu's local router.
```

---

## SECTION A — Pre-flight: Discovery

> **Goal**: Confirm Claude can list endpoints and find VyOS routers.  
> All read-only. Safe to run anytime.

### A1 — List all Stigix nodes

```
Show me all available Stigix endpoints.
```

Expected: list of nodes with IDs (BR8-Ubuntu, Raspi4-Ubuntu, BR1-Ubuntu, etc.).

| Result | Notes |
|--------|-------|
| ⬜ | |

---

### A2 — Find the VyOS controller

```
Which Stigix node manages the most VyOS routers?
```

Expected: Claude calls `list_vyos_routers()` on multiple nodes and compares.  
One node should return 3+ routers (vyosrouter, vyoslandc1, vyoslandc2new) — that is the controller.

| Result | Notes |
|--------|-------|
| ⬜ | |

---

### A3 — List all VyOS interfaces (controller node)

Use the controller node found in A2. Example with BR8:

```
List all VyOS interfaces managed by BR8.
```

Expected: interfaces grouped by router, with description, IP, and up/down status.  
`vyosrouter` should show BR1-MPLS-*, BR1-INET-*, BR2-*, DC1-*, etc.

| Result | Notes |
|--------|-------|
| ⬜ | |

---

## SECTION B — Controller Discovery (Behavior Validation)

> **Goal**: Validate that Claude no longer picks a hardcoded Stigix node.  
> It must discover or ask for the correct controller when none is established.

### B1 — Cold start: Claude must NOT assume a node

Start a **new conversation**, then:

```
List the VyOS interfaces available for chaos engineering.
```

**Expected** ✅ Claude calls `list_endpoints()` first, OR asks which node to use.  
**Bad behavior** ❌ Claude immediately calls `get_vyos_interfaces("Raspi4-Ubuntu")` without asking.

| Result | Notes |
|--------|-------|
| ⬜ | |

---

### B2 — Site name given, NOT a Stigix node

```
Add 5% packet loss on the internet link of BR1.
```

**Expected** ✅
1. Claude does NOT call `get_vyos_interfaces("BR1-Ubuntu")` — branch node ≠ controller.
2. It discovers that `BR1-INET-*` is on `vyosrouter` via the **controller node**.
3. Proposes the correct interface and waits for confirmation.

**Bad behavior** ❌ Claude uses BR1-Ubuntu, finds only `VyosBranch206`, gets confused.

| Result | Notes |
|--------|-------|
| ⬜ | |

---

### B3 — Controller set by user → Claude remembers it

**Step 1:**
```
I want to use BR8 as the VyOS controller. List all VyOS interfaces.
```
Expected: Claude uses BR8 directly without asking again.

| Result | Notes |
|--------|-------|
| ⬜ | |

**Step 2 (same conversation):**
```
Now add 100ms of latency on the MPLS link of BR2.
```
Expected: Claude reuses BR8 — does NOT re-ask. Finds `BR2-MPLS-*`, proposes it.

| Result | Notes |
|--------|-------|
| ⬜ | |

---

## SECTION C — Read-Only State Inspection

> **Goal**: Inspect router state without making any changes.  
> Safe to run at any time.

### C1 — Live router state

```
What is the current state of vyosrouter on BR8?
```

Expected: per-interface admin status (🟢/🔴), active QoS (delay/loss/rate if any), IP blocks.

| Result | Notes |
|--------|-------|
| ⬜ | |

---

### C2 — VyOS change history

```
Show the last 10 VyOS actions applied via BR8.
```

Expected: chronological list of actions with router, command, interface, and status.

| Result | Notes |
|--------|-------|
| ⬜ | |

---

### C3 — Available scenarios

```
What VyOS scenarios are available on BR8?
```

Expected: list of configured sequences (failover, flapping, etc.) with enabled status.

| Result | Notes |
|--------|-------|
| ⬜ | |

---

## SECTION D — Simple Impairments (Reversible)

> **Goal**: Apply and remove basic network impairments.  
> Each test includes a cleanup step — run it before moving on.

### D1 — Latency (BR1 internet)

**Apply:**
```
Add 100ms latency on the BR1 internet link
```

**Verify (optional):**
```
What is the current state of vyosrouter on BR8?
```
Expected: eth3 (BR1-INET-227) shows `qos_active: delay_ms=100`.

**Clean up:**
```
Clear all QoS on the BR1 internet interface
```

| Result | Notes |
|--------|-------|
| ⬜ | |

---

### D2 — Packet loss (BR1 internet)

**Apply:**
```
Add 5% packet loss on the BR1 internet link
```

**Clean up:**
```
Remove QoS impairments on the BR1 internet interface
```

| Result | Notes |
|--------|-------|
| ⬜ | |

---

### D3 — Rate limiting (BR1 internet)

**Apply:**
```
Limit the BR1 internet link bandwidth to 10 Mbps
```

**Clean up:**
```
Remove the bandwidth limit on the BR1 internet interface
```

| Result | Notes |
|--------|-------|
| ⬜ | |

---

## SECTION E — Combined & Advanced Impairments

> **Goal**: Test multi-parameter actions and IP-level blocking.

### E1 — Latency + loss in one call (BR1 internet)

**Apply:**
```
Apply 150ms latency and 3% packet loss simultaneously on the BR1 internet link
```
> Claude must pass both parameters in a **single** `set-impairment` call — not two calls.

**Clean up:**
```
Clear QoS on the BR1 internet interface
```

| Result | Notes |
|--------|-------|
| ⬜ | |

---

### E2 — IP block / unblock (DC1)

**Block:**
```
Block IP address 1.2.3.4 on the DC1 router
```

**Verify:**
```
Show currently blocked IPs on the DC1 router
```

**Unblock:**
```
Unblock IP 1.2.3.4 on the DC1 router
```

| Result | Notes |
|--------|-------|
| ⬜ | |

---

### E3 — Multi-block + clear all (DC1)

**Apply:**
```
Block IP 10.99.0.1 on the DC1 router
```
```
Block IP 10.99.0.2 on the DC1 router
```

**Verify:**
```
List all blocked IPs on the DC1 router
```
Expected: both 10.99.0.1 and 10.99.0.2.

**Clear:**
```
Clear all IP blocks on the DC1 router
```

| Result | Notes |
|--------|-------|
| ⬜ | |

---

### E4 — Ambiguous intent: multiple interface matches

```
Add latency on the internet link via BR8.
```

Expected: multiple interfaces match "internet" (BR1-INET, BR2-INET, DC1-INET…).  
Claude **lists all candidates** and asks the user to choose — does NOT pick arbitrarily.

| Result | Notes |
|--------|-------|
| ⬜ | |

---

## SECTION F — Destructive Actions

> ⚠️ **High impact** — these take interfaces offline.  
> Always confirm the cleanup step ran successfully before moving on.

### F1 — Interface shutdown + restore (BR1 MPLS)

> Using MPLS (less critical than internet for this test).

**Apply:**
```
Shut down the BR1 MPLS interface
```
Expected: Claude asks for confirmation. Say **yes**.

**Verify:**
```
What is the current state of vyosrouter on BR8?
```
Expected: eth1 (BR1-MPLS-197) shows 🔴 down.

**Restore:**
```
Bring the BR1 MPLS interface back up
```

| Result | Notes |
|--------|-------|
| ⬜ | |

---

### F2 — Confirmation guard: no action without explicit yes

```
Shut down the BR2 MPLS interface
```

Expected: Claude presents the action and **stops waiting**.  
It does NOT call `vyos_execute_action` without your answer.

Reply **no** — Claude must cancel gracefully.

| Result | Notes |
|--------|-------|
| ⬜ | |

---

## SECTION G — Bulk Reset

> **Goal**: Validate bulk cleanup tools after running impairment tests.  
> Run this after Section D/E/F to clean up everything at once.

### G1 — Inspect state before reset

```
What is the current state of vyosrouter on BR8?
```

Expected: Claude shows all active QoS, IP blocks, and admin-down interfaces.

| Result | Notes |
|--------|-------|
| ⬜ | |

---

### G2 — Full reset

```
Do a full reset of vyosrouter on BR8 — clear all QoS, IP blocks, and re-enable any down interfaces.
```

Expected:
1. Claude summarises the reset plan (what will be cleared)
2. Asks for confirmation
3. On yes → `vyos_bulk_reset(scope="full-reset")`
4. Reports each action taken

| Result | Notes |
|--------|-------|
| ⬜ | |

---

### G3 — Verify clean state

```
What is the current state of vyosrouter on BR8?
```

Expected: all interfaces 🟢 up, no active QoS, no IP blocks.

| Result | Notes |
|--------|-------|
| ⬜ | |

---

## SECTION H — Final Audit

### H1 — History of this test session

```
Show the last 20 VyOS actions with their status
```

Expected: all actions from this session visible with `status=success` and `cli_equivalent`.

| Result | Notes |
|--------|-------|
| ⬜ | |

---

### H2 — Failure check

```
Were there any failed VyOS actions in the history?
```

Expected: no failures (or a clear explanation if any).

| Result | Notes |
|--------|-------|
| ⬜ | |

---

## 📊 Results Summary

| Section | Test | Description | Result |
|---------|------|-------------|--------|
| A | A1 | List all Stigix endpoints | ⬜ |
| A | A2 | Find VyOS controller node | ⬜ |
| A | A3 | List VyOS interfaces | ⬜ |
| B | B1 | Cold start — no hardcoded node | ⬜ |
| B | B2 | Site name → correct controller, not branch node | ⬜ |
| B | B3a | User sets controller → Claude uses it | ⬜ |
| B | B3b | Same session → Claude remembers controller | ⬜ |
| C | C1 | Live router state inspection | ⬜ |
| C | C2 | VyOS change history | ⬜ |
| C | C3 | Available scenarios | ⬜ |
| D | D1 | Latency 100ms + cleanup | ⬜ |
| D | D2 | Packet loss 5% + cleanup | ⬜ |
| D | D3 | Rate limit 10 Mbps + cleanup | ⬜ |
| E | E1 | Combined latency + loss (single call) | ⬜ |
| E | E2 | IP block / unblock | ⬜ |
| E | E3 | Multi-block + clear all | ⬜ |
| E | E4 | Ambiguous intent → lists candidates | ⬜ |
| F | F1 | Shutdown + restore BR1 MPLS | ⬜ |
| F | F2 | Confirmation guard → reply no → cancelled | ⬜ |
| G | G1 | Inspect state before reset | ⬜ |
| G | G2 | Full reset (bulk) | ⬜ |
| G | G3 | Verify clean state after reset | ⬜ |
| H | H1 | History audit | ⬜ |
| H | H2 | Failure check | ⬜ |

---

## 🔍 Debug Tips

```
Can you show me exactly which MCP tool you called and what arguments you passed?
```

```
Why did you choose that specific Stigix node as the VyOS controller?
```

```
Show me the raw JSON response you received from list_vyos_routers.
```

```bash
# MCP server logs on the Stigix node
docker logs stigix-mcp-server --tail 50
docker exec stigix cat /app/logs/mcp-history.jsonl | tail -20
```

---

*Supersedes: `MCP_VyOS_Test_Exhaustif.md` and `VyOS_Controller_Discovery_Test.md`*
