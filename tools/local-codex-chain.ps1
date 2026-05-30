<#
.SYNOPSIS
Run an ordered queue of local Codex tasks.

.DESCRIPTION
TOOL-003 chain orchestrator. DryRun validates and reports the planned queue
without changing branches or running Codex. ExecuteNoMerge runs each task,
validates, commits, pushes, and opens a PR. Autopilot also enables GitHub
auto-merge and waits for the PR to be merged before continuing.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Queue,

    [Parameter(Mandatory = $true)]
    [ValidateSet("DryRun", "ExecuteNoMerge", "Autopilot")]
    [string]$Mode
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$script:RepoFullName = "Fabian-Hardy/retines-pupilles"
$script:FailurePoint = $null
$script:FailedCommand = $null
$script:FailureExitCode = $null
$script:FailureMessage = $null
$script:RunStatus = "running"
$script:TaskResults = @()

function ConvertTo-LineArray {
    param([AllowNull()] $Value)

    if ($null -eq $Value) {
        return @()
    }

    if ($Value -is [string]) {
        return @($Value)
    }

    if ($Value -is [System.Array]) {
        return @($Value)
    }

    if ($Value -is [System.Collections.IEnumerable]) {
        $items = @()
        foreach ($item in $Value) {
            $items += $item
        }
        return @($items)
    }

    return @($Value)
}

function ConvertTo-TextLineArray {
    param([AllowNull()] $Value)

    $items = @(ConvertTo-LineArray -Value $Value)
    $lines = @()
    foreach ($item in $items) {
        if ($null -eq $item) {
            $lines += ""
        }
        else {
            $lines += $item.ToString()
        }
    }
    return @($lines)
}

function Get-RepoRoot {
    $scriptRoot = Split-Path -Parent $PSCommandPath
    return (Resolve-Path (Join-Path $scriptRoot "..")).Path
}

function Get-DisplayPath {
    param(
        [string]$RepoRoot,
        [string]$Path
    )

    $trimChars = @([char]92, [char]47)
    $root = [System.IO.Path]::GetFullPath($RepoRoot).TrimEnd($trimChars)
    $full = [System.IO.Path]::GetFullPath($Path)

    if ($full.StartsWith($root, [System.StringComparison]::OrdinalIgnoreCase)) {
        $relative = $full.Substring($root.Length).TrimStart($trimChars)
        if ([string]::IsNullOrWhiteSpace($relative)) {
            return "."
        }
        return ($relative -replace "\\", "/")
    }

    return $full
}

function Resolve-RepoPath {
    param(
        [string]$RepoRoot,
        [string]$Path
    )

    if ([System.IO.Path]::IsPathRooted($Path)) {
        return [System.IO.Path]::GetFullPath($Path)
    }

    return [System.IO.Path]::GetFullPath((Join-Path $RepoRoot $Path))
}

function Test-JsonProperty {
    param(
        [object]$Object,
        [string]$Name
    )

    return ($null -ne $Object -and $null -ne $Object.PSObject.Properties[$Name])
}

function Get-RequiredJsonProperty {
    param(
        [object]$Object,
        [string]$Name,
        [string]$Context
    )

    if (-not (Test-JsonProperty -Object $Object -Name $Name)) {
        throw "$Context is missing required property '$Name'."
    }

    return $Object.PSObject.Properties[$Name].Value
}

function Get-OptionalJsonProperty {
    param(
        [object]$Object,
        [string]$Name,
        [AllowNull()]$DefaultValue
    )

    if (-not (Test-JsonProperty -Object $Object -Name $Name)) {
        return $DefaultValue
    }

    return $Object.PSObject.Properties[$Name].Value
}

