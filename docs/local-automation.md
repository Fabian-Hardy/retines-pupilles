# Local Automation

TOOL-001 adds a local automation path that reduces manual copy and paste while
keeping branch, validation, and review rules explicit.

TOOL-005 adds the Python control-plane CLI for queue, state, dry-run, and
policy inspection. See `docs/local-agentic-control-plane.md`.

## Architecture

```text
localhost dashboard
  -> local runner
  -> Codex CLI, Docker, git, gh
  -> GitHub draft pull request
  -> ChatGPT and human review
```

The dashboard is read-only. It shows local state and the commands to run, but it
does not execute arbitrary commands from the browser.

The runner owns git and GitHub side effects. Codex receives the task prompt and
edits files, but the runner handles validation, commit, push, and draft PR
creation.

## Prerequisites

- Run from the repository root.
- Use the assigned task branch, never `main` or `develop`.
- Install and authenticate `git`, `gh`, and `codex`.
- Install Docker when backend validations are requested.
- Local Codex runs must use `--sandbox danger-full-access` on this machine.

## Dashboard

Start the dashboard:

```powershell
python tools\local-dashboard\app.py
```

Open `http://127.0.0.1:8787`.

The dashboard reads:

- `docs/project-progress/roadmap.json` for roadmap counts and phases;
- `git` for branch and status summaries;
- `.local-codex/runs` for recent local run metadata.

## Runner Commands

Show status:

```powershell
.\tools\local-codex-runner.ps1 status
```

Run one explicit task file:

```powershell
.\tools\local-codex-runner.ps1 run-task _tasks\tool-001-local-automation.md -TaskId TOOL-001
```

Run backend validations after Codex edits:

```powershell
.\tools\local-codex-runner.ps1 run-task _tasks\task-010-patient-list-filtering-pagination.md -TaskId TASK-010 -RunBackendValidation
```

`run-next` and `watch` are reserved for queue-aware automation and are safe V1
stubs. They do not run tasks.

## One-Task Flow

`tools/local-codex-task.ps1` performs this sequence:

1. Check that the working tree is clean.
2. Fetch and fast-forward `develop`.
3. Create or switch to the task branch.
4. Run `codex exec --sandbox danger-full-access --cd <repo> -` with the task file as stdin.
5. Write logs under `.local-codex/runs/<timestamp-task>/`.
6. Run `git diff --check`.
7. Optionally run backend validation through Docker.
8. Commit the resulting changes.
9. Push the branch.
10. Open a draft pull request against `develop`.

Codex is instructed not to commit, push, open a PR, or change branches.

## Logs

Each run writes:

- `run.json` for machine-readable metadata;
- `codex.log` for Codex output;
- `commands.log` for git and gh command output;
- `backend-validation.log` when backend validation is requested;
- `pull-request-body.md` for the generated draft PR body.

`.local-codex/` is local-only and ignored by git.

## Validation

For tooling-only changes, run:

```powershell
git diff --check
python -m py_compile tools\local-dashboard\app.py
```

For backend changes, use the repository backend validation commands documented
in `AGENTS.md`.
