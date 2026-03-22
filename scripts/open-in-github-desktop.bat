@echo off
setlocal
set PROJECT_ROOT=%~dp0..
if exist "%LocalAppData%\GitHubDesktop\GitHubDesktop.exe" (
  start "" "%LocalAppData%\GitHubDesktop\GitHubDesktop.exe" "%PROJECT_ROOT%"
) else (
  echo GitHub Desktop was not found in the default location.
  echo Open GitHub Desktop manually and add this folder as an existing repository.
)
