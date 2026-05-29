# AGENTS.md — Rétines & Pupilles

This repository is developed through small scoped tasks, usually tracked as `TASK-XXX` GitHub issues and pull requests.

## Branch policy

- Never commit directly to `main` or `develop`.
- Work only on the branch assigned in the issue.
- Open pull requests against `develop` unless the issue explicitly says otherwise.
- Keep each pull request scoped to one task.
- Do not reformat unrelated files.
- Do not modify secrets, branch protection, repository settings, or deployment credentials.

## Task discipline

Every task must have:

- a task id such as `TASK-010`;
- a target version such as `v0.2.0`;
- a clear objective;
- acceptance criteria;
- expected validation commands;
- known dependencies and sequencing constraints.

If the implementation requires a scope change, document it in the pull request before expanding the work.

## Backend validation

Run these commands for backend changes:

```powershell
docker compose -f docker-compose.yml -f docker-compose.dev.yml run --rm backend ruff check .
docker compose -f docker-compose.yml -f docker-compose.dev.yml run --rm backend mypy app tests --show-traceback
docker compose -f docker-compose.yml -f docker-compose.dev.yml run --rm backend pytest
```

## Frontend validation

Run these commands for frontend changes once the frontend shell exists:

```powershell
docker compose -f docker-compose.yml -f docker-compose.dev.yml build frontend
```

If the frontend task adds lint, type-check or test scripts, run them through Docker or the documented local frontend command.

## Code quality rules

- Keep typing strict.
- Do not remove or weaken tests to make CI pass.
- Do not silence lint, type-checking, or validation errors without justification.
- Prefer explicit schemas and typed API contracts.
- Keep database migrations deterministic and reversible where practical.
- Keep logs free of patient-sensitive data.

## Security and privacy rules

- Treat patient data as sensitive.
- Do not log passwords, tokens, session identifiers, health data, prescriptions, or full patient records.
- Do not introduce broad CORS or authentication bypasses.
- Do not add dependencies unless required by the task.
- Do not store generated secrets in the repository.

## Pull request requirements

Every PR must include:

- task id;
- summary;
- changed files or areas;
- validation commands run;
- known limitations;
- follow-up work, if any.

Preferred PR decision language for review:

- `APPROVE` — ready to merge after checks;
- `REQUEST_CHANGES` — corrections required;
- `BLOCKED` — do not merge until dependency or design issue is resolved.

## Merge policy

- Merge only after CI is green.
- Merge only after the reviewer approves.
- Merge dependent tasks in dependency order, not completion order.
- After each merge into `develop`, update or rebase still-open agent branches before merging them.