function Read-QueueFile {
    param(
        [string]$RepoRoot,
        [string]$QueuePath
    )

    $resolvedQueuePath = Resolve-RepoPath -RepoRoot $RepoRoot -Path $QueuePath
    if (-not (Test-Path -Path $resolvedQueuePath -PathType Leaf)) {
        throw "Queue file not found: $QueuePath"
    }

    try {
        $queueObject = Get-Content -Path $resolvedQueuePath -Raw -Encoding UTF8 | ConvertFrom-Json -ErrorAction Stop
    }
    catch {
        throw "Queue file is not valid JSON: $QueuePath. $($_.Exception.Message)"
    }

    $version = Get-RequiredJsonProperty -Object $queueObject -Name "version" -Context "Queue"
    if ([int]$version -ne 1) {
        throw "Queue version must be 1."
    }

    $defaultBaseBranch = [string](Get-RequiredJsonProperty -Object $queueObject -Name "defaultBaseBranch" -Context "Queue")
    if ([string]::IsNullOrWhiteSpace($defaultBaseBranch)) {
        throw "Queue defaultBaseBranch must be a non-empty string."
    }

    if (-not (Test-JsonProperty -Object $queueObject -Name "tasks")) {
        throw "Queue is missing required property 'tasks'."
    }

    $rawTasks = @(ConvertTo-LineArray -Value $queueObject.tasks)
    $tasks = @()
    $index = 0
    foreach ($rawTask in $rawTasks) {
        $index += 1
        $context = "Task[$index]"

        $id = [string](Get-RequiredJsonProperty -Object $rawTask -Name "id" -Context $context)
        if ($id -notmatch "^(TASK|TOOL)-\d{3,4}$") {
            throw "$context id must look like TASK-013 or TOOL-003."
        }
        $id = $id.ToUpperInvariant()

        $taskFile = [string](Get-RequiredJsonProperty -Object $rawTask -Name "taskFile" -Context $context)
        if ([string]::IsNullOrWhiteSpace($taskFile)) {
            throw "$context taskFile must be a non-empty string."
        }

        $resolvedTaskFile = Resolve-RepoPath -RepoRoot $RepoRoot -Path $taskFile
        if (-not (Test-Path -Path $resolvedTaskFile -PathType Leaf)) {
            throw "$context taskFile does not exist: $taskFile"
        }

        $branchName = [string](Get-RequiredJsonProperty -Object $rawTask -Name "branchName" -Context $context)
        if ([string]::IsNullOrWhiteSpace($branchName)) {
            throw "$context branchName must be a non-empty string."
        }
        if ($branchName -eq "main" -or $branchName -eq $defaultBaseBranch) {
            throw "$context branchName must not be main or the base branch."
        }

        $title = [string](Get-RequiredJsonProperty -Object $rawTask -Name "title" -Context $context)
        if ([string]::IsNullOrWhiteSpace($title)) {
            throw "$context title must be a non-empty string."
        }

        $rawValidations = @(ConvertTo-LineArray -Value (Get-OptionalJsonProperty -Object $rawTask -Name "validations" -DefaultValue @()))
        $validations = @()
        $validationIndex = 0
        foreach ($rawValidation in $rawValidations) {
            $validationIndex += 1
            $validationContext = "$context validation[$validationIndex]"

            $validationName = [string](Get-RequiredJsonProperty -Object $rawValidation -Name "name" -Context $validationContext)
            if ([string]::IsNullOrWhiteSpace($validationName)) {
                throw "$validationContext name must be a non-empty string."
            }

            $validationCommand = [string](Get-RequiredJsonProperty -Object $rawValidation -Name "command" -Context $validationContext)
            if ([string]::IsNullOrWhiteSpace($validationCommand)) {
                throw "$validationContext command must be a non-empty string."
            }

            $validations += [ordered]@{
                name = $validationName
                command = $validationCommand
            }
        }

        $tasks += [ordered]@{
            id = $id
            taskFile = $taskFile
            resolvedTaskFile = $resolvedTaskFile
            branchName = $branchName
            title = $title
            validations = @($validations)
        }
    }

    return [ordered]@{
        path = $resolvedQueuePath
        version = [int]$version
        defaultBaseBranch = $defaultBaseBranch
        tasks = @($tasks)
    }
}

function Format-CommandText {
    param(
        [string]$FilePath,
        [string[]]$Arguments
    )

    $parts = @($FilePath) + @(ConvertTo-LineArray -Value $Arguments)
    $quoted = @()
    foreach ($part in $parts) {
        $text = [string]$part
        if ($text -match "\s") {
            $quoted += "'" + ($text -replace "'", "''") + "'"
        }
        else {
            $quoted += $text
        }
    }

    return ($quoted -join " ")
}

function Invoke-ExternalCommand {
    param(
        [string]$FilePath,
        [string[]]$Arguments = @()
    )

    $display = Format-CommandText -FilePath $FilePath -Arguments $Arguments
    Write-Host ">>> $display" -ForegroundColor DarkGray

    $output = @()
    $exitCode = 0
    $success = $true

    try {
        $rawOutput = & $FilePath @Arguments 2>&1
        $success = $?
        if ($null -ne $LASTEXITCODE) {
            $exitCode = [int]$LASTEXITCODE
        }
        elseif (-not $success) {
            $exitCode = 1
        }
        $output = @(ConvertTo-TextLineArray -Value $rawOutput)
    }
    catch {
        $success = $false
        $exitCode = 1
        $output = @($_.Exception.Message)
    }

    if (-not $success -and $exitCode -eq 0) {
        $exitCode = 1
    }

    return [pscustomobject]@{
        Command = $display
        ExitCode = $exitCode
        Output = @($output)
    }
}

function Stop-Chain {
    param(
        [string]$Message,
        [string]$Point,
        [AllowNull()][string]$Command,
        [AllowNull()][int]$ExitCode,
        [AllowNull()]$TaskResult
    )

    $script:RunStatus = "failed"
    $script:FailureMessage = $Message
    $script:FailurePoint = $Point
    $script:FailedCommand = $Command
    $script:FailureExitCode = $ExitCode

    if ($null -ne $TaskResult) {
        $TaskResult.status = "failed"
        $TaskResult.failurePoint = $Point
        $TaskResult.failedCommand = $Command
        $TaskResult.exitCode = $ExitCode
    }

    throw $Message
}

