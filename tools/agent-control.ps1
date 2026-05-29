<#
.SYNOPSIS
Local helper to manage agent issue waves for the Retines & Pupilles repository.

.DESCRIPTION
This script reads docs/agent-queue/waves.json and uses the GitHub CLI (`gh`) to:
- create/update the labels used by the agent workflow;
- activate all issues in a named wave by adding their configured labels;
- list open issues with status:ready-for-codex;
- optionally create issues in bulk by running the GitHub Actions workflow added in this repository.

The script does not call Codex directly. It only manages GitHub issues/labels so that the repository orchestration can pick up ready tasks.

.EXAMPLES
.	ools\agent-control.ps1 labels
.	ools\agent-control.ps1 wave wave-02-auth-foundation
.	ools\agent-control.ps1 ready
.	ools\agent-control.ps1 create-issues docs/agent-queue/issues-batch-01.json
#>

param(
    [Parameter(Position = 0)]
    [ValidateSet("labels", "wave", "ready", "create-issues", "waves")]
    [string]$Command = "ready",

    [Parameter(Position = 1)]
    [string]$Name,

    [string]$Config = "docs/agent-queue/waves.json",

    [switch]$ApplyReadyLabel
)

$ErrorActionPreference = "Stop"

function Assert-GhAvailable {
    $gh = Get-Command gh -ErrorAction SilentlyContinue
    if (-not $gh) {
        throw "GitHub CLI 'gh' was not found in PATH. Install it or open a shell where gh is available."
    }
}

function Read-AgentConfig {
    param([string]$Path)

    if (-not (Test-Path -Path $Path)) {
        throw "Config file not found: $Path. Run this script from the repository root."
    }

    $raw = Get-Content -Path $Path -Raw -Encoding UTF8
    return $raw | ConvertFrom-Json
}

function Invoke-Gh {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)

    Write-Host "gh $($Arguments -join ' ')" -ForegroundColor DarkGray
    & gh @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "gh command failed with exit code $LASTEXITCODE"
    }
}

function Ensure-Labels {
    param($ConfigData)

    foreach ($label in $ConfigData.labels) {
        Invoke-Gh label create $label.name `
            --repo $ConfigData.repo `
            --color $label.color `
            --description $label.description `
            --force
    }
}

function Get-IssueNumberForTask {
    param(
        [string]$Repo,
        [string]$TaskId
    )

    $json = & gh issue list `
        --repo $Repo `
        --state all `
        --search "$TaskId in:title" `
        --json number,title `
        --limit 20

    if ($LASTEXITCODE -ne 0) {
        throw "Failed to search issue for $TaskId"
    }

    $items = $json | ConvertFrom-Json
    $match = $items | Where-Object { $_.title -like "*$TaskId*" } | Select-Object -First 1

    if (-not $match) {
        throw "No GitHub issue found for task $TaskId. Create issues first or check the task id."
    }

    return [int]$match.number
}

function Activate-Wave {
    param(
        $ConfigData,
        [string]$WaveId
    )

    $wave = $ConfigData.waves | Where-Object { $_.id -eq $WaveId } | Select-Object -First 1
    if (-not $wave) {
        throw "Unknown wave '$WaveId'. Run '.\tools\agent-control.ps1 waves' to list available waves."
    }

    Write-Host "Activating wave: $($wave.id)" -ForegroundColor Cyan
    Write-Host $wave.description

    Ensure-Labels -ConfigData $ConfigData

    foreach ($task in $wave.tasks) {
        $issueNumber = Get-IssueNumberForTask -Repo $ConfigData.repo -TaskId $task.task
        Write-Host "Activating $($task.task) on issue #$issueNumber" -ForegroundColor Green

        foreach ($label in $task.labels) {
            Invoke-Gh issue edit $issueNumber `
                --repo $ConfigData.repo `
                --add-label $label
        }
    }

    Write-Host "Wave activated: $WaveId" -ForegroundColor Green
}

function Show-ReadyIssues {
    param($ConfigData)

    Invoke-Gh issue list `
        --repo $ConfigData.repo `
        --label "status:ready-for-codex"
}

function Show-Waves {
    param($ConfigData)

    foreach ($wave in $ConfigData.waves) {
        Write-Host ""
        Write-Host $wave.id -ForegroundColor Cyan
        Write-Host "  $($wave.description)"
        if ($wave.requires) {
            Write-Host "  Requires: $($wave.requires -join ', ')"
        }
        $taskIds = $wave.tasks | ForEach-Object { $_.task }
        Write-Host "  Tasks: $($taskIds -join ', ')"
    }
}

function Run-CreateIssuesWorkflow {
    param(
        $ConfigData,
        [string]$BatchFile,
        [bool]$Ready
    )

    if (-not $BatchFile) {
        $BatchFile = "docs/agent-queue/issues-batch-01.json"
    }

    Invoke-Gh workflow run "Create Agent Issues" `
        --repo $ConfigData.repo `
        -f "batch_file=$BatchFile" `
        -f "apply_ready_label=$Ready"

    Write-Host "Workflow requested. Check Actions > Create Agent Issues." -ForegroundColor Green
}

Assert-GhAvailable
$configData = Read-AgentConfig -Path $Config

switch ($Command) {
    "labels" {
        Ensure-Labels -ConfigData $configData
        break
    }
    "wave" {
        if (-not $Name) {
            throw "Missing wave id. Example: .\tools\agent-control.ps1 wave wave-02-auth-foundation"
        }
        Activate-Wave -ConfigData $configData -WaveId $Name
        break
    }
    "ready" {
        Show-ReadyIssues -ConfigData $configData
        break
    }
    "create-issues" {
        Run-CreateIssuesWorkflow -ConfigData $configData -BatchFile $Name -Ready ([bool]$ApplyReadyLabel)
        break
    }
    "waves" {
        Show-Waves -ConfigData $configData
        break
    }
}
