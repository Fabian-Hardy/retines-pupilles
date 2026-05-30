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

function Assert-CommandAvailable {
    param([string]$Name)

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' was not found in PATH."
    }
}

function Resolve-RepoFile {
    param(
        [string]$Path,
        [string]$RepoRoot
    )

    if ([string]::IsNullOrWhiteSpace($Path)) {
        throw "Missing task file path."
    }

    $candidatePath = if ([System.IO.Path]::IsPathRooted($Path)) {
        $Path
    }
    else {
        Join-Path $RepoRoot $Path
    }

    $resolvedPath = (Resolve-Path -LiteralPath $candidatePath -ErrorAction Stop).Path
    if (-not (Test-Path -LiteralPath $resolvedPath -PathType Leaf)) {
        throw "Task file '$Path' does not resolve to a file."
    }

    return $resolvedPath
}

function Get-RepositoryRelativePath {
    param(
        [string]$RepoRoot,
        [string]$Path
    )

    $separatorChars = @(
        [System.IO.Path]::DirectorySeparatorChar,
        [System.IO.Path]::AltDirectorySeparatorChar
    )
    $rootPath = (Resolve-Path -LiteralPath $RepoRoot).Path.TrimEnd($separatorChars) + [System.IO.Path]::DirectorySeparatorChar
    $fullPath = (Resolve-Path -LiteralPath $Path).Path

    if (-not $fullPath.StartsWith($rootPath, [System.StringComparison]::OrdinalIgnoreCase)) {
        return $fullPath
    }

    $rootUri = [System.Uri]::new($rootPath)
    $pathUri = [System.Uri]::new($fullPath)
    $relativeUri = $rootUri.MakeRelativeUri($pathUri).ToString()
    return [System.Uri]::UnescapeDataString($relativeUri).Replace("/", [System.IO.Path]::DirectorySeparatorChar)
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

function ConvertTo-NativeArgument {
    param([AllowNull()][string]$Value)

    if ($null -eq $Value -or $Value.Length -eq 0) {
        return '""'
    }

    if ($Value -notmatch '[\s"]') {
        return $Value
    }

    $escaped = $Value -replace '(\\*)"', '$1$1\"'
    $escaped = $escaped -replace '(\\+)$', '$1$1'
    return '"' + $escaped + '"'
}

function Format-NativeCommand {
    param(
        [string]$FilePath,
        [string[]]$Arguments
    )

    $formattedArguments = @($Arguments | ForEach-Object { ConvertTo-NativeArgument $_ })
    if ($formattedArguments.Count -eq 0) {
        return $FilePath
    }

    return "$FilePath $($formattedArguments -join ' ')"
}

function Add-LogLine {
    param(
        [string]$Path,
        [string]$Value
    )

    $logDirectory = Split-Path -Parent $Path
    if ($logDirectory -and -not (Test-Path -LiteralPath $logDirectory)) {
        New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null
    }

    Add-Content -LiteralPath $Path -Encoding UTF8 -Value $Value
}

function Copy-LogFile {
    param(
        [string]$SourcePath,
        [string]$DestinationPath,
        [string]$Header
    )

    Add-LogLine -Path $DestinationPath -Value $Header
    if (Test-Path -LiteralPath $SourcePath) {
        Get-Content -LiteralPath $SourcePath -Encoding UTF8 -ErrorAction SilentlyContinue |
            Add-Content -LiteralPath $DestinationPath -Encoding UTF8
    }
}

function Show-LogTail {
    param(
        [string]$Path,
        [int]$LineCount = 80
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        return
    }

    Write-Host ""
    Write-Host "Last $LineCount log lines from ${Path}:" -ForegroundColor Yellow
    foreach ($line in @(Get-Content -LiteralPath $Path -Tail $LineCount -ErrorAction SilentlyContinue)) {
        Write-Host $line
    }
}

function Invoke-LoggedNative {
    param(
        [string]$FilePath,
        [string[]]$Arguments = @(),
        [string]$LogPath,
        [string]$InputText,
        [int]$FailureTailLines = 80
    )

    # File-backed redirection avoids runspace-unsafe stream callbacks.
    $argumentList = @($Arguments)
    $display = Format-NativeCommand -FilePath $FilePath -Arguments $argumentList
    $logDirectory = Split-Path -Parent $LogPath
    if ($logDirectory -and -not (Test-Path -LiteralPath $logDirectory)) {
        New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null
    }

    Write-Host "Running: $display" -ForegroundColor DarkGray
    Write-Host "  log: $LogPath" -ForegroundColor DarkGray
    Add-LogLine -Path $LogPath -Value ""
    Add-LogLine -Path $LogPath -Value ">>> $display"
    Add-LogLine -Path $LogPath -Value "started_at=$((Get-Date).ToString('o'))"

    $streamPrefix = Join-Path $logDirectory ([System.Guid]::NewGuid().ToString("N"))
    $stdoutPath = "$streamPrefix.stdout.log"
    $stderrPath = "$streamPrefix.stderr.log"
    $inputPath = "$streamPrefix.stdin.txt"
    $hasInput = $PSBoundParameters.ContainsKey("InputText")

    if ($hasInput) {
        Set-Content -LiteralPath $inputPath -Encoding UTF8 -NoNewline -Value $InputText
    }

    $startParameters = @{
        FilePath = $FilePath
        WorkingDirectory = (Get-Location).Path
        RedirectStandardOutput = $stdoutPath
        RedirectStandardError = $stderrPath
        NoNewWindow = $true
        Wait = $true
        PassThru = $true
    }

    if ($argumentList.Count -gt 0) {
        $startParameters.ArgumentList = ($argumentList | ForEach-Object { ConvertTo-NativeArgument $_ }) -join " "
    }
    if ($hasInput) {
        $startParameters.RedirectStandardInput = $inputPath
    }

    $process = Start-Process @startParameters
    $exitCode = $process.ExitCode

    Copy-LogFile -SourcePath $stdoutPath -DestinationPath $LogPath -Header "<<< stdout"
    Copy-LogFile -SourcePath $stderrPath -DestinationPath $LogPath -Header "<<< stderr"
    Add-LogLine -Path $LogPath -Value "exit_code=$exitCode"
    Add-LogLine -Path $LogPath -Value "completed_at=$((Get-Date).ToString('o'))"

    foreach ($tempPath in @($stdoutPath, $stderrPath, $inputPath)) {
        if (Test-Path -LiteralPath $tempPath) {
            Remove-Item -LiteralPath $tempPath -Force
        }
    }

    if ($exitCode -ne 0) {
        Show-LogTail -Path $LogPath -LineCount $FailureTailLines
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

    $display = Format-NativeCommand -FilePath "gh" -Arguments @($Arguments)
    Write-Host "Running: $display" -ForegroundColor DarkGray
    Write-Host "  log: $LogPath" -ForegroundColor DarkGray
    Add-LogLine -Path $LogPath -Value ""
    Add-LogLine -Path $LogPath -Value ">>> $display"

    $output = @(& gh @Arguments 2>&1)
    $exitCode = $LASTEXITCODE
    if ($output.Count -gt 0) {
        foreach ($line in $output) {
            Add-LogLine -Path $LogPath -Value $line.ToString()
        }
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

    $metadataDirectory = Split-Path -Parent $Path
    if ($metadataDirectory -and -not (Test-Path -LiteralPath $metadataDirectory)) {
        New-Item -ItemType Directory -Force -Path $metadataDirectory | Out-Null
    }

    $Metadata | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $Path -Encoding UTF8
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

    $validationList = @($ValidationCommands)
    $validations = if ($validationList.Count -gt 0) {
        ($validationList | ForEach-Object { "- ``$_``" }) -join "`n"
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

    $body | Set-Content -LiteralPath $BodyPath -Encoding UTF8
}

$originalLocation = Get-Location
$repoRoot = Get-RepoRoot
$runMetadata = $null
$metadataPath = $null

try {
    Set-Location -LiteralPath $repoRoot

    Assert-CommandAvailable git

    $resolvedTaskFile = Resolve-RepoFile -Path $TaskFile -RepoRoot $repoRoot
    $taskText = Get-Content -LiteralPath $resolvedTaskFile -Raw -Encoding UTF8

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
    Assert-CommandAvailable codex
    if (-not $SkipPush -and -not $SkipPullRequest) {
        Assert-CommandAvailable gh
    }
    if ($RunBackendValidation) {
        Assert-CommandAvailable docker
    }

    $runStamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $runRoot = Join-Path $repoRoot ".local-codex\runs"
    $runDir = Join-Path $runRoot "$runStamp-$(ConvertTo-Slug $TaskId)"
    New-Item -ItemType Directory -Force -Path $runDir | Out-Null
    $runDir = (Resolve-Path -LiteralPath $runDir).Path

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
        run_dir = $runDir
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

    $relativeTaskFile = Get-RepositoryRelativePath -RepoRoot $repoRoot -Path $resolvedTaskFile
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

        $existingPr = Invoke-GhCapture -Arguments @(
            "pr", "list",
            "--repo", $Repo,
            "--head", $BranchName,
            "--base", $BaseBranch,
            "--state", "open",
            "--json", "number,url,title",
            "--limit", "1"
        ) -LogPath $commandLog -AllowFailure
        $existingPrList = if ($existingPr.ExitCode -eq 0 -and $existingPr.Output.Trim()) {
            @($existingPr.Output | ConvertFrom-Json)
        }
        else {
            @()
        }

        if ($existingPrList.Count -gt 0) {
            $prData = $existingPrList[0]
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
    Write-Host "Logs: $runDir"
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
