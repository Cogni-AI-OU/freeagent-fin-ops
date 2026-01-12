# AGENTS.md

[Guidance for coding agents](https://agents.md/) working in this repository.

## Quick Start

- See [README.md](README.md) for setup and installation instructions
- See [.tours/getting-started.tour](.tours/getting-started.tour) for a guided walkthrough
- For enhanced agent capabilities, see [Copilot Plus](.github/agents/copilot-plus.agent.md)

## Instructions

For detailed coding standards and formatting guidelines, refer to:

- [Copilot Instructions](.github/copilot-instructions.md) - Main coding standards
- [Ansible](.github/instructions/ansible.instructions.md) - Ansible conventions
- [JSON](.github/instructions/json.instructions.md) - JSON formatting standards
- [Markdown](.github/instructions/markdown.instructions.md) - Markdown standards
- [YAML](.github/instructions/yaml.instructions.md) - YAML formatting standards

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

```bash
# Run tests if available
python -m pytest tests/

# Test CLI script manually
./scripts/fa_cli.py --help
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
[`.github/skills/git/SKILL.md` - "Integrating Changes from Target Branch"](.github/skills/git/SKILL.md#integrating-changes-from-target-branch-avoiding-merge-commits)

### Key Points

- **Never** use `git merge <target-branch>` for branch integration
- **Always** create backup tags before destructive operations
- **Always** verify with `git diff` that only your changes remain
- **Use** `GIT_EDITOR=true` for non-interactive cherry-pick operations

### Running the CLI

```bash
# Authenticate and cache tokens
./scripts/fa_cli.py auth

# List bank accounts
./scripts/fa_cli.py bank-accounts list

# List bank transactions
./scripts/fa_cli.py bank-transactions list --bank-account <url>

# List bills
./scripts/fa_cli.py bills list

# List invoices
./scripts/fa_cli.py invoices list

# Get accounting reports
./scripts/fa_cli.py reports balance-sheet
./scripts/fa_cli.py reports profit-and-loss
```

### Environment Setup

```bash
# Install dependencies
pip install -r .devcontainer/requirements.txt

# Install pre-commit hooks
pre-commit install

# Set up environment variables (copy from .env.example)
cp .env.example .env
# Edit .env with your FreeAgent OAuth credentials
```

## Configuration

- **Environment Variables**: All configuration is via `FREEAGENT_*` environment variables
- **OAuth2 Flow**: Uses authorization code flow with token refresh
- **Output Formats**: Supports plain, csv, json, and yaml output formats
- **Pagination**: Built-in pagination support with configurable page size

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

### Project-specific issues

FreeAgent API Issues:

- Check API rate limits (429 responses)
- Verify OAuth tokens are valid (refresh on 401)
- Ensure environment variables are set correctly
