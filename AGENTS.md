# AGENTS.md

Guidance for coding agents working in this repository.

For general project guidance, see [README.md](README.md).

## Required References

- Project overview and install steps: [README.md](README.md)
- Agent configuration and conventions: [.github/copilot-instructions.md](.github/copilot-instructions.md)
- Language and format rules: see [.github/instructions/AGENTS.md](.github/instructions/AGENTS.md)
- Workflow and navigation help: [.tours/getting-started.tour](.tours/getting-started.tour)
- For enhanced agent capabilities, see [Copilot Plus](.github/agents/copilot-plus.agent.md)

## Agent Catalogs

Use these catalogs for authoritative, machine-readable lists of resources:

- Skills: [.github/skills/AGENTS.md](.github/skills/AGENTS.md) - loadable skills and their SKILL.md entries
- Instructions: [.github/instructions/AGENTS.md](.github/instructions/AGENTS.md) - formatting and language rules
- Workflows: [.github/workflows/AGENTS.md](.github/workflows/AGENTS.md) - reusable GitHub Actions with inputs/triggers
- Prompts: [.github/prompts/AGENTS.md](.github/prompts/AGENTS.md) - available prompt files

### Specialized Agents

For specific tasks, use the following specialized agent instructions:

- [Code Tour Agent](.github/agents/code-tour.agent.md) - For creating/updating `.tours/` files
- [Copilot Plus Agent](.github/agents/copilot-plus.agent.md) - Enhanced Copilot capabilities

## Common Tasks

### Before each commit

- Verify your expected changes with `git diff --no-color`.
- Use the project linting/validation tools to confirm your changes meet the coding standard.
- If the repo uses git hooks, run them to validate your changes.

### Linting and Validation

```bash
# Run all pre-commit checks
pre-commit run -a

# Run specific checks
pre-commit run markdownlint -a
pre-commit run yamllint -a
```

### Understanding the Task

- When the task is not clear, look for additional context.
- If triggered by a brief comment, check whether the parent comment exists and includes more detail.
- If it's still ambiguous, communicate with the user and propose options.

### Testing

```bash
# Run Molecule tests
molecule test

# Syntax check
molecule syntax
```

### Adding or Modifying Workflows

- Workflows in `.github/workflows/` can be reused via `workflow_call`
- Test workflow changes on a feature branch before merging to main
- Use `actionlint` to validate workflow syntax locally

### Updating Coding Standards

- Language-specific instructions are in `.github/instructions/`
- Update `.markdownlint.yaml`, `.yamllint`, or `.editorconfig` for linting rules
- Run `pre-commit run -a` to verify changes pass all checks

## Integrating Changes from Target Branch

Recommended way is to use the **cherry-pick workflow** to rebase your commits
on top of the updated target branch:

1. Identify your feature commits
2. Fetch the latest target branch
3. Reset your branch to target (with backup)
4. Cherry-pick your feature commits
5. Verify only your changes remain

**For detailed step-by-step instructions with commands**, see:
[`.github/skills/git/SKILL.md`](.github/skills/git/SKILL.md)

### Key Points

- **Never** use `git merge <target-branch>` for branch integration
- **Always** create backup tags before destructive operations
- **Always** verify with `git diff` that only your changes remain
- **Use** `GIT_EDITOR=true` for non-interactive cherry-pick operations

### Using `report_progress` Tool

**WARNING**: The `report_progress` tool automatically rebases your branch against the remote
tracking branch. This **WILL CRASH** the session if your local history has diverged from remote.

**When Crash Occurs:**

After using `git reset --hard` to rewrite history, your local branch diverges from remote. When `report_progress`
tries to auto-rebase (e.g., 113 commits), it encounters conflicts it cannot resolve, crashing the session.

**Prevention (Choose One):**

1. **Use new branch name** after rewriting history: `git checkout -b <feature>-v2` (safest)
2. **Complete git operations manually**, then ask user for manual push (never call `report_progress` after `git reset --hard`)

**If Already Crashed:**

1. Run `git rebase --abort`
2. Create new branch: `git checkout -b <feature>-v2`
3. Push new branch: `git push origin <feature>-v2`

**Error Patterns:** `Rebasing (1/XXX)` with large numbers, `CONFLICT (content)`, session crash with `GitError`

**For complete details**, see:
[`.github/skills/git/SKILL.md` - "Working with Automation Tools"](.github/skills/git/SKILL.md#working-with-automation-tools)

## References

- Claude-specific guidance: [CLAUDE.md](CLAUDE.md)
- Main documentation: [README.md](README.md)

## Troubleshooting

### GitHub Build issues

- Use `gh` command to interact with GitHub resources. For example:

  - `gh run list --limit 3` to list recent builds.
  - `gh run view {ID} --log | rg -iw "failed|error|exit"` to look for build errors.

### Firewall issues

If you encounter firewall issues when using the GitHub Copilot Agent:

- Refer to <https://gh.io/copilot/firewall-config> for configuration details.
- If you need to allowlist additional hosts, update your firewall configuration accordingly
  and keep the list of allowed hosts in `.github/agents/FIREWALL.md` up to date.

### Linting issues

If Copilot or automated checks behave unexpectedly:

- Re-run `pre-commit run -a` locally to surface formatting or linting issues.
- Verify `.markdownlint.yaml` and `.yamllint` have not been modified incorrectly.
- If problems persist, open an issue with details of the command run and any error output.
