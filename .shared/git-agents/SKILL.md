---
name: git-agents
description: Search Git best practices, workflows, and commands across 8 domains — commits, branching, merging, history, remotes, hooks, debugging, and workflows. Use this skill when working with Git operations, resolving conflicts, writing commit messages, managing branches, or setting up automation.
---

# Git Agents Skill

A searchable knowledge base of Git best practices, commands, and patterns organized across 8 domains. Uses BM25 full-text search to return the most relevant entries for a given query.

## Usage

```bash
# Search a specific domain
python .shared/git-agents/scripts/search.py "squash commits before merge" --domain commits

# Auto-detect domain from query
python .shared/git-agents/scripts/search.py "undo last commit keep changes"

# Limit results
python .shared/git-agents/scripts/search.py "rebase vs merge" --domain merging -n 2
```

## Domains

| Domain | `--domain` flag | Covers |
|--------|----------------|--------|
| Commits | `commits` | Writing messages, amending, squashing, signing |
| Branching | `branching` | Naming, strategies, protection, deletion |
| Merging | `merging` | Merge vs rebase, squash, conflict resolution |
| History | `history` | Log, blame, bisect, reflog, searching |
| Remotes | `remotes` | Push, pull, fetch, forks, upstream tracking |
| Hooks | `hooks` | pre-commit, commit-msg, pre-push, CI integration |
| Debugging | `debugging` | Bisect, stash, patch, cherry-pick, recovery |
| Workflows | `workflows` | Gitflow, trunk-based, PR process, tagging, releases |

## When to Use This Skill

- Before writing a commit message (search `commits`)
- When planning a branching strategy (search `branching`)
- When resolving a conflict or choosing merge vs rebase (search `merging`)
- When you need to find something in the history (search `history`)
- When setting up remote tracking or forks (search `remotes`)
- When automating checks with hooks (search `hooks`)
- When recovering from a mistake or debugging broken state (search `debugging`)
- When defining a team workflow or release process (search `workflows`)

## How to Read Results

Each result includes:
- **Command/Pattern Name** — what to call this technique
- **Keywords** — terms to search with
- **Description** — what it does and why
- **When to Use** — concrete scenarios
- **Command Example** — exact Git commands
- **Gotchas** — known caveats or dangerous misuses
- **Docs URL** — link to official docs
