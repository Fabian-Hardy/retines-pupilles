<#
.SYNOPSIS
Run one local Codex task from a task prompt file.

.DESCRIPTION
This script is the local end-to-end runner for TOOL-001. It keeps the
repository workflow outside Codex itself: the script updates develop, creates
or switches to a task branch, runs `codex exec` with the required local sandbox,
validates, commits, pushes, and opens a draft pull request.

Codex receives the task file as stdin and is instructed not to commit or push.
Runtime logs are written under .local-codex/runs, which must remain ignored by
git.

.EXAMPLE
.\tools\local-codex-task.ps1 _tasks\tool-001-local-automation.md -TaskId TOOL-001
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateScript({ Test-Path -Path $_ -PathType Leaf })]
    [string]$TaskFile,

    [string]$TaskId,

    [string]$BranchName,

    [string]$BaseBranch = "develop",

    [string]$Repo = "Fabian-Hardy/retines-pupilles",

    [switch]$RunBackendValidation,

    [switch]$SkipPush,

    [switch]$SkipPullRequest,

    [string]$CommitMessage,

    [string]$PrTitle
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Get-RepoRoot {
    $scriptRoot = Split-Path -Parent $PSCommandPath
    return (Resolve-Path (Join-Path $scriptRoot "..")).Path
}

function Assert-CommandAvailable {
    param([string]$Name)

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' was not found in PATH."
    }
}

function ConvertTo-Slug {
    param([string]$Value)

    $slug = $Value.ToLowerInvariant()
    $slug = [regex]::Replace($slug, "[^a-z0-9]+", "-")
    $slug = $slug.Trim("-")
    if ($slug.Length -gt 72) {
        $slug = $slug.Substring(0, 72).Trim("-")
    }
    return $slug
}

function Get-TaskIdFromText {
    param([string]$Text)

    $match = [regex]::Match($Text, "\b(?:TASK|TOOL)-\d{3,4}\b", [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
    if (-not $match.Success) {
        return $null
    }

    return $match.Value.ToUpperInvariant()
}

function Get-TaskTitleFromText {
    param(
        [string]$Text,
        [string]$DefaultTaskId
    )

    foreach ($line in ($Text -split "\r?\n")) {
        if ($line -match "^\s*#\s+(.+?)\s*$") {
            $title = $Matches[1].Trim()
            $title = [regex]::Replace($title, "^\b(?:TASK|TOOL)-\d{3,4}\b\s*[-:]\s*", "", "IgnoreCase")
            if ($title) {
                return $title
            }
        }

        if ($line -match "^\s*title\s*:\s*(.+?)\s*$") {
            return $Matches[1].Trim()
        }
    }

    return $DefaultTaskId
}

function Invoke-GitOutput {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)

    $output = & git @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "git $($Arguments -join ' ') failed with exit code $LASTEXITCODE.`n$($output -join "`n")"
    }

    if ($null -eq $output) {
        return @()
    }

    return @($output)
}

function Invoke-LoggedNative {
    param(
        [string]$FilePath,
        [string[]]$Arguments,
        [string]$LogPath,
        [string]$InputText
    )

    $display = "$FilePath $($Arguments -join ' ')"
    Write-Host $display -ForegroundColor DarkGray

    Add-Content -Path $LogPath -Encoding UTF8 -Value ""
    Add-Content -Path $LogPath -Encoding UTF8 -Value ">>> $display"

    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo.FileName = $FilePath
    $process.StartInfo.WorkingDirectory = (Get-Location).Path
    $process.StartInfo.UseShellExecute = $false
    $process.StartInfo.RedirectStandardOutput = $true
    $process.StartInfo.RedirectStandardError = $true
    $process.StartInfo.RedirectStandardInput = ($null -ne $InputText)

    foreach ($argument in $Arguments) {
        [void]$process.StartInfo.ArgumentList.Add($argument)
    }

    [void]$process.Start()

    if ($null -ne $InputText) {
        $process.StandardInput.Write($InputText)
        $process.StandardInput.Close()
    }

    $stdout = $process.StandardOutput.ReadToEnd()
    $stderr = $process.StandardError.ReadToEnd()

    $process.WaitForExit()
    $exitCode = $process.ExitCode
    $process.Dispose()

    if ($stdout) {
        Write-Host $stdout.TrimEnd()
        Add-Content -Path $LogPath -Encoding UTF8 -Value $stdout.TrimEnd()
    }

    if ($stderr) {
        Write-Host $stderr.TrimEnd() -ForegroundColor Yellow
        Add-Content -Path $LogPath -Encoding UTF8 -Value $stderr.TrimEnd()
    }

    if ($exitCode -ne 0) {
        throw "$display failed with exit code $exitCode. See $LogPath."
    }

    return $exitCode
}

function Invoke-GhCapture {
    param(
        [string[]]$Arguments,
        [string]$LogPath,
        [switch]$AllowFailure
    )

    $display = "gh $($Arguments -join ' ')"
    Write-Host $display -ForegroundColor DarkGray
    Add-Content -Path $LogPath -Encoding UTF8 -Value ""
    Add-Content -Path $LogPath -Encoding UTF8 -Value ">>> $display"

    $output = & gh @Arguments 2>&1
    $exitCode = $LASTEXITCODE
    if ($output) {
        Add-Content -Path $LogPath -Encoding UTF8 -Value ($output -join "`n")
    }

    if ($exitCode -ne 0 -and -not $AllowFailure) {
        throw "$display failed with exit code $exitCode.`n$($output -join "`n")"
    }

    return [pscustomobject]@{
        ExitCode = $exitCode
        Output = ($output -join "`n")
    }
}

