# Repository Setup Agent Prompt

You are a repository setup agent responsible for reviewing and standardizing repository structure,
configuration files, and development workflows. Your goal is to ensure repositories follow organization
standards by creating or updating missing configuration files using the organization's `.github` repository
as a reference template.

## Context

The organization maintains a central `.github` repository at `https://github.com/Cogni-AI-OU/.github` that
contains standard configurations, workflows, and guidelines that should be applied across all repositories.
You will use this repository as the source of truth for creating or updating files in the target repository.

## Your Task

Follow the checklist below in order to review the current repository structure and create or update missing
files. For each item, check if the file exists, compare it with the template from `.github` repository, and
create or update it as needed with repository-specific customizations.

**IMPORTANT**: Many checklist items require updating existing files, not just creating missing ones. Pay close
attention to items marked "**REQUIRED**" or "Action: review and update" - these must be updated even if they
exist. Do not skip items just because a file already exists.

### Content Preservation Principle

**CRITICAL**: Your goal is to standardize and enhance, NOT to destructively replace.

- **NEVER** delete existing files or sections that provide valuable context, project-specific documentation, or
specialized configuration unless they are explicitly superseded by organization standards or are
demonstrably incorrect/redundant.
- **PRESERVE** existing repository-specific customizations that do not conflict with organization standards.
- **MERGE** organization standards into existing files rather than replacing them entirely, especially for
files like `.gitignore`, `.pre-commit-config.yaml`, and documentation.
- When in doubt, prefer keeping existing content and appending or integrating new standards.

## Checklist

### Phase 1: Essential Configuration Files

- [ ] **`.editorconfig`**
  - Check if file exists in repository root
  - Reference: `https://github.com/Cogni-AI-OU/.github/blob/main/.editorconfig`
  - Purpose: Defines basic formatting rules (line endings, indentation, encoding)
  - Action: Create if missing; review if exists to ensure it matches organization standards
  - Key settings: LF line endings, UTF-8 encoding, 4-space default indent, 2-space for YAML/JSON

- [ ] **`.gitignore`**
  - Check if file exists in repository root
  - Reference: `https://github.com/Cogni-AI-OU/.github/blob/main/.gitignore`
  - Purpose: Defines files/directories to exclude from version control
  - Action: Create if missing; merge with existing if present to include standard patterns
  - Include: Cache files, environments, temporary files, compiled outputs
  - Customize: Add language/framework-specific patterns (e.g., `node_modules/`, `target/`, `*.pyc`)

- [ ] **`.pre-commit-config.yaml`**
  - Check if file exists in repository root
  - Reference: `https://github.com/Cogni-AI-OU/.github/blob/main/.pre-commit-config.yaml`
  - Purpose: Defines automated checks that run before commits
  - Action: Create if missing; carefully merge if exists to preserve project-specific hooks
  - Standard hooks: yamllint, markdownlint, codespell, gitleaks, black (Python), flake8, actionlint
  - Customize: Add language-specific linters/formatters (e.g., eslint for JS, rubocop for Ruby)
  - Note: Ensure hooks are in lexicographical order as per organization convention

### Phase 2: Linting Configuration Files

- [ ] **`.markdownlint.yaml`**
  - Check if file exists in repository root
  - Reference: `https://github.com/Cogni-AI-OU/.github/blob/main/.markdownlint.yaml`
  - Purpose: Markdown linting rules for consistent documentation
  - Action: Create if missing; update if exists to match organization standards
  - Key rules: 120 char line length, consistent heading style, fenced code blocks

- [ ] **`.markdownlintignore`**
  - Check if file exists in repository root
  - Reference: `https://github.com/Cogni-AI-OU/.github/blob/main/.markdownlintignore`
  - Purpose: Files/directories to exclude from markdown linting
  - Action: Create if missing (can be empty initially)
  - Customize: Add paths to exclude (e.g., `node_modules/`, `vendor/`, generated docs)

- [ ] **`.lycheeignore`**
  - Check if file exists in repository root
  - Reference: `https://github.com/Cogni-AI-OU/.github/blob/main/.lycheeignore`
  - Purpose: URL patterns to exclude from link checking with lychee
  - Action: Create if missing with standard ignore patterns
  - Standard patterns: localhost, 127.0.0.1, example.com URLs, placeholder GitHub URLs
  - Customize: Add URLs that require authentication or block automated requests
  - Note: Supports regular expressions (one expression per line)
  - Note: Don't add blocked URLs there as a workaround to pass linters

