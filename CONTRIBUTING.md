# Contributing / Team Workflow

## Branch model

```
main   ← protected, always demo-able, tagged at milestones (M-6, M-9)
  ↑ PR only, 1 review required
dev    ← protected, integration branch, all features land here first
  ↑ PR only
feature/<member>-<short-task>   ← where you actually work
```

**Never commit directly to `main` or `dev`.** Always branch off `dev`.

### Branch naming

```
feature/m1-dashboard-shell
feature/m2-conflict-map-layer
feature/m3-matches-endpoint
feature/m4-crs-normalization
feature/m5-weighted-scoring
feature/m6-postgis-schema
fix/<short-desc>
```

### Day-1 setup (each member, once)

```bash
git clone <repo-url>
cd bhudrishti
git checkout dev
git pull
git checkout -b feature/m<N>-<your-first-task>
```

### Daily loop

```bash
git checkout dev && git pull            # start of day, sync
git checkout feature/m<N>-<task>
git rebase dev                          # keep your branch current, avoid drift
# ...work, commit often...
git push -u origin feature/m<N>-<task>
# open PR into dev on GitHub
```

## Commit convention (Conventional Commits, lightweight)

```
feat(m4): add CRS normalization to pyproj
fix(m3): correct 422 on empty geometry upload
docs(contracts): add recommendation action enum
test(m6): precision/recall harness for matching
chore: update docker-compose ports
```

Prefix with your module tag (`m1`–`m6`) when the change is role-specific so `git log --grep` stays useful.

## Pull requests

- PR into `dev`, never `main`.
- 1 approval required (GitHub branch protection enforces this).
- CI (`.github/workflows/ci.yml`) must pass — lint + basic tests.
- Small, frequent PRs > one giant PR at the end. Aim for one PR per roadmap milestone sub-task.
- Use the PR template checklist — confirm you didn't change a frozen contract in `docs/contracts/` without a team sync.

## Frozen contracts rule

`docs/contracts/*.json` are **frozen after Day 1**. If your engine needs a field that isn't there, don't silently add it — raise it in standup, update the contract in one PR everyone acks, then build against the new version. This is what lets M1/M2 build against mocks while M3/M4/M5 build the real thing in parallel without merge hell.

## Merging to `main`

Only at roadmap milestones (M-6 vertical slice, M-9 demo-ready). Team lead (M-lead) opens `dev → main` PR, tags a release (`v0.1-vertical-slice`, `v1.0-demo`).

## Branch protection to set on GitHub (Settings → Branches)

For both `main` and `dev`:
- Require a pull request before merging
- Require 1 approval
- Require status checks to pass (CI)
- Do not allow force pushes
- Do not allow deletions
