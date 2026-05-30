# TOOL-002 — Harden local Codex runner on Windows PowerShell

## Context

The local Codex runner introduced in TOOL-001 is useful, but it currently shows several reliability issues on Windows PowerShell.

Known issues observed locally:

1. `tools/local-codex-runner.ps1 run-task` fails around `-BaseBranch`.
2. `tools/local-codex-task.ps1` breaks under `Set-StrictMode` when `.Count` is used on the result of `Invoke-GitOutput` and the command returns zero or one line.
3. Relative log paths can be resolved from `C:\Users\ninif` instead of the repository root.
4. `DataReceivedEventHandler` callbacks for stdout/stderr can crash PowerShell with: `There is no Runspace available`.
5. `gh pr view --head` is not supported by the local GitHub CLI version.
6. Codex output can be too verbose or heavily buffered depending on the workaround used.

## Goal

Make the official local Codex runner reliable on Windows PowerShell.

This task must update the official runner scripts:

- `tools/local-codex-runner.ps1`
- `tools/local-codex-task.ps1`

The local patched copy `tools/local-codex-task-fixed.ps1` may be used as a reference only if present, but the final supported entrypoints must remain the official scripts above.

## Scope

Strictly limit this task to the local Codex runner tooling.

Allowed changes:

- Fix PowerShell argument forwarding between `local-codex-runner.ps1` and `local-codex-task.ps1`.
- Fix `Set-StrictMode`-unsafe assumptions around scalar versus array command output.
- Ensure all generated logs and temporary files are rooted in the repository, not in the caller's current directory.
- Replace or harden stdout/stderr handling so it works in Windows PowerShell without runspace crashes.
- Replace unsupported `gh pr view --head` usage with a GitHub CLI command compatible with the installed local version.
- Reduce console noise while preserving complete logs on disk.
- Add or update documentation/comments when useful.
- Add lightweight validation where practical.

Out of scope:

- Backend authentication changes.
- Application feature work.
- Database migrations.
- Frontend changes.
- CI workflow changes unless strictly required to validate the runner scripts.

## Required fixes

### 1. Fix `-BaseBranch` handling

Ensure `local-codex-runner.ps1 run-task` forwards `-BaseBranch` correctly to `local-codex-task.ps1`.

Expected behavior:

```powershell
.\tools\local-codex-runner.ps1 run-task `
  "_tasks\example.md" `
  -TaskId EXAMPLE `
  -BranchName "feature/example" `
-BaseBranch develop

````

must not fail because of missing, duplicated, unknown, or incorrectly forwarded `-BaseBranch` parameters.

If `-BaseBranch` is omitted, the default must remain `develop`.

### 2. Fix `.Count` under `Set-StrictMode`

Any command output that may contain zero, one, or multiple lines must be normalized before `.Count` is used.

Use patterns such as:

```powershell
$lines = @(Invoke-GitOutput ...)
$count = $lines.Count
````

Avoid relying on PowerShell scalar coercion.

### 3. Resolve paths from the repository root

The runner must resolve repository-relative paths from the actual repository root, not from the shell's current working directory.

Expected behavior:

Running the script from either location should produce logs inside the repository:

```powershell
cd C:\Dev\retines-pupilles
.\tools\local-codex-runner.ps1 status

cd C:\Users\ninif
C:\Dev\retines-pupilles\tools\local-codex-runner.ps1 status
```

Use a robust repo-root detection strategy, for example:

* derive the root from `$PSScriptRoot`, and/or
* verify with `git rev-parse --show-toplevel`.

### 4. Remove runspace-unsafe stdout/stderr handlers

Do not write to PowerShell host APIs from `DataReceivedEventHandler` callbacks.

The implementation should avoid the known crash:

```text
There is no Runspace available
```

Acceptable approaches include:

* redirecting stdout/stderr to log files via `Start-Process`,
* using synchronous process execution with safe stream handling,
* using .NET async reads without PowerShell runspace-dependent callbacks.

The final solution must preserve full stdout/stderr logs on disk.

### 5. Replace unsupported `gh pr view --head`

Do not use:

```powershell
gh pr view --head ...
```

Use a compatible alternative, for example:

```powershell
gh pr list --head $BranchName --base $BaseBranch --state open --json number,url,title
```

The runner should continue to detect or display the relevant PR when possible.

### 6. Control verbosity

The runner should avoid dumping excessive Codex output to the terminal by default.

Expected behavior:

* full output is written to log files;
* console output remains readable;
* on failure, show the relevant tail of logs;
* document where the complete logs are stored.

## Acceptance criteria

The following must pass on Windows PowerShell from a clean `develop` branch:

```powershell
git switch develop
git pull --ff-only origin develop
git status --short
```

Then, after applying the fix:

```powershell
.\tools\local-codex-runner.ps1 status
```

Expected:

* command completes without PowerShell errors;
* no runspace crash;
* paths shown or used by the runner are repository-rooted.

Also validate the task runner path using a small harmless task file or dry-run style flow if available.

At minimum, this command must no longer fail because of `-BaseBranch` handling:

```powershell
.\tools\local-codex-runner.ps1 run-task `
  "_tasks\tool-002-harden-local-codex-runner-windows-powershell.md" `
  -TaskId TOOL-002 `
  -BranchName "chore/tool-002-harden-local-codex-runner-windows-powershell" `
  -BaseBranch develop
```

If Codex itself fails for an unrelated reason, the runner must still:

* write logs to the expected repository-local log path;
* exit with a clear error;
* not crash PowerShell;
* not leave the repository in an ambiguous state.

## Validation commands

Run the most relevant available checks, for example:

```powershell
.\tools\local-codex-runner.ps1 status
```

If the project has existing script or tooling tests, run them.

If no automated tests exist for the PowerShell scripts, perform manual validation and document the exact commands used in the PR description.

## Deliverables

* Updated `tools/local-codex-runner.ps1`.
* Updated `tools/local-codex-task.ps1`.
* No backend or frontend feature changes.
* PR dedicated to TOOL-002.
* PR description listing:

  * bugs fixed;
  * validation commands run;
  * any remaining limitations.