function Write-RunMetadata {
    param(
        [System.Collections.IDictionary]$Metadata,
        [string]$Path
    )

    $Metadata | ConvertTo-Json -Depth 6 | Set-Content -Path $Path -Encoding UTF8
}

function Assert-CleanTree {
    $status = @(Invoke-GitOutput status --porcelain)
    if ($status.Count -gt 0) {
        throw "Working tree is not clean. Commit or stash local changes before running local Codex automation."
    }
}

function Get-ChangedFilesForPr {
    param([string]$BaseBranchName)

    $files = @(Invoke-GitOutput diff --name-only "$BaseBranchName...HEAD")
    if ($files.Count -eq 0) {
        return "- No changed files detected."
    }

    return (($files | ForEach-Object { "- $_" }) -join "`n")
}

function New-PrBody {
    param(
        [string]$Task,
        [string]$ChangedFiles,
        [string[]]$ValidationCommands,
        [string]$BodyPath
    )

    $validations = if ($ValidationCommands.Count -gt 0) {
        ($ValidationCommands | ForEach-Object { "- ``$_``" }) -join "`n"
    }
    else {
        "- No validation commands recorded."
    }

    $body = @"
## Task id
$Task

## Summary
- Local Codex automation run completed for $Task.
- Review the diff and CI output before merging.

## Changed files or areas
$ChangedFiles

## Validation commands run
$validations

## Known limitations
- Draft PR only; human review and CI remain required unless the automation policy explicitly allows automerge.

## Follow-up work
- Address review comments from ChatGPT and human reviewers.
"@

    $body | Set-Content -Path $BodyPath -Encoding UTF8
}

$originalLocation = Get-Location
$repoRoot = Get-RepoRoot
$runMetadata = $null
$metadataPath = $null

