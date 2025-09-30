<#
PowerShell helper script: remove_large_history.ps1
Purpose: mirror-clone the repo, remove specified large files from history using git-filter-repo,
perform cleanup, and force-push the rewritten history back to origin.

USAGE:
- Review the variables below (especially $RepoUrl).
- Run from an elevated PowerShell / Developer PowerShell where `git` and `python` are available.
- The script will create a temporary mirror clone under $TempDir, create a backup bundle, run git-filter-repo,
  and require interactive confirmation before force-pushing the cleaned mirror.

WARNING: This rewrites history and requires a force-push. All collaborators must re-clone or reset.
#>

param(
    [string]$RepoUrl = 'https://github.com/windprince/agents.git',
    [int]$MaxBlobSizeMB = 10,
    [string[]]$ExcludeExtensions = @('db','sqlite','sqlite3','db-journal'),
    [switch]$AutoConfirm,
    [switch]$RewriteOnly
)

# ----- CONFIGURE -----
$TempDir = Join-Path -Path $env:TEMP -ChildPath ("agents-filter-{0}" -f (Get-Date -Format yyyyMMddHHmmss))
$MirrorDir = Join-Path $TempDir 'agents.git'
$BackupBundle = Join-Path $TempDir 'agents-backup.bundle'
# Specific known paths to remove (keeps backward-compatibility)
$PathsToRemove = @(
    'CRO_file_analysis/Study_archive/Studies_archive_CSV.csv',
    'CRO_file_analysis/Study_archive/study_archive.db'
)
# If you want to remove all large blobs above $MaxBlobSizeMB and/or remove files with certain extensions,
# tweak the script parameters when invoking the script (see usage below).
# ---------------------

function Abort($msg){ Write-Host "ERROR: $msg" -ForegroundColor Red; exit 1 }

Write-Host "Temporary workspace: $TempDir" -ForegroundColor Cyan

# Basic checks
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Abort 'git not found in PATH. Install Git and try again.' }
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { Write-Warning 'python not found in PATH. git-filter-repo may not be installable automatically.' }

# Create temp dir
New-Item -Path $TempDir -ItemType Directory -Force | Out-Null
Set-Location -Path $TempDir

Write-Host "Cloning mirror of $RepoUrl into $MirrorDir ..." -ForegroundColor Yellow
git clone --mirror $RepoUrl $MirrorDir 2>&1 | Write-Host
if ($LASTEXITCODE -ne 0) { Abort 'git clone --mirror failed' }

Set-Location -Path $MirrorDir

# Create a backup bundle before rewriting
Write-Host "Creating a backup bundle at $BackupBundle ..." -ForegroundColor Yellow
git bundle create $BackupBundle --all 2>&1 | Write-Host
if ($LASTEXITCODE -ne 0) { Write-Warning 'git bundle creation failed; you may still proceed but having a bundle backup is recommended.' }

# Ensure git-filter-repo is available; install via pip if python/pip present
$filterRepoCmd = 'git-filter-repo'
$hasFilterRepo = (Get-Command git-filter-repo -ErrorAction SilentlyContinue) -ne $null -or (Get-Command 'git' -ErrorAction SilentlyContinue) -and (& git filter-repo --help 2>&1) -ne $null
if (-not $hasFilterRepo) {
    if (Get-Command python -ErrorAction SilentlyContinue) {
        Write-Host 'Attempting to install git-filter-repo via pip (requires network access)...' -ForegroundColor Yellow
        python -m pip install --upgrade git-filter-repo 2>&1 | Write-Host
        if ($LASTEXITCODE -ne 0) { Write-Warning 'pip install failed or unavailable; please install git-filter-repo manually: https://github.com/newren/git-filter-repo'; }
    } else {
        Write-Warning 'git-filter-repo not found and python not available to install it. Please install git-filter-repo manually.'
    }
}


# Show the planned git-filter-repo command for review (we will use either 'git filter-repo' or a python module fallback)
$pathsArgsArray = @()
if ($PathsToRemove -and $PathsToRemove.Count -gt 0) { $pathsArgsArray += ($PathsToRemove | ForEach-Object { "--path=$_" }) }

# Build extension exclusion globs (e.g. --path-glob='*.db' --path-glob='*.sqlite')
$extGlobs = @()
foreach ($ext in $ExcludeExtensions) { if (-not [string]::IsNullOrWhiteSpace($ext)) { $ext = $ext.TrimStart('.'); $extGlobs += "--path-glob='*.$ext'" } }

# Add strip-blobs-bigger-than (in bytes) if MaxBlobSizeMB provided
$stripSizeArg = $null
if ($MaxBlobSizeMB -gt 0) { $stripSizeArg = "--strip-blobs-bigger-than=$([int]($MaxBlobSizeMB * 1024 * 1024))" }

# Compose preview command
$filterCmdPreviewParts = @()
if ($pathsArgsArray.Count -gt 0) { $filterCmdPreviewParts += $pathsArgsArray }
if ($extGlobs.Count -gt 0) { $filterCmdPreviewParts += $extGlobs }
if ($stripSizeArg) { $filterCmdPreviewParts += $stripSizeArg }
$filterCmdPreview = "git filter-repo --invert-paths " + ($filterCmdPreviewParts -join ' ')

Write-Host "About to run git-filter-repo with the following command (preview):" -ForegroundColor Cyan
Write-Host $filterCmdPreview -ForegroundColor Gray

