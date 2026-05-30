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

    [switch]$SkipCommit,

    [switch]$SkipPush,

    [switch]$SkipPullRequest
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Get-RepoRoot {
    $scriptRoot = Split-Path -Parent $PSCommandPath
    return (Resolve-Path (Join-Path $scriptRoot "..")).Path
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

    Set-Location $RepoRoot

    $branch = Invoke-GitMaybe branch --show-current
    $status = Invoke-GitMaybe status --short
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
        $runs = Get-ChildItem -Path $runsRoot -Directory |
            Sort-Object LastWriteTime -Descending |
            Select-Object -First 8

        if ($null -eq $runs -or @($runs).Count -eq 0) {
            Write-Host "  none"
        }

        foreach ($run in $runs) {
            $metadataPath = Join-Path $run.FullName "run.json"
            if (Test-Path -Path $metadataPath) {
                $metadata = Get-Content -Path $metadataPath -Raw -Encoding UTF8 | ConvertFrom-Json
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
            $taskArguments = @{
                TaskFile = $TaskFile
                BaseBranch = $BaseBranch
                Repo = $Repo
            }

            if ($TaskId) {
                $taskArguments["TaskId"] = $TaskId
            }
            if ($BranchName) {
                $taskArguments["BranchName"] = $BranchName
            }
            if ($RunBackendValidation) {
                $taskArguments["RunBackendValidation"] = $true
            }
            if ($SkipCommit) {
                $taskArguments["SkipCommit"] = $true
            }
            if ($SkipPush) {
                $taskArguments["SkipPush"] = $true
            }
            if ($SkipPullRequest) {
                $taskArguments["SkipPullRequest"] = $true
            }

            & $taskScript @taskArguments
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
