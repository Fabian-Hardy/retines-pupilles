<#
.SYNOPSIS
Small command dispatcher for local Codex automation.

.DESCRIPTION
V1 implements `run-task` and `status`. The `run-next` and `watch` commands are
reserved for queue-aware automation and deliberately stop with clear messages.

.EXAMPLE
.\tools\local-codex-runner.ps1 status

.EXAMPLE
.\tools\local-codex-runner.ps1 run-task _tasks\tool-001-local-automation.md -TaskId TOOL-001
#>

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet("run-task", "run-next", "watch", "status")]
    [string]$Command = "status",

    [Parameter(Position = 1)]
    [string]$TaskFile,

    [string]$TaskId,

    [string]$BranchName,

    [string]$BaseBranch = "develop",

    [string]$Repo = "Fabian-Hardy/retines-pupilles",

    [switch]$RunBackendValidation,

    [switch]$SkipPush,

    [switch]$SkipPullRequest
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Get-RepoRoot {
    $scriptRoot = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $PSCommandPath }
    $candidateRoot = (Resolve-Path -LiteralPath (Join-Path $scriptRoot "..")).Path

    if (Get-Command git -ErrorAction SilentlyContinue) {
        $gitRoot = @(& git -C $candidateRoot rev-parse --show-toplevel 2>$null)
        if ($LASTEXITCODE -eq 0 -and $gitRoot.Count -gt 0) {
            return (Resolve-Path -LiteralPath $gitRoot[0]).Path
        }
    }

    if (Test-Path -LiteralPath (Join-Path $candidateRoot ".git")) {
        return $candidateRoot
    }

    throw "Unable to determine repository root from script path '$scriptRoot'."
}

function Resolve-RepoFile {
    param(
        [string]$Path,
        [string]$RepoRoot
    )

    if ([string]::IsNullOrWhiteSpace($Path)) {
        throw "Missing file path."
    }

    $candidatePath = if ([System.IO.Path]::IsPathRooted($Path)) {
        $Path
    }
    else {
        Join-Path $RepoRoot $Path
    }

    $resolvedPath = (Resolve-Path -LiteralPath $candidatePath -ErrorAction Stop).Path
    if (-not (Test-Path -LiteralPath $resolvedPath -PathType Leaf)) {
        throw "File path '$Path' does not resolve to a file."
    }

    return $resolvedPath
}

function Invoke-GitMaybe {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)

    $output = & git @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        return @("git $($Arguments -join ' ') failed: $($output -join ' ')")
    }

    if ($null -eq $output) {
        return @()
    }

    return @($output)
}

function Show-Status {
    param([string]$RepoRoot)

    Set-Location -LiteralPath $RepoRoot

    $branch = @(Invoke-GitMaybe branch --show-current)
    $status = @(Invoke-GitMaybe status --short)
    $runsRoot = Join-Path $RepoRoot ".local-codex/runs"

    Write-Host "Repository: $RepoRoot"
    Write-Host "Branch: $($branch -join ' ')"
    Write-Host ""
    Write-Host "Git status:"
    if ($null -eq $status -or @($status).Count -eq 0) {
        Write-Host "  clean"
    }
    else {
        foreach ($line in $status) {
            Write-Host "  $line"
        }
    }

    Write-Host ""
    Write-Host "Recent local Codex runs:"
    if (-not (Test-Path -Path $runsRoot)) {
        Write-Host "  none"
    }
    else {
        $runs = @(Get-ChildItem -Path $runsRoot -Directory |
            Sort-Object LastWriteTime -Descending |
            Select-Object -First 8)

        if ($null -eq $runs -or @($runs).Count -eq 0) {
            Write-Host "  none"
        }

        foreach ($run in $runs) {
            $metadataPath = Join-Path $run.FullName "run.json"
            if (Test-Path -Path $metadataPath) {
                $metadata = Get-Content -LiteralPath $metadataPath -Raw -Encoding UTF8 | ConvertFrom-Json
                Write-Host ("  {0}  {1}  {2}  {3}" -f $metadata.started_at, $metadata.status, $metadata.task_id, $metadata.branch)
            }
            else {
                Write-Host ("  {0}  {1}" -f $run.LastWriteTime.ToString("o"), $run.Name)
            }
        }
    }

    Write-Host ""
    Write-Host "Dashboard:"
    Write-Host "  python tools\local-dashboard\app.py"
    Write-Host "  http://127.0.0.1:8787"
}

$repoRoot = Get-RepoRoot
$originalLocation = Get-Location

try {
    switch ($Command) {
        "run-task" {
            if (-not $TaskFile) {
                throw "Missing task file. Example: .\tools\local-codex-runner.ps1 run-task _tasks\tool-001-local-automation.md -TaskId TOOL-001"
            }

            $taskScript = Join-Path $repoRoot "tools/local-codex-task.ps1"
            $resolvedTaskFile = Resolve-RepoFile -Path $TaskFile -RepoRoot $repoRoot
            $taskParameters = @{
                TaskFile = $resolvedTaskFile
                BaseBranch = $BaseBranch
                Repo = $Repo
            }

            if ($TaskId) {
                $taskParameters.TaskId = $TaskId
            }
            if ($BranchName) {
                $taskParameters.BranchName = $BranchName
            }
            if ($RunBackendValidation) {
                $taskParameters.RunBackendValidation = $true
            }
            if ($SkipPush) {
                $taskParameters.SkipPush = $true
            }
            if ($SkipPullRequest) {
                $taskParameters.SkipPullRequest = $true
            }

            & $taskScript @taskParameters
            if ($LASTEXITCODE -ne 0) {
                exit $LASTEXITCODE
            }
            break
        }

        "run-next" {
            Write-Host "run-next is reserved for queue-aware automation and is not implemented in V1."
            Write-Host "Use run-task with an explicit task file."
            break
        }

        "watch" {
            Write-Host "watch is reserved for queue-aware automation and is not implemented in V1."
            Write-Host "Use the localhost dashboard for read-only status and run-task for explicit execution."
            break
        }

        "status" {
            Show-Status -RepoRoot $repoRoot
            break
        }
    }
}
finally {
    Set-Location $originalLocation
}