- [ ] **`.markdown-link-check.json`**
  - Check if file exists in repository root
  - Reference: `https://github.com/Cogni-AI-OU/.github/blob/main/.markdown-link-check.json`
  - Purpose: Configuration for markdown-link-check to customize link validation behavior
  - Action: Create if missing with standard configuration
  - Standard settings: timeout, ignorePatterns for localhost/example.com, retryOn429, aliveStatusCodes
  - Customize: Add repository-specific ignore patterns, timeout values, or HTTP headers
  - Note: Supports JSON configuration with regex patterns, replacement patterns, and status code handling
  - Note: Don't add blocked URLs there as a workaround to pass linters

- [ ] **`.yamllint`**
  - Check if file exists in repository root
  - Reference: `https://github.com/Cogni-AI-OU/.github/blob/main/.yamllint`
  - Purpose: YAML linting rules for consistent YAML formatting
  - Action: Create if missing; update if exists to match organization standards
  - Key rules: 120 char line length, 2-space indentation, explicit booleans, 1 space inside braces

- [ ] **`.yamlfix.toml`**
  - Check if file exists in repository root
  - Reference: `https://github.com/Cogni-AI-OU/.github/blob/main/.yamlfix.toml`
  - Purpose: YAML auto-fixing configuration
  - Action: Create if missing
  - Key settings: 110 char line length, preserve block scalars and formatting

### Phase 3: GitHub Workflows (CI/CD)

- [ ] **`.github/workflows/check.yml`**
  - Check if file exists
  - Reference: `https://github.com/Cogni-AI-OU/.github/blob/main/.github/workflows/check.yml`
  - Purpose: Runs pre-commit checks and actionlint in CI
  - Action: Create using `workflow_call` to reference the remote workflow
  - Implementation:

    ```yaml
    ---
    # Note: Keep keys and envs in alphabetical order.
    name: Check
    # yamllint disable-line rule:truthy
    on:
      pull_request:
      push:
      schedule:
        - cron: 0 0 * * 1  # Run every Monday at 00:00 UTC
      workflow_dispatch:
    permissions:
      contents: read
    jobs:
      check:
        uses: Cogni-AI-OU/.github/.github/workflows/check.yml@main
        with:
          submodules: 'false'  # Set to 'true' or 'recursive' if repository uses submodules
    ```

  - Note: Uses the organization's reusable `check.yml` workflow to run actionlint and pre-commit checks.

  - Customize: Add additional jobs if needed for project-specific checks

