# GitHub Actions Workflows

This directory contains GitHub Actions workflows that automate various tasks for this repository.

## Workflows

### check.yml

**Purpose**: Runs automated checks on all pushes and pull requests to ensure code quality and adherence to
project standards.

**Reusable**: This workflow calls the organization's reusable workflow:

```yaml
uses: Cogni-AI-OU/.github/.github/workflows/check.yml@main
```

**Jobs**:

- **actionlint**: Validates GitHub Actions workflow files for syntax errors and best practices
- **pre-commit**: Runs pre-commit hooks to check code formatting, linting, and other quality checks

**Reference**: Uses [reviewdog/action-actionlint][actionlint-action] and [pre-commit/action][pre-commit-action]

### claude-review.yml

**Purpose**: Provides automated code review for pull requests using Claude AI. Reviews focus on bugs, security
vulnerabilities, performance issues, and missing error handling.

**Reusable**: This workflow calls the organization's reusable workflow:

```yaml
uses: Cogni-AI-OU/.github/.github/workflows/claude-review.yml@main
secrets: inherit
```

**Jobs**:

- **claude-review**: Analyzes pull request changes and posts review comments with identified issues and
  inline suggestions for fixes

**Configuration**:

- Runs on pull requests (opened and synchronized)
- Skips bot-authored PRs automatically
- Uses Claude Opus 4.5 model by default
- Limited to specific allowed tools for security

**Reference**: Uses [anthropics/claude-code-action][claude-action]

### claude.yml

**Purpose**: Enables interactive collaboration with Claude AI on issues and pull requests. Claude can be
triggered by mentioning `@claude` in comments, reviews, or newly opened issues.

**Reusable**: This workflow calls the organization's reusable workflow:

```yaml
uses: Cogni-AI-OU/.github/.github/workflows/claude.yml@main
secrets: inherit
```

**Jobs**:

- **claude**: Responds to `@claude` mentions and provides AI-assisted coding, debugging, and problem-solving

**Security Features**:

- Strict access control (only OWNER, MEMBER, COLLABORATOR, CONTRIBUTOR associations)
- PR/issue authors can trigger on their own content
- External contributors are explicitly blocked

**Configuration**:

- Uses Claude Opus 4.5 model by default
- Maximum 100 turns per conversation
- Grants broad git access for autonomous commits (requires repository branch protection)

**Reference**: Uses [anthropics/claude-code-action][claude-action]

### devcontainer-ci.yml

**Purpose**: Builds and tests the development container configuration to ensure all required tools and
dependencies are properly installed.

**Reusable**: This workflow calls the organization's reusable workflow:

```yaml
uses: Cogni-AI-OU/.github/.github/workflows/devcontainer-ci.yml@main
```

**Jobs**:

- **devcontainer-build**: Builds the dev container, verifies required commands and Python packages are
  installed, and pushes the image to GitHub Container Registry on main branch

**Triggers**:

- Pull requests affecting `.devcontainer/` or this workflow
- Pushes to main branch affecting `.devcontainer/` or this workflow

**Reference**: Uses [devcontainers/ci][devcontainer-ci-action]

## Security Considerations

The Claude workflows grant intentionally broad git access to enable autonomous code changes. To safely use
these workflows:

- Enable branch protection rules requiring pull request reviews
- Require status checks to pass before merging
- Monitor audit logs for `github-actions[bot]` activity
- Use CODEOWNERS for sensitive directories
- Review Claude's commits before merging PRs

For detailed security guidance, see [../README.md](../README.md) and [CLAUDE.md](../../CLAUDE.md).

## Problem Matchers

Problem matchers automatically annotate files with errors and warnings in pull requests. This repository uses:

- **actionlint-matcher.json**: For actionlint workflow validation errors
- **pre-commit-matcher.json**: For pre-commit hook errors

These are registered in the workflows before running the corresponding tools.

<!-- Named links -->

[actionlint-action]: https://github.com/reviewdog/action-actionlint
[pre-commit-action]: https://github.com/pre-commit/action
[claude-action]: https://github.com/anthropics/claude-code-action
[devcontainer-ci-action]: https://github.com/devcontainers/ci
