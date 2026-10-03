<#
.SYNOPSIS
    Mirror the project knowledge base into the dsh-kb vault.

.DESCRIPTION
    WHY POWERSHELL: in this restricted environment Python subprocesses are
    denied write access to the dsh-kb vault, while PowerShell is allowed. So
    Python does the parsing/rendering (tools/render_index.py) and this script
    only writes files.

    This file is deliberately ASCII-ONLY. Windows PowerShell 5.1 reads .ps1
    files as ANSI when they have no BOM, which corrupts non-ASCII literals and
    breaks parsing. All Chinese text is emitted by render_index.py instead.

    Behaviour:
      * copy kb/wiki/**/*.md  ->  <Target>/wiki/
      * copy kb/schema.md     ->  <Target>/schema.md
      * regenerate index.md from frontmatter
      * append one line to log.md (read-then-write)
      * never touches raw/ (schema: raw material is immutable)

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File tools\sync_kb.ps1
    powershell -ExecutionPolicy Bypass -File tools\sync_kb.ps1 -Target D:\kb -DryRun
#>
[CmdletBinding()]
param(
    [string]$Target = (Join-Path $HOME '.dsh\kb'),
    [string]$Source,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

# The renderer emits UTF-8; make sure PowerShell decodes it as UTF-8 rather
# than the console's default code page (otherwise index.md lands as mojibake).
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$env:PYTHONIOENCODING = 'utf-8'

# Windows PowerShell 5.1 turns a native command's stderr into a terminating
# error while ErrorActionPreference is 'Stop'. Python legitimately writes
# warnings to stderr, so relax the preference around those calls.
function Invoke-Python {
    param([string[]]$Arguments)
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $output = & $python @Arguments 2>&1
        $code = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previous
    }
    if ($code -ne 0) {
        throw "python $($Arguments -join ' ') exited with code $code`n$output"
    }
    # Drop any stderr text that came through the merge.
    return @($output | Where-Object { $_ -isnot [System.Management.Automation.ErrorRecord] })
}

$projectRoot = Split-Path -Parent $PSScriptRoot
if (-not $Source) { $Source = Join-Path $projectRoot 'kb' }

$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) { $python = 'python' }
$renderer = Join-Path $PSScriptRoot 'render_index.py'

Write-Host "[sync_kb] source : $Source"
Write-Host "[sync_kb] target : $Target"
Write-Host "[sync_kb] python : $python"

if (-not (Test-Path (Join-Path $Source 'wiki'))) {
    throw "source is missing wiki/: $Source"
}

$pages = @(Get-ChildItem -Path (Join-Path $Source 'wiki') -Recurse -File -Filter '*.md')
Write-Host "[sync_kb] pages  : $($pages.Count)"

if ($DryRun) {
    foreach ($page in $pages) {
        Write-Host ("  - " + $page.FullName.Substring($Source.Length).TrimStart('\'))
    }
    Write-Host '[sync_kb] dry-run complete, nothing written'
    return
}

# ---- 1. copy wiki pages ---------------------------------------------------
$copied = 0
foreach ($page in $pages) {
    $rel = $page.FullName.Substring($Source.Length).TrimStart('\')
    $destination = Join-Path $Target $rel
    $parent = Split-Path -Parent $destination
    if (-not (Test-Path $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    Copy-Item -LiteralPath $page.FullName -Destination $destination -Force
    $copied++
}
Write-Host "[sync_kb] copied $copied pages"

# ---- 2. schema.md ---------------------------------------------------------
$schema = Join-Path $Source 'schema.md'
if (Test-Path $schema) {
    Copy-Item -LiteralPath $schema -Destination (Join-Path $Target 'schema.md') -Force
    Write-Host '[sync_kb] schema.md updated'
}

# ---- 3. index.md (regenerated from frontmatter) ---------------------------
$indexText = Invoke-Python -Arguments @($renderer, '--kb-root', $Source)
$indexPath = Join-Path $Target 'index.md'
[System.IO.File]::WriteAllText($indexPath, ($indexText -join "`n") + "`n",
    (New-Object System.Text.UTF8Encoding($false)))
Write-Host "[sync_kb] index.md updated"

# ---- 4. log.md (read-then-write, append one line) -------------------------
$logPath = Join-Path $Target 'log.md'
$existing = ''
if (Test-Path $logPath) {
    $existing = [System.IO.File]::ReadAllText($logPath)
}
if ([string]::IsNullOrWhiteSpace($existing)) {
    $existing = (Invoke-Python -Arguments @($renderer, '--log-header')) -join "`n"
}
$logLine = (Invoke-Python -Arguments @(
    $renderer, '--kb-root', $Source, '--log-line', '--count', $copied
)) -join "`n"
if (-not $existing.EndsWith("`n")) { $existing += "`n" }
[System.IO.File]::WriteAllText($logPath, $existing + $logLine + "`n",
    (New-Object System.Text.UTF8Encoding($false)))
Write-Host '[sync_kb] log.md appended'

# ---- 5. verify ------------------------------------------------------------
$result = @(Get-ChildItem -Path $Target -Recurse -File -Filter '*.md')
Write-Host "[sync_kb] target vault now holds $($result.Count) .md files"
Write-Host '[sync_kb] done'
