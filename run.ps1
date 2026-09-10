param(
    [string]$Path = ".\sample.png",
    [ValidateSet("json", "md")][string]$Format = "json",
    [string]$Output = ""
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

if (-not (Test-Path ".\.venv\Scripts\Activate.ps1")) {
    Write-Error "Virtual environment not found. Run: python -m venv .venv"
    exit 1
}

& ".\.venv\Scripts\Activate.ps1"

$arguments = @("main.py", "analyze", $Path, "--format", $Format)
if ($Output) {
    $arguments += @("--output", $Output)
}

python @arguments