function Assert-CommandSucceeded {
    param(
        [object]$Result,
        [string]$Point,
        [AllowNull()]$TaskResult
    )

    if ([int]$Result.ExitCode -ne 0) {
        $message = "$Point failed with exit code $($Result.ExitCode)."
        Stop-Chain -Message $message -Point $Point -Command $Result.Command -ExitCode ([int]$Result.ExitCode) -TaskResult $TaskResult
    }
}

function Get-GitHash {
    $result = Invoke-ExternalCommand -FilePath "git" -Arguments @("rev-parse", "HEAD")
    if ([int]$result.ExitCode -ne 0) {
        return $null
    }

    $lines = @(ConvertTo-LineArray -Value $result.Output)
    if ($lines.Count -eq 0) {
        return $null
    }

    return [string]$lines[0]
}

function Assert-CleanGitStatus {
    param([AllowNull()]$TaskResult)

    $result = Invoke-ExternalCommand -FilePath "git" -Arguments @("status", "--short")
    Assert-CommandSucceeded -Result $result -Point "git status" -TaskResult $TaskResult

    $lines = @(ConvertTo-LineArray -Value $result.Output | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    if ($lines.Count -gt 0) {
        Stop-Chain -Message "Working tree is dirty at the start of the task." -Point "clean working tree check" -Command $result.Command -ExitCode 1 -TaskResult $TaskResult
    }
}

function Test-LocalBranchExists {
    param([string]$BranchName)

    $result = Invoke-ExternalCommand -FilePath "git" -Arguments @("show-ref", "--verify", "--quiet", "refs/heads/$BranchName")
    return ([int]$result.ExitCode -eq 0)
}

function Test-RemoteBranchExists {
    param([string]$BranchName)

    $result = Invoke-ExternalCommand -FilePath "git" -Arguments @("ls-remote", "--exit-code", "--heads", "origin", $BranchName)
    return ([int]$result.ExitCode -eq 0)
}

function Switch-TaskBranch {
    param(
        [string]$BaseBranch,
        [string]$BranchName,
        [AllowNull()]$TaskResult
    )

    if (Test-LocalBranchExists -BranchName $BranchName) {
        $switchResult = Invoke-ExternalCommand -FilePath "git" -Arguments @("switch", $BranchName)
        Assert-CommandSucceeded -Result $switchResult -Point "switch feature branch" -TaskResult $TaskResult
        return
    }

    if (Test-RemoteBranchExists -BranchName $BranchName) {
        $trackResult = Invoke-ExternalCommand -FilePath "git" -Arguments @("switch", "--track", "-c", $BranchName, "origin/$BranchName")
        Assert-CommandSucceeded -Result $trackResult -Point "switch remote feature branch" -TaskResult $TaskResult
        return
    }

    $createResult = Invoke-ExternalCommand -FilePath "git" -Arguments @("switch", "-c", $BranchName, $BaseBranch)
    Assert-CommandSucceeded -Result $createResult -Point "create feature branch" -TaskResult $TaskResult
}

function Get-ChangedPaths {
    param([AllowNull()]$TaskResult)

    $result = Invoke-ExternalCommand -FilePath "git" -Arguments @("status", "--short")
    Assert-CommandSucceeded -Result $result -Point "changed file inspection" -TaskResult $TaskResult

    $paths = @()
    $lines = @(ConvertTo-LineArray -Value $result.Output)
    foreach ($line in $lines) {
        $text = [string]$line
        if ($text.Length -lt 4) {
            continue
        }

        $pathText = $text.Substring(3).Trim()
        if ([string]::IsNullOrWhiteSpace($pathText)) {
            continue
        }

        if ($pathText -match " -> ") {
            $parts = @($pathText -split "\s+->\s+")
            foreach ($part in $parts) {
                if (-not [string]::IsNullOrWhiteSpace($part)) {
                    $paths += $part
                }
            }
        }
        else {
            $paths += $pathText
        }
    }

    return @($paths | Select-Object -Unique)
}

function Assert-NoSensitivePaths {
    param(
        [string[]]$Paths,
        [AllowNull()]$TaskResult
    )

    $suspicious = @()
    foreach ($path in @(ConvertTo-LineArray -Value $Paths)) {
        $normalized = ([string]$path) -replace "\\", "/"
        $leaf = [System.IO.Path]::GetFileName($normalized)
        if (
            $leaf -eq ".env" -or
            $leaf -like ".env.*" -or
            $leaf -like "*.pem" -or
            $leaf -like "*.key" -or
            $normalized -match "(?i)secret" -or
            $normalized -match "(?i)credential"
        ) {
            $suspicious += $path
        }
    }

    $suspiciousPaths = @(ConvertTo-LineArray -Value ($suspicious | Select-Object -Unique))
    if ($suspiciousPaths.Count -gt 0) {
        $message = "Refusing to commit because suspicious secret-related paths changed: $($suspiciousPaths -join ', ')"
        Stop-Chain -Message $message -Point "secret guard" -Command "git status --short" -ExitCode 1 -TaskResult $TaskResult
    }
}

function Get-IntOrZero {
    param([string]$Value)

    $parsed = 0
    if ([int]::TryParse($Value, [ref]$parsed)) {
        return $parsed
    }

    return 0
}

function Assert-NoMassiveDeletion {
    param([AllowNull()]$TaskResult)

    # Conservative thresholds: ordinary scoped tasks should not delete more than
    # 20 files or 1500 lines, nor be overwhelmingly deletion-heavy.
    $maxDeletedFiles = 20
    $maxDeletedLines = 1500
    $ratioDeletedLines = 8
    $ratioFloorDeletedLines = 500

    $numstatResult = Invoke-ExternalCommand -FilePath "git" -Arguments @("diff", "--numstat", "HEAD", "--")
    Assert-CommandSucceeded -Result $numstatResult -Point "diff deletion guard" -TaskResult $TaskResult

    $insertedLines = 0
    $deletedLines = 0
    $numstatLines = @(ConvertTo-LineArray -Value $numstatResult.Output)
    foreach ($line in $numstatLines) {
        $parts = @(([string]$line) -split "`t")
        if ($parts.Count -lt 3) {
            continue
        }

        $insertedLines += Get-IntOrZero -Value $parts[0]
        $deletedLines += Get-IntOrZero -Value $parts[1]
    }

    $statusResult = Invoke-ExternalCommand -FilePath "git" -Arguments @("status", "--short")
    Assert-CommandSucceeded -Result $statusResult -Point "deleted file guard" -TaskResult $TaskResult

    $deletedFiles = 0
    $statusLines = @(ConvertTo-LineArray -Value $statusResult.Output)
    foreach ($line in $statusLines) {
        $text = [string]$line
        if ($text.Length -ge 2 -and $text.Substring(0, 2).Contains("D")) {
            $deletedFiles += 1
        }
    }

    $ratioExceeded = ($deletedLines -gt $ratioFloorDeletedLines -and $deletedLines -gt (($insertedLines + 1) * $ratioDeletedLines))
    if ($deletedFiles -gt $maxDeletedFiles -or $deletedLines -gt $maxDeletedLines -or $ratioExceeded) {
        $message = "Refusing to commit because deletion volume is abnormal: $deletedFiles files, $deletedLines deleted lines."
        Stop-Chain -Message $message -Point "mass deletion guard" -Command $numstatResult.Command -ExitCode 1 -TaskResult $TaskResult
    }
}

function Assert-NoDestructiveMigration {
    param(
        [string]$RepoRoot,
        [string[]]$Paths,
        [AllowNull()]$TaskResult
    )

    $destructivePattern = "(?im)\bDROP\s+TABLE\b|\bDROP\s+COLUMN\b|\bTRUNCATE\b|\bDELETE\s+FROM\b"
    foreach ($path in @(ConvertTo-LineArray -Value $Paths)) {
        $normalized = ([string]$path) -replace "\\", "/"
        $isMigrationPath = (
            $normalized -match "(?i)(^|/)migrations?(/|$)" -or
            $normalized -match "(?i)(^|/)alembic(/|$)" -or
            $normalized -match "(?i)(^|/)versions(/|$)" -or
            $normalized -match "(?i)\.sql$"
        )

        if (-not $isMigrationPath) {
            continue
        }

        $fullPath = Resolve-RepoPath -RepoRoot $RepoRoot -Path $path
        if (-not (Test-Path -Path $fullPath -PathType Leaf)) {
            continue
        }

        $content = Get-Content -Path $fullPath -Raw -Encoding UTF8
        if ($content -match $destructivePattern) {
            $message = "Refusing to commit because a migration or SQL file contains a destructive statement: $path"
            Stop-Chain -Message $message -Point "destructive migration guard" -Command "scan changed migration and SQL files" -ExitCode 1 -TaskResult $TaskResult
        }
    }
}

function Assert-GuardRails {
    param(
        [string]$RepoRoot,
        [AllowNull()]$TaskResult
    )

    $diffCheck = Invoke-ExternalCommand -FilePath "git" -Arguments @("diff", "--check")
    Assert-CommandSucceeded -Result $diffCheck -Point "git diff --check" -TaskResult $TaskResult

    $changedPaths = @(Get-ChangedPaths -TaskResult $TaskResult)
    if ($changedPaths.Count -eq 0) {
        Stop-Chain -Message "Runner completed without producing changes to commit." -Point "git change check" -Command "git status --short" -ExitCode 1 -TaskResult $TaskResult
    }

    Assert-NoSensitivePaths -Paths $changedPaths -TaskResult $TaskResult
    Assert-NoMassiveDeletion -TaskResult $TaskResult
    Assert-NoDestructiveMigration -RepoRoot $RepoRoot -Paths $changedPaths -TaskResult $TaskResult
}

function Invoke-ValidationCommand {
    param(
        [string]$Command,
        [AllowNull()]$TaskResult
    )

    $arguments = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $Command)
    $result = Invoke-ExternalCommand -FilePath "powershell" -Arguments $arguments
    Assert-CommandSucceeded -Result $result -Point "validation command" -TaskResult $TaskResult
    return $result
}