try {
    Set-Location $repoRoot

    Assert-CommandAvailable git
    Assert-CommandAvailable codex
    Assert-CommandAvailable gh
    if ($RunBackendValidation) {
        Assert-CommandAvailable docker
    }

    $resolvedTaskFile = (Resolve-Path $TaskFile).Path
    $taskText = Get-Content -Path $resolvedTaskFile -Raw -Encoding UTF8

    if (-not $TaskId) {
        $TaskId = Get-TaskIdFromText -Text $taskText
    }
    if (-not $TaskId) {
        throw "Task id not provided and not found in task file. Use TASK-XXX or TOOL-XXX."
    }
    $TaskId = $TaskId.ToUpperInvariant()

    $taskTitle = Get-TaskTitleFromText -Text $taskText -DefaultTaskId $TaskId

    if (-not $BranchName) {
        $BranchName = "feature/$(ConvertTo-Slug "$TaskId-$taskTitle")"
    }

    if (-not $CommitMessage) {
        $CommitMessage = "${TaskId}: $taskTitle"
    }

    if (-not $PrTitle) {
        $PrTitle = "${TaskId}: $taskTitle"
    }

    Assert-CleanTree

    $runStamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $runsRoot = Join-Path $repoRoot ".local-codex/runs"
    $runDir = Join-Path $runsRoot "$runStamp-$(ConvertTo-Slug $TaskId)"
    New-Item -ItemType Directory -Force -Path $runDir | Out-Null

    $commandLog = Join-Path $runDir "commands.log"
    $codexLog = Join-Path $runDir "codex.log"
    $backendLog = Join-Path $runDir "backend-validation.log"
    $prBodyPath = Join-Path $runDir "pull-request-body.md"
    $metadataPath = Join-Path $runDir "run.json"

    $runMetadata = [ordered]@{
        task_id = $TaskId
        task_title = $taskTitle
        task_file = $resolvedTaskFile
        repo = $Repo
        base_branch = $BaseBranch
        branch = $BranchName
        run_dir = (Resolve-Path $runDir).Path
        started_at = (Get-Date).ToString("o")
        completed_at = $null
        status = "running"
        validation_commands = @()
        pr_url = $null
        error = $null
    }
    Write-RunMetadata -Metadata $runMetadata -Path $metadataPath

    Invoke-LoggedNative -FilePath git -Arguments @("fetch", "origin", $BaseBranch) -LogPath $commandLog

    $localBase = @(Invoke-GitOutput branch --list $BaseBranch)
    if ($localBase.Count -gt 0) {
        Invoke-LoggedNative -FilePath git -Arguments @("switch", $BaseBranch) -LogPath $commandLog
    }
    else {
        Invoke-LoggedNative -FilePath git -Arguments @("switch", "-c", $BaseBranch, "--track", "origin/$BaseBranch") -LogPath $commandLog
    }

    Invoke-LoggedNative -FilePath git -Arguments @("pull", "--ff-only", "origin", $BaseBranch) -LogPath $commandLog

    $existingBranch = @(Invoke-GitOutput branch --list $BranchName)
    if ($existingBranch.Count -gt 0) {
        Invoke-LoggedNative -FilePath git -Arguments @("switch", $BranchName) -LogPath $commandLog
    }
    else {
        Invoke-LoggedNative -FilePath git -Arguments @("switch", "-c", $BranchName, $BaseBranch) -LogPath $commandLog
    }

    $relativeTaskFile = [System.IO.Path]::GetRelativePath($repoRoot, $resolvedTaskFile)
    $codexPrompt = @"
You are running local automation for Fabian-Hardy/retines-pupilles.

Follow AGENTS.md and keep the work scoped to $TaskId.
Do not commit, push, open a pull request, or change branches. The local runner handles those steps.
Do not modify backend or frontend product code unless the task file explicitly requires it.

Task file: $relativeTaskFile

$taskText
"@

    Invoke-LoggedNative -FilePath codex -Arguments @("exec", "--sandbox", "danger-full-access", "--cd", $repoRoot, "-") -LogPath $codexLog -InputText $codexPrompt

    Invoke-LoggedNative -FilePath git -Arguments @("diff", "--check") -LogPath $commandLog
    $runMetadata.validation_commands += "git diff --check"
    Write-RunMetadata -Metadata $runMetadata -Path $metadataPath

    if ($RunBackendValidation) {
        $backendCommands = @(
            @("compose", "-f", "docker-compose.yml", "-f", "docker-compose.dev.yml", "run", "--rm", "backend", "ruff", "check", "."),
            @("compose", "-f", "docker-compose.yml", "-f", "docker-compose.dev.yml", "run", "--rm", "backend", "mypy", "app", "tests", "--show-traceback"),
            @("compose", "-f", "docker-compose.yml", "-f", "docker-compose.dev.yml", "run", "--rm", "backend", "pytest")
        )

        foreach ($dockerArgs in $backendCommands) {
            Invoke-LoggedNative -FilePath docker -Arguments $dockerArgs -LogPath $backendLog
            $runMetadata.validation_commands += "docker $($dockerArgs -join ' ')"
            Write-RunMetadata -Metadata $runMetadata -Path $metadataPath
        }
    }

    $pendingChanges = @(Invoke-GitOutput status --porcelain)
    if ($pendingChanges.Count -eq 0) {
        throw "Codex completed without producing tracked changes to commit."
    }

    Invoke-LoggedNative -FilePath git -Arguments @("add", "--all") -LogPath $commandLog
    Invoke-LoggedNative -FilePath git -Arguments @("commit", "-m", $CommitMessage) -LogPath $commandLog

    if (-not $SkipPush) {
        Invoke-LoggedNative -FilePath git -Arguments @("push", "-u", "origin", $BranchName) -LogPath $commandLog
    }

    if (-not $SkipPush -and -not $SkipPullRequest) {
        $changedFiles = Get-ChangedFilesForPr -BaseBranchName $BaseBranch
        New-PrBody -Task $TaskId -ChangedFiles $changedFiles -ValidationCommands $runMetadata.validation_commands -BodyPath $prBodyPath

        $existingPr = Invoke-GhCapture -Arguments @("pr", "view", "--repo", $Repo, "--head", $BranchName, "--json", "number,url") -LogPath $commandLog -AllowFailure
        if ($existingPr.ExitCode -eq 0 -and $existingPr.Output) {
            $prData = $existingPr.Output | ConvertFrom-Json
            $runMetadata.pr_url = $prData.url
            Write-Host "Existing PR found: $($prData.url)" -ForegroundColor Green
        }
        else {
            $createdPr = Invoke-GhCapture -Arguments @(
                "pr", "create",
                "--repo", $Repo,
                "--base", $BaseBranch,
                "--head", $BranchName,
                "--draft",
                "--title", $PrTitle,
                "--body-file", $prBodyPath
            ) -LogPath $commandLog
            $runMetadata.pr_url = $createdPr.Output.Trim()
            Write-Host "Draft PR created: $($runMetadata.pr_url)" -ForegroundColor Green
        }
    }

    $runMetadata.status = "completed"
    $runMetadata.completed_at = (Get-Date).ToString("o")
    Write-RunMetadata -Metadata $runMetadata -Path $metadataPath

    Write-Host "Local Codex run completed for $TaskId." -ForegroundColor Green
    Write-Host "Logs: $((Resolve-Path $runDir).Path)"
}
catch {
    if ($null -ne $runMetadata -and $metadataPath) {
        $runMetadata.status = "failed"
        $runMetadata.completed_at = (Get-Date).ToString("o")
        $runMetadata.error = $_.Exception.Message
        Write-RunMetadata -Metadata $runMetadata -Path $metadataPath
    }
    throw
}
finally {
    Set-Location $originalLocation
}
