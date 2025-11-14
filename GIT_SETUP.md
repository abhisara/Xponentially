# Git Setup for Claude Code

This document describes the Git configuration set up globally for working with Claude Code across all projects.

## Global Git Configuration

### User Information
```bash
user.name=abhisara
user.email=abhinav.sarapure@gmail.com
```

### Commit Template
Location: `~/.gitmessage`

All commits use a structured template with:
- **Type prefix**: feat, fix, refactor, docs, test, chore, perf, style
- **Subject line**: Imperative mood, max 50 characters
- **Body**: Explains why (not how), max 72 characters per line
- **Co-authored-by**: For Claude Code contributions

### Other Settings
- **Default branch**: `main`
- **Pull strategy**: `merge` (not rebase)
- **Default editor**: `nano`

## GitHub CLI (gh)

### Installation
```bash
brew install gh
```

### Authentication
```bash
gh auth login
```

**Current status**: Authenticated as `abhisara` with SSH protocol

### Token Scopes
- `repo` - Full control of private repositories
- `admin:public_key` - Manage public keys
- `gist` - Create gists
- `read:org` - Read org and team membership

## Repository Structure for Claude

### Essential Files in Every Repo

1. **`.gitignore`** - Protects sensitive files
   - `.env` files (API keys, secrets)
   - Virtual environments (`.venv/`, `venv/`)
   - Cache files (`__pycache__/`, `*.pyc`)
   - IDE configs (`.vscode/`, `.idea/`)
   - OS files (`.DS_Store`)

2. **`CLAUDE.md`** - Project-specific instructions
   - Virtual environment location
   - Git conventions
   - Branching strategy
   - Pre-commit checklist

3. **`.gitmessage`** (optional local override)
   - Project-specific commit template
   - Only if different from global template

## Workflow for Claude Code

### Creating a New Repository

```bash
# Initialize Git
git init

# Create .gitignore
# (Use project-appropriate template)

# Create initial commit
git add .
git commit -m "feat: initial commit

Description of what this project does.

Co-Authored-By: Claude <noreply@anthropic.com>"

# Create GitHub repo and push
gh repo create <repo-name> --public --source=. --description="<description>" --push
```

### Making Commits

```bash
# Stage changes
git add .

# Commit with template (editor will open with template)
git commit

# Or inline commit following template format
git commit -m "type: subject

Body explaining why this change was made.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### Pushing Changes

```bash
# Push to GitHub
git push

# Or for first push on new branch
git push -u origin <branch-name>
```

## Branching Strategy

### Main Branch
- `main` - Production-ready code
- Protected, requires clean commits

### Feature Branches
- `feature/<name>` - New features
- `fix/<name>` - Bug fixes
- `refactor/<name>` - Code improvements
- `docs/<name>` - Documentation updates

### Workflow
```bash
# Create feature branch
git checkout -b feature/new-feature

# Work on feature, make commits
git add .
git commit

# Push feature branch
git push -u origin feature/new-feature

# Create PR via GitHub CLI
gh pr create --title "feat: new feature" --body "Description"

# After PR approval, merge (on GitHub or via CLI)
gh pr merge --merge
```

## Best Practices for Claude

### Before Committing
1. ✅ Verify `.env` is NOT staged (`git status`)
2. ✅ Check no API keys in code (`git diff`)
3. ✅ Review diff to ensure only intended changes
4. ✅ Run basic smoke test if applicable

### Commit Message Quality
- **DO**: Use imperative mood ("add feature" not "added feature")
- **DO**: Explain why, not how
- **DO**: Reference issues/tickets when applicable
- **DO**: Add Co-Authored-By for Claude Code contributions
- **DON'T**: Commit without description
- **DON'T**: Use vague messages ("fix stuff", "updates")

### What to Commit
- ✅ Source code
- ✅ Configuration files (without secrets)
- ✅ Documentation
- ✅ Requirements/dependency files
- ✅ Tests
- ❌ `.env` files
- ❌ Virtual environments
- ❌ Cache/compiled files
- ❌ API keys or tokens
- ❌ Large binary files (unless necessary)

## GitHub CLI Useful Commands

### Repository Management
```bash
# Create repo
gh repo create <name> --public --source=. --push

# View repo
gh repo view

# Clone repo
gh repo clone <owner>/<repo>
```

### Pull Requests
```bash
# Create PR
gh pr create --title "title" --body "description"

# List PRs
gh pr list

# View PR
gh pr view <number>

# Merge PR
gh pr merge <number> --merge
```

### Issues
```bash
# Create issue
gh issue create --title "title" --body "description"

# List issues
gh issue list

# View issue
gh issue view <number>
```

## Cross-Project Consistency

This setup ensures:
1. **Consistent commit messages** across all projects
2. **Claude-friendly conventions** documented in CLAUDE.md
3. **Security by default** with comprehensive .gitignore
4. **Easy GitHub integration** with gh CLI
5. **Global settings** that work everywhere

## Verifying Setup

```bash
# Check global config
git config --global --list

# Check GitHub auth
gh auth status

# Check remote
git remote -v

# Check current branch
git branch -vv
```

---

**Last Updated**: 2025-11-13
**Configured by**: Claude Code with user abhisara