# Confirm before running destructive operation (unless AutoConfirm)
if (-not $AutoConfirm) {
    $confirm = Read-Host "Proceed to rewrite history (this is destructive and requires force-push)? Type Y to continue"
    if ($confirm -ne 'Y') { Write-Host 'Aborting per user request.'; exit 0 }
} else {
    Write-Host "AutoConfirm enabled: proceeding with rewrite without interactive prompt." -ForegroundColor Yellow
}

# Run git-filter-repo
Write-Host 'Running git-filter-repo ...' -ForegroundColor Yellow
# Use the exact invocation; modern git-filter-repo installs a 'git' subcommand which is invoked as 'git filter-repo'
# Use the git subcommand form (works when git-filter-repo is installed)
try {
    # First try the git subcommand form
    $cmdParts = @('git','filter-repo','--invert-paths') + $filterCmdPreviewParts
    $cmd = $cmdParts -join ' '
    Write-Host "Running: $cmd" -ForegroundColor Gray
    iex $cmd
    if ($LASTEXITCODE -ne 0) { Throw 'git filter-repo command failed' }
} catch {
    Write-Host "git filter-repo subcommand not available or failed: $_" -ForegroundColor Yellow
    # Try python module fallback: python -m git_filter_repo --invert-paths --path <path> ...
    try {
    $pyCmdParts = @('python','-m','git_filter_repo','--invert-paths') + $filterCmdPreviewParts
    $pyCmd = $pyCmdParts -join ' '
    Write-Host "Running fallback: $pyCmd" -ForegroundColor Gray
    iex $pyCmd
        if ($LASTEXITCODE -ne 0) { Throw 'python -m git_filter_repo command failed' }
    } catch {
        Write-Host "git filter-repo failed entirely: $_" -ForegroundColor Red
        Write-Host 'You can try installing git-filter-repo (pip install git-filter-repo) or use BFG as an alternative.' -ForegroundColor Yellow
        exit 1
    }
}

# Housekeeping: expire reflog and aggressively gc
Write-Host 'Expiring reflogs and running garbage collection ...' -ForegroundColor Yellow
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# Show size report
Write-Host 'Repository size summary (count-objects -vH):' -ForegroundColor Cyan
git count-objects -vH

# git-filter-repo may remove the 'origin' remote from a mirror; ensure origin exists and points at the intended URL
Write-Host "\nEnsuring 'origin' remote is configured and pointing to $RepoUrl..." -ForegroundColor Cyan
try {
    $remotes = git remote 2>$null
} catch {
    $remotes = $null
}
if (-not $remotes -or ($remotes -notcontains 'origin')) {
    Write-Host "Origin remote not found; adding origin -> $RepoUrl" -ForegroundColor Yellow
    git remote add origin $RepoUrl
    if ($LASTEXITCODE -ne 0) { Write-Warning "Failed to add origin remote; please add it manually: git remote add origin $RepoUrl" }
} else {
    Write-Host "Origin remote found; setting origin URL to $RepoUrl" -ForegroundColor Yellow
    git remote set-url origin $RepoUrl
    if ($LASTEXITCODE -ne 0) { Write-Warning "Failed to set origin URL; please verify remote configuration." }
}
Write-Host "Current remotes:" -ForegroundColor Gray
git remote -v

# Before attempting a destructive push, verify we actually have refs (branches/tags) to push.
Write-Host "\nChecking for refs (branches/tags) in the rewritten repository..." -ForegroundColor Cyan
try {
    $showRef = git show-ref 2>$null
} catch {
    $showRef = $null
}
if (-not $showRef -or [string]::IsNullOrWhiteSpace($showRef)) {
    Write-Warning "No refs found in the rewritten repository. A force-push now would fail or be a no-op."
    Write-Host "Possible reasons: the original clone had no refs (empty remote), or git-filter-repo removed all refs.\n" -ForegroundColor Yellow
    Write-Host "Options:\n - Run this script from a machine that can authenticate and fetch the remote refs,\n - Or re-run git clone --mirror from an environment with access to the remote and then re-run the rewrite.\n" -ForegroundColor Cyan
    Write-Host "Aborting push to avoid replacing remote with an empty set of refs." -ForegroundColor Red
    exit 1
}

# FINAL CONFIRM: push cleaned history to remote
if ($RewriteOnly) {
    Write-Host "\nRewrite-only mode: rewrite and GC complete. Skipping final push as requested." -ForegroundColor Yellow
    Write-Host "If you want to push the cleaned mirror to origin, run this script again without -RewriteOnly and type PUSH when prompted." -ForegroundColor Cyan
    exit 0
}

Write-Host "
READY TO FORCE-PUSH THE CLEANED REPOSITORY TO ORIGIN ($RepoUrl)
This will replace remote history. All collaborators must re-clone after this." -ForegroundColor Red
$confirmPush = Read-Host "Type PUSH to perform 'git push --force ---mirror origin'"
if ($confirmPush -ne 'PUSH') { Write-Host 'Push aborted by user.'; exit 0 }

Write-Host 'Performing force push (this may take a while) ...' -ForegroundColor Yellow
git push --force --mirror origin
if ($LASTEXITCODE -ne 0) { Abort 'git push --force --mirror failed' }

Write-Host "
SUCCESS: remote mirror has been updated. Please inform collaborators to reclone the repo.
Backup bundle is at: $BackupBundle
Temporary workspace: $TempDir (you can remove it when satisfied)
" -ForegroundColor Green

# End of script
