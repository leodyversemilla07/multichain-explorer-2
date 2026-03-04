---
description: search git best practices, commands, branching strategies, merging, hooks, and workflows
---

# Git Agents Skill

Use this workflow to search the git-agents skill knowledge base for best practices, commands, and patterns.

## Invoking the Skill

```bash
# Auto-detect the domain from the query
python .shared/git-agents/scripts/search.py "<your query>"

# Target a specific domain
python .shared/git-agents/scripts/search.py "<your query>" --domain <domain>

# Limit results
python .shared/git-agents/scripts/search.py "<your query>" --domain <domain> -n 2
```

## Available Domains

| Domain | Flag | Topics |
|--------|------|--------|
| Commits | `--domain commits` | Conventional commits, amend, squash, GPG signing, stash |
| Branching | `--domain branching` | Create, switch, name, delete, protect, orphan, tracking |
| Merging | `--domain merging` | Merge vs rebase, squash merge, conflicts, cherry-pick |
| History | `--domain history` | git log, blame, bisect, reflog, grep, diff, show |
| Remotes | `--domain remotes` | Push, pull, fetch, clone, fork, sync, sparse checkout |
| Hooks | `--domain hooks` | pre-commit, commit-msg, pre-push, lefthook, framework |
| Debugging | `--domain debugging` | reset, revert, stash, recover lost commits, worktree |
| Workflows | `--domain workflows` | Gitflow, trunk-based, PR process, semver, changelog |

## Recommended Usage Pattern

1. **Identify intent** — What Git operation are you about to do?
2. **Search the skill** — Run the search command for the relevant domain
3. **Read the result** — Pay attention to the **Gotchas** field — it highlights common mistakes
4. **Apply** — Use the **Command Example** as a starting point

## Example Searches

```bash
# Before writing a commit
python .shared/git-agents/scripts/search.py "conventional commit message format" --domain commits

# Before merging a feature branch
python .shared/git-agents/scripts/search.py "squash merge PR clean history" --domain merging

# When something went wrong
python .shared/git-agents/scripts/search.py "recover lost commits after reset hard" --domain debugging

# Setting up team hooks
python .shared/git-agents/scripts/search.py "pre-commit framework version controlled team" --domain hooks

# Choosing a workflow
python .shared/git-agents/scripts/search.py "trunk based development CI continuous" --domain workflows
```
