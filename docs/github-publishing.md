# Publish to the target GitHub repository

Target: `https://github.com/ThushanDev/VedaOps-Self-Healing-Server_-DevOps-Project.git`

These steps leave commit and push under your control.

## If this folder is already a clone of the target repository

Open PowerShell in the repository folder and confirm the remote before staging:

```powershell
git remote -v
git status
```

If `origin` points somewhere else, update it to the target URL and inspect `git status` again:

```powershell
git remote set-url origin https://github.com/ThushanDev/VedaOps-Self-Healing-Server_-DevOps-Project.git
```

After reviewing the changes, stage and create a commit with your Git identity:

```powershell
git add -A
git status
git commit -m "feat: build VedaOps self-healing server"
```

If the target repository is empty and this is its first commit, push `main`:

```powershell
git push -u origin main
```

If the target already has a default branch or protects `main`, create a feature branch before staging, then push it and open a pull request:

```powershell
git switch -c feature/vedaops-project
git add -A
git status
git commit -m "feat: build VedaOps self-healing server"
git push -u origin feature/vedaops-project
```

Use the repository's actual default branch if it is not `main`. Do not use `--force` to get around a rejected push; fetch and reconcile the remote changes first.

## If this folder is not a clone

The target repository is public and its `main` branch currently contains only a README. Clone it beside this workspace, then run this PowerShell block from the VedaOps project root. It keeps the clone's `.git` metadata and skips local environment/runtime files while copying the project, including `.env.example`.

```powershell
git clone https://github.com/ThushanDev/VedaOps-Self-Healing-Server_-DevOps-Project.git ..\VedaOps-Self-Healing-Server_-DevOps-Project
$SourcePath = (Resolve-Path .).Path
$TargetPath = (Resolve-Path ..\VedaOps-Self-Healing-Server_-DevOps-Project).Path
if (-not (Test-Path -LiteralPath (Join-Path $TargetPath '.git') -PathType Container)) { throw 'Target is not a Git clone.' }
robocopy $SourcePath $TargetPath /E /R:1 /W:1 /XD .git .runtime .venv .vscode __pycache__ .pytest_cache .ruff_cache dist build /XF .env .env.* .coverage *.pyc
$CopyExitCode = $LASTEXITCODE
if ($CopyExitCode -ge 8) { throw "Copy failed with robocopy exit code $CopyExitCode." }
Copy-Item -LiteralPath (Join-Path $SourcePath '.env.example') -Destination $TargetPath -Force
Set-Location $TargetPath
git status
```

Review the resulting changes, then follow the commit and push steps above. If Git prompts you to sign in, complete GitHub's normal authentication flow yourself. The CI checks run on the pull request before it can be merged.
