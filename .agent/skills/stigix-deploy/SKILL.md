---
name: stigix-deploy
description: Bump version, commit code changes, and push a GitHub tag for the stigix project. Use whenever making code changes that should trigger a Docker image rebuild via GitHub Actions CI.
---

# Stigix Deploy Skill

Use this skill whenever you make **code changes** to the stigix project that should be shipped to Docker Hub via GitHub Actions.

## When to Use

- After any edit to `server.ts`, `*.tsx`, `Dockerfile`, `targets-manager.ts`, or other source files
- After changes to `engines/` scripts, `iot/`, `vyos/`, or `mcp-server/`
- **Skip** for doc-only changes (`docs/`, `README.md`, `CHANGELOG.md`, `*.md`) — those don't need a tag/rebuild

> [!IMPORTANT]
> **Dockerfile Audit**: If you added a NEW `.ts` file or a new directory in `web-dashboard/`, you MUST ensure it is explicitly copied in the `Runtime Stage` of the `web-dashboard/Dockerfile`. Otherwise, the container will fail with `ERR_MODULE_NOT_FOUND`.

## Steps

### 1 — Determine the new version

Read the current version:
```bash
cat /Users/jsuzanne/Github/stigix/VERSION
```
The format is `vX.Y.Z-patch.NNN`. You MUST strictly increment NNN by exactly +1 (e.g., from 140 to 141). Do not skip numbers or round to tens unless the USER explicitly requests it.

### 2 — Bump VERSION files and README badge

```bash
NEW_VER="v1.2.1-patch.NNN"   # replace NNN
echo "$NEW_VER" > VERSION
echo "$NEW_VER" > web-dashboard/VERSION
echo "$NEW_VER" > engines/VERSION
```

All three files must always stay in sync.

**Also update the Version badge in `README.md`** (usually around line 5) to match the new version:
```markdown
[![Version](https://img.shields.io/badge/Version-1.2.1--patch.NNN-blue.svg)](https://github.com/jsuzanne/stigix/releases)
```
*(Note the double dash `--` before `patch` in the shields.io URL format)*

### 2bis — Update CHANGELOG.md

> [!IMPORTANT]
> **Mandatory step** — `CHANGELOG.md` must be updated before every code commit. Never ship a patch without a changelog entry.

#### Step A — Audit for undocumented versions (ALWAYS run this first)

Before writing the new entry, run this command to compare git tags with CHANGELOG entries:

```bash
# List all v1.x tags
git tag | grep "^v" | sort -V

# List all documented versions in CHANGELOG
grep "^## \[v" CHANGELOG.md | head -20

# Find the gap: last documented version
grep "^## \[v" CHANGELOG.md | head -1
```

If `git tag` shows versions that do NOT appear in the CHANGELOG, you MUST add entries for ALL missing versions before proceeding. Use `git log --oneline` to reconstruct what changed:

```bash
# Get commits for a specific range (replace TAG_A and TAG_B)
git log --oneline TAG_A..TAG_B

# Or get the full history since v1.3.0 in chronological order
git log --oneline --reverse v1.3.0..HEAD
```

**Add one CHANGELOG entry per tagged version.** Do not group multiple patches into one entry unless they are truly inseparable.

#### Step B — Write the new entry

Open `/Users/jsuzanne/Github/stigix/CHANGELOG.md` and **prepend** a new entry at the very top (after the file header), following this exact format:

```markdown
## [vX.Y.Z-patch.NNN] - YYYY-MM-DD
### Added / Fixed / Changed / Performance / Refactored
- **Component**: Description of what changed and why. Use emojis for readability. 🚀
```

**Rules for the entry:**
- Use the correct date (`YYYY-MM-DD` in local time).
- Group bullet points under the appropriate heading(s): `Added`, `Fixed`, `Changed`, `Performance`, `Refactored`, `Removed`, `Documentation`.
- Be concise but specific — mention the file/component affected and the user-visible impact.
- **One entry per tagged version** — never aggregate multiple patches into one block.

### 3 — Stage, commit, and push

Stage **all** changed files (source + VERSION files + CHANGELOG together in one commit). 

> [!IMPORTANT]
> **Visibility Rule**: Always prefix the commit message with the new version number. This makes it easy to track which version is being built in the GitHub Actions list.

```bash
git add -A
git commit -m "$NEW_VER: <feat|fix>: <short description>

<expanded bullet summary of what changed>"
git push
```

### 4 — Push a matching git tag

```bash
git tag $NEW_VER
git push origin $NEW_VER
```

This triggers GitHub Actions which automatically creates:
- **Fast AMD64-only images**: For "patch" versions (e.g., `v1.2.1-patch.239`) and pushes to the `main` branch. This speeds up the development CI cycle.
- **Multi-platform images (AMD64 + ARM64)**: Only for official stable tags (e.g. `v1.2.1`). This ensures Raspberry Pi compatibility for releases.

### 5 — Verify CI Visibility

Check the Actions tab: `https://github.com/jsuzanne/stigix/actions`.
You should see the run name labeled with `🚀 Release $NEW_VER`.

## Rules

- **Prefix**: Never forget the `$NEW_VER:` prefix in the commit message.
- **Sync**: VERSION files and the git tag must always match exactly.
- **Timing**: Always bump version **before** the tag push.
- **Changelog Verification**: You MUST run the CHANGELOG audit (Step 2bis-A) at every deploy. Compare `git tag` output against documented entries in `CHANGELOG.md`. All missing versions MUST be backfilled — one entry per version — before committing.
- **No Grouping**: Never merge multiple patch versions into a single CHANGELOG entry unless they were released as a single atomic tag.
- **Doc-only**: Skip versioning for README/Documentation-only changes.