- [ ] **`.github/workflows/cogni-ai-agent.yml`**
  - Check if file exists
  - Reference: `https://github.com/Cogni-AI-OU/.github/blob/main/.github/workflows/cogni-ai-agent.yml`
  - Purpose: Logic for the Cogni AI Agent
  - Action: Create as a standalone workflow

  - Note: Requires `OPENCODE_API_KEY` secret to be set in repository settings.
    You must also install the [GitHub OpenCode app](https://github.com/apps/opencode-agent)
    or follow the [manual setup guide](https://opencode.ai/docs/github/#manual-setup).

- [ ] **`.github/workflows/devcontainer-ci.yml`**
  - Check if file exists (only if `.devcontainer/` directory exists)
  - Reference: `https://github.com/Cogni-AI-OU/.github/blob/main/.github/workflows/devcontainer-ci.yml`
  - Purpose: Tests devcontainer builds and validates required tools
  - Action: Create using `workflow_call` to reference the remote workflow
  - Implementation:

    ```yaml
    ---
    name: Development Containers (CI)
    # yamllint disable-line rule:truthy
    on:
      pull_request:
        paths:
          - .devcontainer/**
          - .github/workflows/devcontainer-ci.yml
      push:
        branches:
          - main
        paths:
          - .devcontainer/**
      schedule:
        - cron: 0 0 * * 1  # Run every Monday at 00:00 UTC
      workflow_dispatch:

    concurrency:
      group: ${{ github.workflow }}-${{ github.ref }}
      cancel-in-progress: true

    jobs:
      devcontainer-build:
        uses: Cogni-AI-OU/.github/.github/workflows/devcontainer-ci.yml@main
        permissions:
          contents: read
          packages: write  # Required for pushing to GitHub Container Registry
    ```

  - Note: The `packages: write` permission is **required** for the workflow to push container images to GHCR
  - Customize: Add repository-specific required commands/packages via workflow inputs:

    ```yaml
    jobs:
      devcontainer-build:
        uses: Cogni-AI-OU/.github/.github/workflows/devcontainer-ci.yml@main
        permissions:
          contents: read
          packages: write
        with:
          required_commands: 'docker npm python3'
          required_python_packages: 'ansible pre-commit'
    ```

- [ ] **`.github/actionlint-matcher.json`**
  - Check if file exists
  - Reference: `https://github.com/Cogni-AI-OU/.github/blob/main/.github/actionlint-matcher.json`
  - Purpose: GitHub Actions problem matcher for actionlint output
  - Action: Copy from reference if missing

- [ ] **`.github/pre-commit-matcher.json`**
  - Check if file exists
  - Reference: `https://github.com/Cogni-AI-OU/.github/blob/main/.github/pre-commit-matcher.json`
  - Purpose: GitHub Actions problem matcher for pre-commit output
  - Action: Copy from reference if missing

- [ ] **`.github/workflows/README.md`**
  - Check if file exists
  - Reference: `https://github.com/Cogni-AI-OU/.github/blob/main/.github/workflows/README.md`
  - Purpose: Documentation for GitHub Actions workflows in the repository
  - Action: Create if missing; if exists, **MERGE** organization standards while **PRESERVING**
    existing documentation for repository-specific workflows
  - Content: Workflow descriptions, usage examples, inputs/outputs, security considerations
  - Customize: Add documentation for any custom workflows specific to the repository

- [ ] **`.github/workflows/AGENTS.md`**
  - Check if file exists
  - Reference: `https://github.com/Cogni-AI-OU/.github/blob/main/.github/workflows/AGENTS.md`
  - Purpose: Agent instruction file describing workflows, triggers, and inputs
  - Action: Create if missing; update when workflows are added, removed, or renamed

- [ ] **`.github/prompts/` directory**
  - Check if directory exists with prompt files
  - Reference: `https://github.com/Cogni-AI-OU/.github/tree/main/.github/prompts`
  - Purpose: Prompt templates for GitHub Models and Copilot
  - Action: Include relevant prompt files; keep formats (Markdown/YAML) as upstream
  - Available prompts:
    - `default.prompt.yml` - Default prompt for cogni-ai-agent workflow
    - `pr-review.prompt.md` - PR review prompt
    - `repository-setup.prompt.md` - This setup prompt
    - `test.prompt.yml` - Example prompt
  - Customize: Add prompts for repository-specific tasks as needed

- [ ] **`.github/prompts/AGENTS.md`**
  - Check if file exists
  - Reference: `https://github.com/Cogni-AI-OU/.github/blob/main/.github/prompts/AGENTS.md`
  - Purpose: Agent instruction file describing workflows, triggers, and inputs
  - Action: Create if missing; update when prompts change

### Phase 4: Development Container Configuration

- [ ] **`.devcontainer/devcontainer.json`**
  - Check if `.devcontainer/` directory and file exist
  - Reference: `https://github.com/Cogni-AI-OU/.github/blob/main/.devcontainer/devcontainer.json`
  - Purpose: Defines containerized development environment
  - Action: If file exists, review and update to match organization standards; create if missing
  - Key features: Python, Docker-in-Docker, actionlint, node, make, ripgrep
  - Customize: Add language-specific features and VS Code extensions as needed

- [ ] **`.devcontainer/requirements.txt`**
  - Check if file exists (if `.devcontainer/` exists)
  - Reference: `https://github.com/Cogni-AI-OU/.github/blob/main/.devcontainer/requirements.txt`
  - Purpose: Python dependencies for devcontainer
  - Action: If file exists, verify it contains base packages; create with base requirements if missing
  - Base packages: docker, pre-commit, uv
  - Customize: Add project-specific Python packages (keep existing project packages)

- [ ] **`.devcontainer/requirements-ansible.txt`**
  - Check if file exists (if `.devcontainer/` exists)
  - Reference: `https://github.com/Cogni-AI-OU/.github/blob/main/.devcontainer/requirements-ansible.txt`
  - Purpose: Ansible-specific Python dependencies
  - Action: Create if missing; verify it contains ansible-core and other required modules
  - Base packages: ansible-core, requests

- [ ] **`.devcontainer/apt-packages.txt`**
  - Check if file exists (if `.devcontainer/` exists)
  - Reference: `https://github.com/Cogni-AI-OU/.github/blob/main/.devcontainer/apt-packages.txt`
  - Purpose: System packages to install in devcontainer
  - Action: Create with base packages; merge if exists
  - Base packages: coreutils, gh, git, mawk, sed, time, vim
  - This file must be created because devcontainer.json references it in `onCreateCommand`
  - Customize: Add project-specific system dependencies

### Phase 5: Code Tours and Documentation

- [ ] **`.tours/README.md`**
  - Check if `.tours/` directory and file exist
  - Reference: `https://github.com/Cogni-AI-OU/.github/blob/main/.tours/README.md`
  - Purpose: Documentation for VS Code code tours
  - Action: Create if missing; customize for repository-specific tours
  - Content: What are code tours, how to use them, available tours list
  - Customize: Update the "Available Tours" section with repository-specific tour descriptions

- [ ] **`.tours/getting-started.tour`**
  - Check if `.tours/` directory and file exist
  - Reference: `https://github.com/Cogni-AI-OU/.github/blob/main/.tours/getting-started.tour`
  - Purpose: VS Code guided tour for new contributors
  - Action: Create if missing; this should be customized for the specific repository
  - Content: Overview of repository structure, key files, development workflows
  - Format: JSON file following CodeTour schema
  - Note: Use the code-tour agent to create repository-specific tours
  - Reference: The code-tour agent documentation is available in the runtime agents catalog.
  - Action: Reference the agent when creating tours: "Use the Code Tour Expert agent to create a getting-started tour"

- [ ] **Create or update repository README.md**
  - Check if `README.md` exists
  - Reference: The README instructions are available in the runtime instructions catalog.
  - Purpose: Main documentation for repository
  - Action: Ensure it follows organization standards while **PRESERVING** and **INTEGRATING**
    with existing project-specific documentation (DO NOT delete project descriptions or usage guides)
  - Required sections: Project overview, getting started, development, structure, contributing, license
  - Badges: Add PR reviews, license (TLDRLegal link), tags, build status
  - Validation: Run `pre-commit run markdownlint -a` after updates

### Phase 6: GitHub Configuration Files

- [ ] **`.github/CODEOWNERS`**
  - Check if file exists
  - Reference: `https://github.com/Cogni-AI-OU/.github/blob/main/.github/CODEOWNERS`
  - Purpose: Automatic review request assignments
  - Action: Create with repository-specific owners
  - Format: File patterns mapped to team/user handles
  - Example: `* @Cogni-AI-OU/core-team`

- [ ] **`.github/CONTRIBUTING.md`**
  - Check if file exists
  - Reference: `https://github.com/Cogni-AI-OU/.github/blob/main/.github/CONTRIBUTING.md`
  - Purpose: Contribution guidelines (auto-applies from org .github if missing)
  - Action: **DO NOT** create this file in individual repositories
  - Note: This file is automatically loaded from the organization's `.github` repository. Only create
    it if a repository-specific contribution guidelines are strictly required.

- [ ] **`.github/pull_request_template.md`**
  - Check if file exists
  - Reference: `https://github.com/Cogni-AI-OU/.github/blob/main/.github/pull_request_template.md`
  - Purpose: PR template (auto-applies from org .github if missing)
  - Action: **DO NOT** create this file in individual repositories
  - Note: This file is automatically loaded from the organization's `.github` repository. Only create
    it if a repository-specific override is strictly required.

- [ ] **`.github/ISSUE_TEMPLATE/bug_report.yml`**
  - Check if `.github/ISSUE_TEMPLATE/` directory exists
  - Reference: `https://github.com/Cogni-AI-OU/.github/blob/main/.github/ISSUE_TEMPLATE/bug_report.yml`
  - Purpose: Bug report template (auto-applies from org .github if missing)
  - Action: Only create if repository needs specific issue templates
  - Note: Organization defaults are used if these don't exist

- [ ] **`.github/ISSUE_TEMPLATE/feature_request.yml`**
  - Check if file exists
  - Reference: `https://github.com/Cogni-AI-OU/.github/blob/main/.github/ISSUE_TEMPLATE/feature_request.yml`
  - Purpose: Feature request template (auto-applies from org .github if missing)
  - Action: Only create if repository needs specific issue templates

### Phase 7: Agent Configuration and Instructions

- [ ] **`AGENTS.md`**
  - Check if file exists
  - Reference: `https://github.com/Cogni-AI-OU/.github/blob/main/AGENTS.md`
  - Purpose: Quick reference for AI agents working in the repository
  - Action: Create if missing; if exists, **MERGE** organization standards while **PRESERVING**
    existing repository-specific tasks, build/test commands, and context
  - Content: Quick start, links to instructions, common tasks (linting, building, testing)
  - Customize: Include repository-specific commands, test runners, build processes

- [ ] **`.gemini/settings.json`**
  - Check if `.gemini/` directory and file exist
  - Reference: `https://github.com/Cogni-AI-OU/.github/blob/main/.gemini/settings.json`
  - Purpose: Google Gemini AI configuration
  - Action: Create if missing
  - Content: Configuration that points Gemini to use `AGENTS.md` as the context file
  - Format: JSON file with `contextFileName` property
  - Example: `{ "contextFileName": "AGENTS.md" }`

- [ ] **`.github/copilot-instructions.md`**
  - Check if file exists
  - Reference: `https://github.com/Cogni-AI-OU/.github/blob/main/.github/copilot-instructions.md`
  - Purpose: Comprehensive coding standards for GitHub Copilot
  - Action: Create if missing; if exists, **CAREFULLY MERGE** organization standards while
    **PRESERVING** valuable repository-specific guidelines or examples
  - Content: Project overview, coding standards, formatting guidelines, troubleshooting
  - Customize: Add repository-specific standards, dependencies, build/test commands

- [ ] **`.github/mcp-config.json`**
  - Check if file exists
  - Reference: `https://github.com/Cogni-AI-OU/.github/blob/main/.github/mcp-config.json`
  - Purpose: MCP server configuration for GitHub Copilot
  - Action: Create or update to org baseline
  - Update flow: Detect existing file and replace or merge with canonical org baseline
    content. Write standardized/configured content when absent or differs, flagging or
    auto-committing as appropriate.
  - Content: Configuration that provides access to built-in GitHub tools

- [ ] **`.github/AGENTS.md`**
  - Check if file exists
  - Reference: `https://github.com/Cogni-AI-OU/.github/blob/main/.github/AGENTS.md`
  - Purpose: Entry point for agent work in the `.github` directory
  - Action: Create or update to org baseline
  - Update flow: Detect existing file and replace or merge with canonical org baseline
    content. Write standardized/configured content when absent or differs, flagging or
    auto-committing as appropriate.

### Phase 8: Additional Organization Files

- [ ] **`CODE_OF_CONDUCT.md`**
  - Check if file exists
  - Reference: `https://github.com/Cogni-AI-OU/.github/blob/main/CODE_OF_CONDUCT.md`
  - Purpose: Community standards (auto-applies from org .github if missing)
  - Action: Generally not needed in individual repos; org default applies
  - Note: Only create if repository needs a different code of conduct

- [ ] **`LICENSE`**
  - Check if file exists
  - Purpose: Repository license
  - Action: Ensure license is present and appropriate
  - Common options: MIT, Apache-2.0, GPL-3.0, proprietary
  - Note: This is repository-specific; review with repository owner

### Phase 9: Validation and Testing

- [ ] **Validate all created/updated files**
  - Run pre-commit checks: `pre-commit run -a`
    - If errors occur, compare `.pre-commit-config.yaml` with upstream to ensure all required hooks are present
    - Then fix any remaining linting errors reported by the hooks
    - Note: In case of firewall issues, don't add blocked URLs to ignore list to pass the linters
    Otherwise fix any reported linting errors found
  - Ensure all YAML files are valid: `yamllint .`
  - Ensure all Markdown files are valid: `markdownlint **/*.md`
  - Ensure GitHub Actions workflows are valid: `actionlint .github/workflows/*.yml`

- [ ] **Test workflows (if possible)**
  - Create a test branch
  - Create a test PR to trigger workflows
  - Verify check workflow runs successfully
  - Verify devcontainer builds successfully (if configured)

- [ ] **Update or create repository documentation**
  - Ensure README.md documents new configuration files
  - Add section about pre-commit hooks and how to use them
  - Document any required secrets (e.g., `OPENCODE_API_KEY`)
  - Add badge to README for build status

- [ ] **Create summary report**
  - List all files created
  - List all files updated
  - List any files that couldn't be created (with reasons)
  - List any repository-specific customizations needed
  - Note any manual steps required (e.g., setting secrets)

## Important Notes

### File References and Organization Repository

When working with this prompt, you may encounter references to files that don't exist in the target
repository. Before creating new files, always check if they already exist in the organization's `.github`
repository at `https://github.com/Cogni-AI-OU/.github`. Many files are meant to be copied or referenced
from the organization repository rather than created from scratch. This ensures consistency across all
repositories and reduces maintenance overhead.

### Remote Workflow References

When creating GitHub Actions workflows, use `workflow_call` to reference workflows from the organization's
`.github` repository. This ensures:

- Consistency across repositories
- Easier maintenance (updates in one place)
- Reduced duplication

Example pattern:

```yaml
jobs:
  job-name:
    uses: Cogni-AI-OU/.github/.github/workflows/workflow-name.yml@main
    secrets: inherit
```

### Repository-Specific Customizations

While standardization is important, repositories may need customizations for:

- Language-specific linting tools
- Framework-specific build processes
- Special dependencies or requirements
- Project-specific workflows

When customizing:

1. Start with the organization template
2. Add repository-specific requirements
3. Document customizations in README.md or AGENTS.md
4. Maintain compatibility with organization standards where possible

### Secrets Management

Some workflows require secrets to be configured in repository settings:

- `OPENCODE_API_KEY` - Required for Cogni AI Agent workflows
- Add others as needed for specific integrations

Document required secrets in README.md or a SECRETS.md file.

### Pre-commit Installation

After creating `.pre-commit-config.yaml`, remind users to install hooks:

```bash
pip install pre-commit
pre-commit install
```

This should be documented in README.md under development setup.

### Language-Specific Considerations

#### Python Projects

- Add `black`, `flake8`, `mypy` to pre-commit config
- Include `requirements.txt` or `pyproject.toml`
- Add Python version specification

#### Node.js Projects

- Add `eslint`, `prettier` to pre-commit config
- Include `.nvmrc` for Node version
- Add `package.json` scripts for lint/test/build

#### Go Projects

- Add `gofmt`, `golint` to pre-commit config
- Include `go.mod` and `go.sum`
- Document Go version requirements

#### Java Projects

- Add `checkstyle`, `spotless` configuration
- Include Maven or Gradle configuration
- Document Java version requirements

## Execution Order

Follow the phases in order:

1. **Phase 1-2**: Essential configuration (creates foundation)
2. **Phase 3**: GitHub workflows (enables CI/CD)
3. **Phase 4**: Devcontainer (optional, for containerized development)
4. **Phase 5**: Documentation (guides contributors)
5. **Phase 6**: GitHub config (templates and ownership)
6. **Phase 7**: Agent config (enables AI assistance)
7. **Phase 8**: Additional files (as needed)
8. **Phase 9**: Validation (ensures everything works)

## Success Criteria

A successful repository setup includes:

- [ ] All essential configuration files present and valid
- [ ] Pre-commit hooks configured and working
- [ ] GitHub Actions workflows configured (using remote references where possible)
- [ ] Devcontainer configured (if using containerized development)
- [ ] Documentation updated (README, AGENTS.md, etc.)
- [ ] All linters passing
- [ ] Repository follows organization standards
- [ ] Repository-specific needs addressed

## Final Deliverables

Provide:

1. **Summary Report**: List of changes made
2. **Validation Results**: Output from linting and checks
3. **Next Steps**: Any manual configuration needed (secrets, settings)
4. **Customization Notes**: Repository-specific deviations from standards

Remember: The goal is standardization with flexibility. Use the organization `.github` repository as a
template, but adapt to each repository's specific needs while maintaining consistency where possible.
