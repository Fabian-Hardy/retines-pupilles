# Automation Policy

TOOL-001 automation is allowed to prepare draft pull requests, but it must not
weaken the repository branch policy.

## Non-Negotiable Rules

- Never push directly to `develop`.
- Never push directly to `main`.
- Open automation pull requests against `develop` unless an issue explicitly
  says otherwise.
- Keep each automation run scoped to one task id.
- Do not modify secrets, branch protection, repository settings, deployment
  credentials, or patient data.
- Keep `.local-codex/` local-only.

## Low-Risk Automerge Candidates

A pull request may be labeled as a low-risk automerge candidate only when all of
these are true:

- The task is documentation, local tooling, test-only, or formatting limited to
  files already in the task scope.
- No backend or frontend product behavior changes.
- No authentication, authorization, session, privacy, deployment, or migration
  changes.
- No new runtime dependency.
- No generated secret or patient-sensitive data.
- Required validation commands and CI are green.
- ChatGPT review returns `APPROVE`.
- No human reviewer has requested changes.

Low-risk automerge is still optional. If there is uncertainty, require human
review.

## Human Review Required

Human review is required for any pull request touching:

- authentication, authorization, sessions, or password handling;
- patient data models, patient API behavior, prescriptions, documents, or audit
  logs;
- database migrations or irreversible data operations;
- CORS, security headers, rate limits, tokens, secrets, or privacy controls;
- Docker, deployment, backup, restore, or infrastructure configuration;
- production dependencies or dependency update policy;
- external integrations, email, OCR, accounting, calendar, or supplier systems;
- broad refactors or cross-module contracts;
- any change where validations were skipped, failed, or incomplete.

## Labels

Use these labels to make automation decisions explicit:

- `automation:local-codex` for PRs created by the local runner.
- `automation:automerge-candidate` for low-risk PRs that satisfy the policy.
- `automation:human-review-required` for PRs that must not automerge.
- `risk:low`, `risk:medium`, and `risk:high` for review routing.
- `area:tooling`, `area:docs`, `area:backend`, `area:frontend`, and
  `area:infra` for ownership.
- `status:ready-for-codex`, `status:in-progress`, `status:review`, and
  `status:blocked` for task flow.

Labels document intent only. They do not override branch protection, failed CI,
or reviewer decisions.

## Review Decision Language

Automation and reviewers should use the repository decision language:

- `APPROVE` means the PR is ready to merge after checks.
- `REQUEST_CHANGES` means corrections are required.
- `BLOCKED` means the PR must not merge until a dependency or design issue is
  resolved.

## Merge Order

Merge dependent tasks in dependency order, not completion order. After each
merge into `develop`, update or rebase still-open automation branches before
merging them.
