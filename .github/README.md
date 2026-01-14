# GitHub Workflows and Actions

This directory contains GitHub Actions workflows, agent prompts, and related configuration.

## Workflows

### Check Workflow

The `check.yml` workflow runs on pull requests, pushes, and weekly schedule to
ensure code quality and correctness.

Jobs:

- **actionlint**: Validates GitHub Actions workflow files
- **link-checker**: Checks for broken links in Markdown files using Lychee
- **pre-commit**: Runs pre-commit hooks for code formatting and linting

#### Link Checker

The link checker job uses [Lychee](https://github.com/lycheeverse/lychee) to
scan all Markdown files for broken links. It includes caching to avoid rate
limits and can be configured via `.lycheeignore` at the repository root to
exclude specific URLs or patterns.

**Local Testing**: You can test links locally using `linkcheckmd` (a Python
alternative to Lychee):

```bash
# Install from requirements.txt
pip install -r .devcontainer/requirements.txt

# Check a single file
python -m linkcheckmd path/to/file.md

# Check all markdown files in a directory
python -m linkcheckmd .
```

The tool checks both local file references and remote URLs, making it easy to
catch broken links before pushing changes.

## Workflow Templates

The `workflow-templates/` directory contains reference workflows that are not
actively executed but are preserved for future use or copying to other
repositories. These templates can be customized and moved to the `workflows/`
directory when needed.

## Agent Prompts

The `prompts/` directory contains ready-to-use prompts for AI agents to perform
common repository management tasks. For agent-loading guidance and catalog, see
[prompts/AGENTS.md](prompts/AGENTS.md). For human-oriented details, see
[prompts/README.md](prompts/README.md).

## Problem Matchers

GitHub Actions problem matchers automatically annotate files with errors and
warnings in pull requests, making it easier to identify and fix issues.

### Available Matchers

- **actionlint-matcher.json**: Captures errors from actionlint workflow linting
- **pre-commit-matcher.json**: Captures errors from pre-commit hooks

### Pre-commit Problem Matcher

The pre-commit problem matcher supports two output formats:

1. **Generic format** (`file:line:col: message`): Used by flake8, actionlint,
   and other tools that provide column information
2. **No-column format** (`file:line message`): Used by markdownlint and other
   tools that only provide line numbers

Note: Some hooks like yamllint and ansible-lint already output GitHub Actions
annotations directly and don't need the problem matcher.

### Configuration

Problem matchers are registered in the `.github/workflows/check.yml` workflow
before running the corresponding tools.

## Security

### Claude Workflow Git Access

The Claude Code workflow (`claude.yml`) grants intentionally broad git access
via `Bash(git:*)` to enable autonomous code changes. This permission is necessary
for Claude to commit and push changes, but requires proper safeguards.

#### Security Controls

**Access Control:**

- Only trusted users can trigger Claude (OWNER, MEMBER, COLLABORATOR, CONTRIBUTOR)
- PR/issue authors can only trigger on their own content
- External contributors (FIRST_TIME_CONTRIBUTOR, NONE) are explicitly blocked

**Required Repository Protections:**

To safely use Claude with git access, repository administrators must configure:

1. **Branch Protection Rules** on main/protected branches:
   - Require pull request reviews before merging
   - Require status checks to pass (e.g., linting, tests)
   - Require conversation resolution before merging
   - Do not allow bypassing the above settings

2. **GitHub Audit Logs** (organization-level):
   - Enable and regularly review audit logs
   - Monitor commits made by `github-actions[bot]` (Claude's identity)
   - Set up alerts for suspicious patterns (rapid commits, deleted branches, etc.)

3. **Protected Branch Policies**:
   - Restrict who can push to protected branches
   - Consider requiring deployment approvals for production branches
   - Use CODEOWNERS to require specific reviewer approval for sensitive files

#### Best Practices

- Review Claude's commits before merging PRs
- Use draft PRs for Claude's work to require explicit promotion
- Regularly audit Claude's tool usage and permissions
- Rotate `ANTHROPIC_API_KEY` periodically
- Monitor workflow run logs for unexpected behavior

For more details, see [CLAUDE.md](../CLAUDE.md).
