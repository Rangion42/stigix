---
name: stigix-doc-update
description: >
  Evaluate whether a new feature or change warrants a documentation update in the Stigix docs.
  Use after adding new features (not bug fixes). Decides which docs to update, writes the
  content, and proposes the update to the user when the value is uncertain.
---

# Stigix Doc Update Skill

Use this skill **after implementing new features** to evaluate whether documentation should
be updated, and to perform the update if it adds real value for users.

## When to Use

- After adding **new user-facing features** (new MCP tools, new CLI commands, new UI capabilities)
- After adding **new configuration options** that users need to set up (e.g., interface descriptions for VyOS MCP)
- After changing **user-facing behavior** (new parameters, changed defaults, new workflows)
- **NOT** for bug fixes, refactors, or internal implementation changes

## When NOT to Update Docs

Skip documentation updates for:
- Bug fixes (unless the fix changes user-visible behavior significantly)
- Internal refactors with no user-facing impact
- Performance improvements with no usage change
- Dependency bumps

---

## Step 1 — Evaluate If Documentation Is Warranted

Ask yourself these questions:

| Question | Update needed? |
|---|---|
| Does the feature introduce a **new workflow** a user would follow? | ✅ Yes |
| Does it require **user configuration** (e.g., VyOS interface descriptions)? | ✅ Yes |
| Does it expose a **new MCP tool** or **new CLI command**? | ✅ Yes |
| Does it add a **new concept** (e.g., "ad-hoc actions", "natural language control")? | ✅ Yes |
| Is it a **bug fix** with no changed behavior? | ❌ No |
| Is it purely **internal** (refactor, cleanup, test)? | ❌ No |
| Is it **already well-documented** in docstrings/inline comments? | ⚠️ Maybe — propose to user |

> [!TIP]
> When in doubt, **propose** to the user rather than silently skipping or silently writing docs.
> Say: *"This feature adds [X]. Would you like me to update [doc file] with a usage example?"*

---

## Step 2 — Identify Which Docs to Update

### Stigix Documentation Map

| What changed | Primary doc | Secondary doc |
|---|---|---|
| New MCP tool(s) | `docs/MCP_SERVER.md` | `mcp-server/Exemple/MCP_Test_Plan.md` |
| New CLI command | `docs/STIGIX_CLI.md` | — |
| New VyOS feature / config | `docs/VYOS_CONTROL.md` | `docs/MCP_SERVER.md` (if MCP exposed) |
| New security test type | `docs/SECURITY_TESTING.md` | — |
| New traffic / DEM feature | `docs/TRAFFIC_FLOW_GUIDE.md` | — |
| New install / deploy step | `README.md` | Install scripts inline comments |
| New use case scenario | `docs/stigix_usecase.md` | — |
| New MCP tool (batch test) | `mcp-server/Exemple/MCP_Test_Plan.md` | — |

### Checklist for MCP tools

When a new `@mcp.tool()` is added, always update **all three**:
- [ ] `docs/MCP_SERVER.md` — add row to the relevant tool table + example prompt
- [ ] `docs/MCP_SERVER.md` — add a "Usage Example" section if the workflow is non-obvious
- [ ] `mcp-server/Exemple/MCP_Test_Plan.md` — add row in the results grid (⬜ = untested)

---

## Step 3 — Write the Documentation

### For `docs/MCP_SERVER.md`

**Tool table row format:**
```markdown
| `tool_name` | One-line description of what it does | *"Natural language example prompt"* |
```

**Usage Example format:**
```markdown
### N. Feature Name
**User:** *"Natural language request"*
```
get_tool_name("agent_id")
→ What it returns / what it does
→ Follow-up tool call if needed
```
```

**Tip/Important box** — add when:
- The tool requires a prerequisite step (e.g., `get_vyos_interfaces` before `vyos_execute_action`)
- There's a configuration requirement (e.g., interface descriptions must exist)
- The tool has a non-obvious limitation

### For `docs/VYOS_CONTROL.md`

Add sections under the relevant area. Follow the existing structure:
- New capability → add under `## 🚀 Core Features`
- New workflow → add under `## 🛠️ Operational Workflow`
- Configuration requirement → add a new `## 🤖 [Feature Name]` section at the bottom

### For `mcp-server/Exemple/MCP_Test_Plan.md`

Add new tools to the results grid with `⬜` (untested) status:
```markdown
| N | `tool_name` | ⬜ | | Description of what to test |
```

Also add the tool to the appropriate Phase section with a ready-to-use test prompt.

---

## Step 4 — Review Before Committing

Before committing the doc changes:

- [ ] Does the example actually work? (No hallucinated parameters)
- [ ] Is the tool name exactly right? (Match `server.py` `@mcp.tool()` function name)
- [ ] Are parameter names accurate? (Match the function signature)
- [ ] Is the tone consistent with the existing docs? (Practical, example-driven)
- [ ] No duplicate content? (Don't repeat what's in the code docstring verbatim)

---

## Step 5 — Commit (Doc-only rules)

Doc-only changes **do NOT** require a version bump or git tag.

```bash
git add docs/<updated_file>.md
git add mcp-server/Exemple/<updated_file>.md   # if applicable
git commit -m "docs: <short description of what was documented>

- Updated docs/MCP_SERVER.md: added <tool_name> to tools table + usage example
- Updated docs/VYOS_CONTROL.md: added <section name>
- Updated MCP_Test_Plan.md: added <N> new tools to results grid"
git push
```

> [!NOTE]
> No version bump. No git tag. Doc commits go directly to `main` without triggering CI.

---

## Proposing to the User

When the value of a doc update is uncertain, use this format to propose:

> "This feature adds [feature name]. I could update [doc file] to document [what would be added].
> This would be useful for [audience / use case].
> Want me to do it? (It won't trigger a rebuild — doc-only commit)"

Examples of when to **propose rather than auto-update**:
- The feature is experimental or not yet stable
- The feature is only useful for advanced users and might clutter the main docs
- The existing docs already cover a similar pattern well enough
- The feature adds many small tools that could overwhelm the table

---

## Quick Reference — Docs That Should Stay Up-to-Date

| Doc | Last known update | What it covers |
|---|---|---|
| `docs/MCP_SERVER.md` | patch.106 | All MCP tools, usage examples |
| `docs/VYOS_CONTROL.md` | patch.106 | VyOS sequences, interface naming |
| `docs/STIGIX_CLI.md` | patch.70 | CLI commands reference |
| `docs/SECURITY_TESTING.md` | — | Security test types and workflows |
| `mcp-server/Exemple/MCP_Test_Plan.md` | patch.105 | Test plan + results grid |
| `README.md` | patch.42 | Install guide, feature overview |
