# CLAUDE.md

This file provides Claude Code-specific guidance for the FreeAgent FinOps CLI repository.
For general agent instructions, see [AGENTS.md](AGENTS.md).

## Claude Code Configuration

Claude Code is configured via GitHub Actions workflows in this repository.
The primary workflow is [.github/workflows/claude.yml](.github/workflows/claude.yml).

### Triggering Claude

Claude can be triggered by mentioning `@claude` in:

- **PR comments**: Comment on a pull request with `@claude` followed by instructions
- **Inline review comments**: Add `@claude` to a review comment on specific code lines
- **Issue comments**: Comment on an issue with `@claude` followed by instructions
- **New issues**: Create an issue with `@claude` in the title or body
- **Reply to Claude's comments**: Reply to Claude's comments (posted via
  `github-actions[bot]` with claude-code-action markers) to continue the
  conversation without needing to mention `@claude` again

**Who can trigger Claude:**

- Organization owners, members, and collaborators (on any PR/issue)
- PR authors (on their own PRs only)
- Issue authors (on their own issues only)

**Security**: External contributors cannot trigger Claude on other people's PRs or
issues. This prevents unauthorized API usage and ensures code changes are reviewed
by trusted users.

**Note**: Claude's comments appear under the `github-actions[bot]` user because
they are posted through the GitHub Actions workflow.

### Environment Variables

- `ANTHROPIC_API_KEY`: API key for Claude (stored as repository secret)
- Required secrets must be configured in repository settings

### Model Selection

By default, workflows use `claude-opus-4-5`. The model is configured in the
organization's `.github` repository workflow templates.

## Tools

Claude Code provides access to various tools for interacting with the repository
and environment.

### Allowed Tools

The allowed tools are defined in the organization's workflow files. Current categories include:

- **File operations**: Edit, Read, Write, Glob, Grep, LS
- **Git operations**: Full git access for commits and pushes
- **GitHub CLI**: Issue and PR management commands
- **Data processing**: jq, yq for JSON/YAML manipulation
- **Pre-commit**: Running linting and validation

### Model Context Protocol (MCP)

MCP servers extend Claude's capabilities with additional tools and integrations.

**Built-in MCP Servers:**

The Claude Code Action automatically provides these MCP servers:

- `github_comment`: Post and update PR/issue comments
- `github_inline_comment`: Create inline code review comments
- `github_ci`: Access CI status and workflow run details

## Prompting Best Practices

When working with Claude in this repository:

- Reference `AGENTS.md` for coding standards and common tasks
- Reference `.github/copilot-instructions.md` for detailed project context
- Run `pre-commit run -a` before finalizing changes
- Test CLI changes manually using `./scripts/fa_cli.py`
- Keep responses concise; focus on actionable issues
- Verify OAuth flow and API interactions work correctly

## Project-Specific Context

### FreeAgent API

- Uses OAuth2 authorization code flow
- Supports token refresh (handles 401 responses)
- Implements rate limit handling (429 backoff)
- Configuration via `FREEAGENT_*` environment variables

### CLI Architecture

- Python 3.11+ with `uv` script headers
- `argparse` for CLI argument parsing
- Multiple output formats: plain, csv, json, yaml
- Pagination support with configurable page size
- BrokenPipeError handling for piped output

### Key Files

- `scripts/fa_cli.py`: Main CLI with all commands
- `.env.example`: Documents required environment variables
- `.github/copilot-instructions.md`: Comprehensive project documentation
- `.github/prompts/sdk-scripts.prompt.md`: Guidance for extending CLI

## Troubleshooting

### Common Issues

1. **Workflow not triggering**: Check `@claude` mentions and workflow logs
2. **Linting failures**: Run `pre-commit run -a` locally
3. **API authentication**: Verify `FREEAGENT_*` environment variables
4. **CLI execution**: Ensure Python 3.11+ and dependencies are installed

### Testing Changes

```bash
# Run pre-commit checks
pre-commit run -a

# Test CLI authentication
./scripts/fa_cli.py auth

# Test basic commands
./scripts/fa_cli.py bank-accounts list
./scripts/fa_cli.py --help
```

### Required Secrets

The following secrets must be configured in repository settings:

- `ANTHROPIC_API_KEY`: Required for Claude Code workflows

For FreeAgent API testing, developers need to configure their own OAuth credentials
in `.env` file (not stored in repository).
