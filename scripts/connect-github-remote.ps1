param(
    [Parameter(Mandatory = $true)]
    [string]$RemoteUrl,
    [string]$Branch = "main",
    [switch]$Push
)

$ErrorActionPreference = 'Stop'

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Git is not installed or not available in PATH. Install Git for Windows first."
}

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

if (-not (Test-Path ".git")) {
    throw "This folder is not a Git repo yet. Run scripts\\init-local-repo.ps1 first."
}

$existing = git remote get-url origin 2>$null
if ($LASTEXITCODE -eq 0 -and $existing) {
    git remote set-url origin $RemoteUrl | Out-Host
    Write-Host "Updated existing origin remote." -ForegroundColor Yellow
} else {
    git remote add origin $RemoteUrl | Out-Host
    Write-Host "Added origin remote." -ForegroundColor Green
}

git branch -M $Branch | Out-Host

if ($Push) {
    git push -u origin $Branch | Out-Host
}
