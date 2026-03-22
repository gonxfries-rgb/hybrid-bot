param(
    [string]$CommitMessage = "Initial commit",
    [switch]$ForceMain
)

$ErrorActionPreference = 'Stop'

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Git is not installed or not available in PATH. Install Git for Windows first."
}

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

if (-not (Test-Path ".git")) {
    git init | Out-Host
}

if ($ForceMain) {
    git branch -M main 2>$null | Out-Host
}

if (-not (Test-Path ".gitignore")) {
    throw ".gitignore is missing."
}

if (Test-Path ".env") {
    Write-Host "Found .env. It will stay local and will not be committed if .gitignore is unchanged." -ForegroundColor Yellow
}

git add . | Out-Host

$status = git status --porcelain
if (-not $status) {
    Write-Host "Nothing to commit. Local repo is already initialized." -ForegroundColor Cyan
    exit 0
}

git commit -m $CommitMessage | Out-Host
Write-Host "Local Git repo is ready." -ForegroundColor Green
