# Local Agentic Control Plane

TOOL-005 adds a local, repository-scoped control plane for preparing an
automated development flow:

```text
queue -> branch -> Codex local -> local tests -> commit -> push -> PR -> CI -> review policy -> squash merge -> next task
```

This version is intentionally a reporting and state-management layer. It does
not run Codex, create commits, push branches, open pull requests, merge pull
requests, deploy, or access the VPS.

## Queue

The CLI reuses the existing repository queue at
`docs/agent-queue/issues-batch-01.json` by default. That file already contains
task ids, titles, branches, dependencies, risks, scopes, and validation types.
The control plane normalizes its legacy fields into the TOOL-005 model:

- `dependencies` becomes `depends_on`;
- `risk` becomes `risk_level`;
- `validation` becomes `validation_commands`;
- missing `status` defaults to `pending`;
- missing `allow_auto_merge` defaults to `false`;
- missing `notes` defaults to an empty list.

Future queue entries may use these fields directly:

```json
{
  "id": "TOOL-005",
  "title": "Local agentic development control plane",
  "branch": "tool/tool-005-local-agentic-control-plane",
  "status": "pending",
  "depends_on": [],
  "risk_level": "low",
  "allow_auto_merge": false,
  "validation_commands": [
    "git diff --check",
    "python -m unittest tests.tools.test_agentic_control_plane"
  ],
  "notes": ["Reports readiness only; does not merge."]
}
```

## Runtime State

Local runtime state is stored under `.local/agentic-control-plane/`, which is
ignored by Git. Task state is JSON under:

```text
.local/agentic-control-plane/tasks/<TASK-ID>.json
```

Each task state tracks:

- task id;
- status;
- branch;
- PR number when known;
- timestamps;
- last error;
- validation results;
- log paths.

The standard log paths are:

```text
.local/agentic-control-plane/runs/<TASK-ID>/stdout.log
.local/agentic-control-plane/runs/<TASK-ID>/stderr.log
.local/agentic-control-plane/runs/<TASK-ID>/codex.log
.local/agentic-control-plane/runs/<TASK-ID>/run.json
```

TOOL-005 records the paths but does not yet execute a real run that writes all
of these logs.

## Commands

Initialize local state:

```bash
python tools/agentic_control_plane.py init
```

List queue entries:

```bash
python tools/agentic_control_plane.py queue
python tools/agentic_control_plane.py queue --json
```

Show local git and task state:

```bash
python tools/agentic_control_plane.py status
```

Show the next unblocked pending task:

```bash
python tools/agentic_control_plane.py next
```

Report planned actions for a task:

```bash
python tools/agentic_control_plane.py run --task-id TOOL-005 --dry-run
```

`run` without `--dry-run` refuses in TOOL-005.

Validate queue and state JSON:

```bash
python tools/agentic_control_plane.py validate
```

Mark local task state:

```bash
python tools/agentic_control_plane.py mark TOOL-005 --status pr_open --pr-number 123
python tools/agentic_control_plane.py mark TOOL-005 --status failed --error "validation failed"
```

## Statuses

- `pending`: queued and not started.
- `running`: local automation has started.
- `failed`: local automation or validation failed.
- `pr_open`: a pull request exists.
- `ci_pending`: CI is still running or waiting.
- `ready_to_merge`: policy reports the PR is ready, but this tool still does not merge.
- `merged`: the task has been merged.
- `skipped`: intentionally skipped.
- `needs_human`: blocked on a human decision or manual review.

## Git and GitHub Inspection

The CLI can inspect:

- current branch;
- clean or dirty working tree;
- existing local branch;
- existing fetched remote branch;
- existing PR for a branch through the `gh` CLI when available.

GitHub inspection is best-effort. A missing or unauthenticated `gh` CLI is
reported as unavailable, not treated as permission to continue with side
effects.

## Review Policy

The merge policy function reports `ready_to_merge` only when all checks pass:

- PR is not draft;
- CI is green;
- changed files are scoped to the task;
- no secrets are detected;
- no destructive migration is detected;
- no sensitive infrastructure or production change is detected;
- no major UX or business-rule change is detected;
- `allow_auto_merge` is `true`;
- `risk_level` is `low`.

This policy reports readiness only. It never performs a merge.

## Local Validation

For TOOL-005-only changes, run:

```bash
git diff --check
python -m unittest tests.tools.test_agentic_control_plane
python tools/agentic_control_plane.py validate
```

The full acceptance validation also includes:

```bash
cd backend && source ../.venv/bin/activate && set -a && source .env && set +a && ruff check . && mypy . && pytest
cd frontend && npm ci && npm run typecheck && npm run build
```

## Not Implemented Yet

TOOL-005 deliberately does not:

- run Codex;
- create or switch branches;
- commit changes;
- push branches;
- create pull requests;
- merge pull requests;
- deploy anything;
- touch production or VPS access;
- store secrets.

Future TOOL-006 or a TOOL-005 follow-up should implement the next safe step:
an explicit local runner that can execute one queued task behind a hard
confirmation gate, write real stdout/stderr/Codex logs, update state as it
progresses, and open a draft PR without merge capability.