function Get-ChangedFilesForPr {
    param(
        [string]$BaseBranch,
        [AllowNull()]$TaskResult
    )

    $result = Invoke-ExternalCommand -FilePath "git" -Arguments @("diff", "--name-only", "$BaseBranch...HEAD")
    Assert-CommandSucceeded -Result $result -Point "PR changed files" -TaskResult $TaskResult

    $files = @(ConvertTo-LineArray -Value $result.Output | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    if ($files.Count -eq 0) {
        return "- No changed files detected."
    }

    return (($files | ForEach-Object { "- $_" }) -join "`n")
}

function New-PullRequestBody {
    param(
        [object]$Task,
        [string]$ChangedFiles,
        [array]$Validations,
        [string]$Mode
    )

    $validationLines = @()
    foreach ($validation in @(ConvertTo-LineArray -Value $Validations)) {
        $validationLines += "- $($validation.name): ``$($validation.command)``"
    }
    if ($validationLines.Count -eq 0) {
        $validationLines += "- No local validation commands were defined in the queue."
    }

    return @"
## Task id
$($Task.id)

## Summary
- Local Codex chain runner completed $($Task.id) in $Mode mode.

## Changed files or areas
$ChangedFiles

## Validation commands run
$($validationLines -join "`n")

## Known limitations
- Review GitHub CI and the generated chain report before merging unless Autopilot has already enabled auto-merge.

## Follow-up work
- None identified by the chain runner.
"@
}

function Get-OrCreatePullRequest {
    param(
        [object]$Task,
        [string]$BaseBranch,
        [string]$Body,
        [AllowNull()]$TaskResult
    )

    $existingResult = Invoke-ExternalCommand -FilePath "gh" -Arguments @("pr", "view", "--repo", $script:RepoFullName, "--head", $Task.branchName, "--json", "number,url")
    if ([int]$existingResult.ExitCode -eq 0) {
        $json = ((@(ConvertTo-LineArray -Value $existingResult.Output)) -join "`n").Trim()
        if (-not [string]::IsNullOrWhiteSpace($json)) {
            $data = $json | ConvertFrom-Json
            return [pscustomobject]@{
                Number = [int]$data.number
                Url = [string]$data.url
                Created = $false
            }
        }
    }

    $createResult = Invoke-ExternalCommand -FilePath "gh" -Arguments @(
        "pr", "create",
        "--repo", $script:RepoFullName,
        "--base", $BaseBranch,
        "--head", $Task.branchName,
        "--title", "$($Task.id): $($Task.title)",
        "--body", $Body
    )
    Assert-CommandSucceeded -Result $createResult -Point "create pull request" -TaskResult $TaskResult

    $url = ((@(ConvertTo-LineArray -Value $createResult.Output)) -join "`n").Trim()
    if ([string]::IsNullOrWhiteSpace($url)) {
        Stop-Chain -Message "gh pr create did not return a PR URL." -Point "create pull request" -Command $createResult.Command -ExitCode 1 -TaskResult $TaskResult
    }

    $viewResult = Invoke-ExternalCommand -FilePath "gh" -Arguments @("pr", "view", $url, "--repo", $script:RepoFullName, "--json", "number,url")
    Assert-CommandSucceeded -Result $viewResult -Point "read created pull request" -TaskResult $TaskResult
    $viewJson = ((@(ConvertTo-LineArray -Value $viewResult.Output)) -join "`n").Trim()
    $viewData = $viewJson | ConvertFrom-Json

    return [pscustomobject]@{
        Number = [int]$viewData.number
        Url = [string]$viewData.url
        Created = $true
    }
}

function Get-CheckRollupState {
    param([AllowNull()]$Rollup)

    $items = @(ConvertTo-LineArray -Value $Rollup)
    if ($items.Count -eq 0) {
        return "none"
    }

    $hasPending = $false
    foreach ($item in $items) {
        $values = @()
        foreach ($propertyName in @("conclusion", "status", "state")) {
            if (Test-JsonProperty -Object $item -Name $propertyName) {
                $value = [string]$item.PSObject.Properties[$propertyName].Value
                if (-not [string]::IsNullOrWhiteSpace($value)) {
                    $values += $value.ToUpperInvariant()
                }
            }
        }

        foreach ($value in $values) {
            if ($value -in @("FAILURE", "FAILED", "ERROR", "CANCELLED", "TIMED_OUT", "ACTION_REQUIRED")) {
                return "red"
            }
            if ($value -in @("PENDING", "QUEUED", "IN_PROGRESS", "REQUESTED", "WAITING", "EXPECTED")) {
                $hasPending = $true
            }
        }
    }

    if ($hasPending) {
        return "pending"
    }

    return "green"
}

function Get-PullRequestState {
    param(
        [int]$PrNumber,
        [AllowNull()]$TaskResult
    )

    $result = Invoke-ExternalCommand -FilePath "gh" -Arguments @("pr", "view", "$PrNumber", "--repo", $script:RepoFullName, "--json", "number,url,state,mergedAt,mergeStateStatus,statusCheckRollup")
    Assert-CommandSucceeded -Result $result -Point "read pull request state" -TaskResult $TaskResult

    $json = ((@(ConvertTo-LineArray -Value $result.Output)) -join "`n").Trim()
    if ([string]::IsNullOrWhiteSpace($json)) {
        Stop-Chain -Message "gh pr view returned no JSON for PR #$PrNumber." -Point "read pull request state" -Command $result.Command -ExitCode 1 -TaskResult $TaskResult
    }

    return ($json | ConvertFrom-Json)
}

function Assert-PullRequestCiNotRed {
    param(
        [int]$PrNumber,
        [AllowNull()]$TaskResult
    )

    $state = Get-PullRequestState -PrNumber $PrNumber -TaskResult $TaskResult
    $ciState = Get-CheckRollupState -Rollup $state.statusCheckRollup
    if ($ciState -eq "red") {
        Stop-Chain -Message "Refusing auto-merge because CI is red for PR #$PrNumber." -Point "CI guard" -Command "gh pr view $PrNumber --json statusCheckRollup" -ExitCode 1 -TaskResult $TaskResult
    }
}

function Enable-AutoMergeAndWait {
    param(
        [int]$PrNumber,
        [AllowNull()]$TaskResult
    )

    Assert-PullRequestCiNotRed -PrNumber $PrNumber -TaskResult $TaskResult

    $mergeResult = Invoke-ExternalCommand -FilePath "gh" -Arguments @("pr", "merge", "$PrNumber", "--repo", $script:RepoFullName, "--auto", "--squash", "--delete-branch")
    Assert-CommandSucceeded -Result $mergeResult -Point "enable auto-merge" -TaskResult $TaskResult

    $deadline = (Get-Date).AddMinutes(60)
    while ((Get-Date) -lt $deadline) {
        $state = Get-PullRequestState -PrNumber $PrNumber -TaskResult $TaskResult
        if (-not [string]::IsNullOrWhiteSpace([string]$state.mergedAt)) {
            return
        }

        $ciState = Get-CheckRollupState -Rollup $state.statusCheckRollup
        if ($ciState -eq "red") {
            Stop-Chain -Message "Stopping because CI became red while waiting for PR #$PrNumber." -Point "CI wait guard" -Command "gh pr view $PrNumber --json statusCheckRollup" -ExitCode 1 -TaskResult $TaskResult
        }

        Start-Sleep -Seconds 30
    }

    Stop-Chain -Message "PR #$PrNumber was not merged within 60 minutes." -Point "wait for merge" -Command "gh pr view $PrNumber" -ExitCode 1 -TaskResult $TaskResult
}

function Invoke-Task {
    param(
        [string]$RepoRoot,
        [object]$Task,
        [string]$BaseBranch,
        [string]$Mode
    )

    $taskResult = [ordered]@{
        id = $Task.id
        title = $Task.title
        branch = $Task.branchName
        status = "running"
        pr = $null
        validations = @()
        failurePoint = $null
        failedCommand = $null
        exitCode = $null
    }
    $script:TaskResults += $taskResult

    Assert-CleanGitStatus -TaskResult $taskResult

    $switchBase = Invoke-ExternalCommand -FilePath "git" -Arguments @("switch", $BaseBranch)
    Assert-CommandSucceeded -Result $switchBase -Point "switch base branch" -TaskResult $taskResult

    $pullBase = Invoke-ExternalCommand -FilePath "git" -Arguments @("pull", "--ff-only", "origin", $BaseBranch)
    Assert-CommandSucceeded -Result $pullBase -Point "pull base branch" -TaskResult $taskResult

    Switch-TaskBranch -BaseBranch $BaseBranch -BranchName $Task.branchName -TaskResult $taskResult

    $runnerPath = Join-Path $RepoRoot "tools/local-codex-runner.ps1"
    $runnerArgs = @(
        "run-task",
        $Task.taskFile,
        "-TaskId", $Task.id,
        "-BranchName", $Task.branchName,
        "-BaseBranch", $BaseBranch,
        "-SkipCommit",
        "-SkipPush",
        "-SkipPullRequest"
    )
    $runnerResult = Invoke-ExternalCommand -FilePath $runnerPath -Arguments $runnerArgs
    Assert-CommandSucceeded -Result $runnerResult -Point "local Codex runner" -TaskResult $taskResult

    foreach ($validation in @(ConvertTo-LineArray -Value $Task.validations)) {
        $validationRecord = [ordered]@{
            name = $validation.name
            command = $validation.command
            status = "running"
            exitCode = $null
        }
        $taskResult.validations += $validationRecord

        $validationResult = Invoke-ValidationCommand -Command $validation.command -TaskResult $taskResult
        $validationRecord.status = "passed"
        $validationRecord.exitCode = [int]$validationResult.ExitCode
    }

    Assert-GuardRails -RepoRoot $RepoRoot -TaskResult $taskResult

    $addResult = Invoke-ExternalCommand -FilePath "git" -Arguments @("add", "--all")
    Assert-CommandSucceeded -Result $addResult -Point "stage changes" -TaskResult $taskResult

    $commitMessage = "$($Task.id): $($Task.title)"
    $commitResult = Invoke-ExternalCommand -FilePath "git" -Arguments @("commit", "-m", $commitMessage)
    Assert-CommandSucceeded -Result $commitResult -Point "commit changes" -TaskResult $taskResult

    $pushResult = Invoke-ExternalCommand -FilePath "git" -Arguments @("push", "-u", "origin", $Task.branchName)
    Assert-CommandSucceeded -Result $pushResult -Point "push branch" -TaskResult $taskResult

    $changedFiles = Get-ChangedFilesForPr -BaseBranch $BaseBranch -TaskResult $taskResult
    $prBody = New-PullRequestBody -Task $Task -ChangedFiles $changedFiles -Validations $Task.validations -Mode $Mode
    $pr = Get-OrCreatePullRequest -Task $Task -BaseBranch $BaseBranch -Body $prBody -TaskResult $taskResult
    $taskResult.pr = $pr.Url

    if ($Mode -eq "Autopilot") {
        Enable-AutoMergeAndWait -PrNumber $pr.Number -TaskResult $taskResult

        $switchDevelop = Invoke-ExternalCommand -FilePath "git" -Arguments @("switch", $BaseBranch)
        Assert-CommandSucceeded -Result $switchDevelop -Point "return to base branch" -TaskResult $taskResult

        $pullDevelop = Invoke-ExternalCommand -FilePath "git" -Arguments @("pull", "--ff-only", "origin", $BaseBranch)
        Assert-CommandSucceeded -Result $pullDevelop -Point "resync base branch" -TaskResult $taskResult
    }

    $taskResult.status = "completed"
}

function Invoke-DryRun {
    param(
        [object]$QueueData,
        [string]$RepoRoot
    )

    $tasks = @(ConvertTo-LineArray -Value $QueueData.tasks)
    Write-Host "DryRun queue: $(Get-DisplayPath -RepoRoot $RepoRoot -Path $QueueData.path)"
    Write-Host "Base branch: $($QueueData.defaultBaseBranch)"
    Write-Host "Task count: $($tasks.Count)"

    if ($tasks.Count -eq 0) {
        Write-Host "No tasks are currently queued."
        return
    }

    foreach ($task in $tasks) {
        $taskResult = [ordered]@{
            id = $task.id
            title = $task.title
            branch = $task.branchName
            status = "planned"
            pr = $null
            validations = @()
            failurePoint = $null
            failedCommand = $null
            exitCode = $null
        }
        foreach ($validation in @(ConvertTo-LineArray -Value $task.validations)) {
            $taskResult.validations += [ordered]@{
                name = $validation.name
                command = $validation.command
                status = "planned"
                exitCode = $null
            }
        }
        $script:TaskResults += $taskResult

        Write-Host ""
        Write-Host "Task $($task.id): $($task.title)"
        Write-Host "  branch: $($task.branchName)"
        Write-Host "  task file: $(Get-DisplayPath -RepoRoot $RepoRoot -Path $task.resolvedTaskFile)"
        Write-Host "  would: check git status, update $($QueueData.defaultBaseBranch), switch/create branch"
        Write-Host "  would: run tools/local-codex-runner.ps1 run-task with -SkipCommit -SkipPush -SkipPullRequest"
        Write-Host "  would: run validations, guard checks, commit, push, and create PR"
        if ($Mode -eq "Autopilot") {
            Write-Host "  would: enable GitHub auto-merge and wait for merge"
        }
    }
}

function Write-Report {
    param(
        [string]$ReportPath,
        [string]$Mode,
        [AllowNull()][string]$QueuePath,
        [AllowNull()][string]$InitialHash,
        [AllowNull()][string]$FinalHash,
        [string]$Status,
        [AllowNull()][string]$Summary
    )

    $lines = @()
    $lines += "# Local Codex Chain Report"
    $lines += ""
    $lines += "- Mode: $Mode"
    $lines += "- Queue: $QueuePath"
    $lines += "- Initial git hash: $InitialHash"
    $lines += "- Final git hash: $FinalHash"
    $lines += "- Status: $Status"
    if (-not [string]::IsNullOrWhiteSpace($script:FailurePoint)) {
        $lines += "- Failure point: $script:FailurePoint"
    }
    if (-not [string]::IsNullOrWhiteSpace($script:FailedCommand)) {
        $lines += "- Failed command: ``$script:FailedCommand``"
    }
    if ($null -ne $script:FailureExitCode) {
        $lines += "- Exit code: $script:FailureExitCode"
    }
    if (-not [string]::IsNullOrWhiteSpace($Summary)) {
        $lines += "- Summary: $Summary"
    }

    $lines += ""
    $lines += "## Tasks"
    $taskResults = @(ConvertTo-LineArray -Value $script:TaskResults)
    if ($taskResults.Count -eq 0) {
        $lines += "- No tasks processed."
    }
    else {
        foreach ($task in $taskResults) {
            $lines += ""
            $lines += "### $($task.id)"
            $lines += "- Status: $($task.status)"
            $lines += "- Branch: $($task.branch)"
            if (-not [string]::IsNullOrWhiteSpace([string]$task.pr)) {
                $lines += "- PR: $($task.pr)"
            }
            if (-not [string]::IsNullOrWhiteSpace([string]$task.failurePoint)) {
                $lines += "- Failure point: $($task.failurePoint)"
            }
            if (-not [string]::IsNullOrWhiteSpace([string]$task.failedCommand)) {
                $lines += "- Failed command: ``$($task.failedCommand)``"
            }
            if ($null -ne $task.exitCode) {
                $lines += "- Exit code: $($task.exitCode)"
            }

            $validations = @(ConvertTo-LineArray -Value $task.validations)
            if ($validations.Count -gt 0) {
                $lines += "- Validations:"
                foreach ($validation in $validations) {
                    $validationExit = ""
                    if ($null -ne $validation.exitCode) {
                        $validationExit = " (exit $($validation.exitCode))"
                    }
                    $lines += "  - $($validation.status): $($validation.name) - ``$($validation.command)``$validationExit"
                }
            }
        }
    }

    $reportDirectory = Split-Path -Parent $ReportPath
    if (-not (Test-Path -Path $reportDirectory)) {
        New-Item -ItemType Directory -Force -Path $reportDirectory | Out-Null
    }

    $lines -join "`n" | Set-Content -Path $ReportPath -Encoding UTF8
}

function New-ReportPath {
    param([string]$RepoRoot)

    $reportRoot = Join-Path $RepoRoot "_reports"
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $path = Join-Path $reportRoot "local-codex-chain-$stamp.md"
    $index = 2
    while (Test-Path -Path $path) {
        $path = Join-Path $reportRoot ("local-codex-chain-$stamp-{0:D2}.md" -f $index)
        $index += 1
    }

    return $path
}

$repoRoot = Get-RepoRoot
$originalLocation = Get-Location
$reportPath = New-ReportPath -RepoRoot $repoRoot
$initialHash = $null
$finalHash = $null
$queueData = $null
$resolvedQueueDisplay = $Queue

try {
    Set-Location $repoRoot

    $initialHash = Get-GitHash
    $queueData = Read-QueueFile -RepoRoot $repoRoot -QueuePath $Queue
    $resolvedQueueDisplay = Get-DisplayPath -RepoRoot $repoRoot -Path $queueData.path

    if ($Mode -eq "DryRun") {
        Invoke-DryRun -QueueData $queueData -RepoRoot $repoRoot
    }
    else {
        foreach ($tool in @("git", "gh", "powershell")) {
            if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
                Stop-Chain -Message "Required command '$tool' was not found in PATH." -Point "tool availability" -Command "Get-Command $tool" -ExitCode 1 -TaskResult $null
            }
        }

        $tasks = @(ConvertTo-LineArray -Value $queueData.tasks)
        foreach ($task in $tasks) {
            Invoke-Task -RepoRoot $repoRoot -Task $task -BaseBranch $queueData.defaultBaseBranch -Mode $Mode
        }
    }

    $script:RunStatus = "completed"
    $script:FailureMessage = $null
}
catch {
    if ($script:RunStatus -ne "failed") {
        $script:RunStatus = "failed"
        $script:FailureMessage = $_.Exception.Message
        if ([string]::IsNullOrWhiteSpace($script:FailurePoint)) {
            $script:FailurePoint = "unhandled exception"
        }
    }
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
}
finally {
    try {
        $finalHash = Get-GitHash
    }
    catch {
        $finalHash = $null
    }

    Write-Report `
        -ReportPath $reportPath `
        -Mode $Mode `
        -QueuePath $resolvedQueueDisplay `
        -InitialHash $initialHash `
        -FinalHash $finalHash `
        -Status $script:RunStatus `
        -Summary $script:FailureMessage

    Write-Host "Report: $(Get-DisplayPath -RepoRoot $repoRoot -Path $reportPath)"
    Set-Location $originalLocation
}

if ($script:RunStatus -ne "completed") {
    exit 1
}
