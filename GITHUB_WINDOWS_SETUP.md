# Windows GitHub Setup

This project is ready for both:
- a **local Git repository** on your PC, and
- a **GitHub remote repository** you push to later.

## Option A: Fastest path with PowerShell

Open PowerShell in the project folder and run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\init-local-repo.ps1 -CommitMessage "Initial hybrid bot commit" -ForceMain
```

Then connect a GitHub remote:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\connect-github-remote.ps1 -RemoteUrl "https://github.com/YOURNAME/YOURREPO.git" -Push
```

## Option B: GitHub Desktop

1. Open GitHub Desktop.
2. Choose **Add an Existing Repository**.
3. Pick this project folder.
4. Commit the current files.
5. Publish the repository.

You can also double-click `scripts\\open-in-github-desktop.bat`.

## Safety notes

- `.env` is ignored by Git and stays local.
- Database files in `data/` are ignored.
- `data/.gitkeep` keeps the folder present after cloning.
