---
name: stigix-secret-guard
description: >
  Pre-push security checklist to prevent leaking Palo Alto SASE credentials
  and other secrets into the Stigix GitHub repository.
  Use this skill BEFORE any git commit or push, and whenever modifying files
  that could contain credentials (.env, credentials.json, *.old, *.bak, etc.)
---

# Stigix Secret Guard Skill

Use this skill **before every `git commit` or `git push`** that touches configuration files,
environment files, or any file outside of `src/`, `mcp-server/src/`, or `web-dashboard/src/`.

---

## ⚠️ Known Leak Patterns for Stigix

The following patterns indicate **real Palo Alto SASE credentials** and must NEVER be committed:

### Pattern 1 — Palo Alto Service Account ID
```
*@*.iam.panserviceaccount.com
```
Example: `PrismaSASE@1927975026.iam.panserviceaccount.com`

### Pattern 2 — Palo Alto Client Secret (UUID format)
```
PRISMA_SDWAN_CLIENT_SECRET="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```
A UUID-format value next to any of: `CLIENT_SECRET`, `client_secret`, `PRISMA_SDWAN_CLIENT_SECRET`

### Pattern 3 — TSG ID (numeric Prisma tenant ID)
```
PRISMA_SDWAN_TSGID=<10-digit number>
```
Example: `PRISMA_SDWAN_TSGID=1927975026`

### Pattern 4 — credentials.json / .old files with real values
Any `credentials.json`, `credentials.json.old`, `.env`, `.env.*` containing real values instead of placeholders.

---

## Step 1 — Pre-Commit Scan

Before `git add` or `git commit`, run:

```bash
# Scan staged files for Palo Alto credentials
git diff --cached | grep -E "panserviceaccount\.com|PRISMA_SDWAN_CLIENT_SECRET=\\\".{10,}\\\"|PRISMA_SDWAN_TSGID=[0-9]{7,}"

# Scan entire working tree (catch untracked files too)
grep -r --include="*.json" --include="*.env" --include="*.old" --include="*.bak" --include="*.md" \
  -E "panserviceaccount\.com|[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}" \
  . 2>/dev/null | grep -v ".gitignore\|node_modules\|your-client\|placeholder\|example"
```

If any match → **STOP. Do not commit.**

---

## Step 2 — Verify .gitignore Coverage

The following patterns MUST be in `.gitignore`:

```gitignore
# Credentials
credentials.json
**/credentials.json
secrets.json
**/secrets.json
*.pem
*.key

# Environment files
.env
.env.*
.env.local
.env.prod
.env.production

# Roadmap / notes (may contain real values)
Roadmap/
roadmap/
```

Check with:
```bash
git check-ignore -v engines/credentials.json
git check-ignore -v web-dashboard/.env
```
Both must return a match. If not → add to `.gitignore` immediately.

---

## Step 3 — Check Tracked Files

```bash
# List all tracked files that could contain secrets
git ls-files | grep -E "\.env|credentials|\.old|\.bak|secrets"
```

Any match → inspect the file content and remove if it contains real values:
```bash
git rm --cached <file>   # Remove from tracking (keeps local copy)
git commit -m "chore: remove sensitive file from tracking"
```

---

## Step 4 — Scan Git History (if leak suspected)

```bash
# Search entire git history for the secret
git log --all --full-history -S "panserviceaccount.com" --oneline
git log --all --full-history -S "CLIENT_SECRET" --oneline
```

If any commit found → the secret is in the public history. You MUST:
1. **Immediately revoke** the service account on [apps.paloaltonetworks.com](https://apps.paloaltonetworks.com)
2. Create a new service account with a new secret
3. Consider rewriting git history with `git filter-repo` (advanced — only if repo is private or just before going public)

---

## Step 5 — Revocation Procedure (if leaked)

1. Go to **[apps.paloaltonetworks.com](https://apps.paloaltonetworks.com)**
2. Navigate to **Identity & Access → Service Accounts**
3. Find the account matching the leaked `client_id` (e.g., `PrismaSASE@<TSGID>.iam.panserviceaccount.com`)
4. **Delete or rotate the client secret** — this immediately invalidates any exposure
5. Create a new service account
6. Update only local files: `.env`, `credentials.json` (gitignored)

---

## Files That Are Safe vs. Dangerous

| File | Safe? | Rule |
|---|---|---|
| `engines/credentials.json` | ✅ Local only | Gitignored via `**/credentials.json` |
| `web-dashboard/.env` | ✅ Local only | Gitignored via `.env` |
| `Roadmap/*.md` | ✅ Local only | Gitignored via `Roadmap/` |
| `engines/credentials.json.old` | 🔴 **DANGER** | `.old` files NOT gitignored by default |
| `*.env.backup` | 🔴 **DANGER** | Backups may escape gitignore rules |
| `Scripts/getflow.py` | ✅ Safe | Contains only placeholders |
| `docs/*.md` | ✅ Safe | Contains only example values |
| `README.md` | ✅ Safe | Contains only `your-client-secret` |

> [!CAUTION]
> **`.old`, `.bak`, `.backup` files are the most common leak vector** — they often contain
> real values copied from active config files and are NOT always gitignored.
> Always check before committing files with these extensions.

---

## Quick Pre-Push Checklist

Before any `git push`:

- [ ] `git diff --cached | grep panserviceaccount` → returns nothing
- [ ] `git diff --cached | grep CLIENT_SECRET` → returns nothing or only `your-client-secret`
- [ ] `git ls-files | grep -E "\.old|\.bak|credentials"` → returns nothing sensitive  
- [ ] `.env` files are listed in `git check-ignore -v` output
- [ ] No `credentials.json.old` or similar backup files tracked
