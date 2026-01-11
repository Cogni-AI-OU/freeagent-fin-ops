# Agent Prompts

This directory contains prompt files that can be used with AI agents (Claude Code, GitHub Copilot, etc.)
to perform standardized tasks across repositories.

## Available Prompts

### Repository Setup (`repository-setup.prompt.md`)

Comprehensive prompt for reviewing and standardizing repository structure. This prompt guides an agent
through a detailed checklist to:

- Create or update essential configuration files (`.editorconfig`, `.gitignore`, `.pre-commit-config.yaml`)
- Set up linting configurations (`.markdownlint.yaml`, `.yamllint`, `.yamlfix.toml`)
- Configure GitHub Actions workflows (using remote workflow references)
- Set up development containers (`.devcontainer/`)
- Create code tours and documentation
- Configure GitHub files (issue templates, PR templates, CODEOWNERS)
- Set up agent configuration files (`AGENTS.md`, `CLAUDE.md`, copilot instructions)

## How to Use

### With Claude Code

1. **In an Issue or PR**: Mention `@claude` and provide the prompt content or reference the file:

   ```text
   @claude Please follow the checklist in
   https://github.com/Cogni-AI-OU/.github/blob/main/.github/prompts/repository-setup.prompt.md
   to review and update this repository's configuration.
   ```

2. **Directly**: Copy the prompt content and paste it into a Claude Code conversation.

### With GitHub Copilot

1. **In VS Code Chat**: Open Copilot Chat and reference the prompt:

   ```text
   @workspace Please follow the repository setup checklist from
   .github/prompts/repository-setup.prompt.md to standardize this repository.
   ```

2. **In Pull Request**: Create a PR and ask Copilot to review using the prompt guidelines.

### Standalone Usage

You can also use these prompts with other AI tools by:

1. Reading the prompt file
2. Copying the content to your AI tool of choice
3. Adjusting as needed for your specific use case

## Customizing Prompts

Feel free to create your own prompt files for common tasks:

1. Create a new `.prompt.md` file in this directory
2. Structure it with clear sections and checklists
3. Include references to relevant documentation and templates
4. Test it with an AI agent
5. Submit a PR to add it to the organization's prompt library

## Prompt File Guidelines

When creating prompt files:

- **Use clear structure**: Organize with headers, lists, and phases
- **Include context**: Explain the purpose and background
- **Provide references**: Link to templates and documentation
- **Use checklists**: Make it easy to track progress
- **Be specific**: Include exact commands, file paths, and examples
- **Add customization notes**: Guide agents on when/how to adapt
- **Include validation steps**: Ensure work can be verified

## Examples

### Example 1: Complete Repository Setup

```text
@claude I need you to set up this repository following organization standards.
Please use the repository-setup.prompt.md checklist and:

1. Review all configuration files
2. Create missing files
3. Set up workflows using remote references
4. Configure devcontainer
5. Create documentation
6. Validate everything works

Report progress after each phase.
```

### Example 2: Partial Setup (Workflows Only)

```text
@claude Please follow Phase 3 of the repository-setup.prompt.md to add
GitHub Actions workflows to this repository. Use workflow_call to reference
remote workflows from Cogni-AI-OU/.github.
```

### Example 3: Validation Only

```text
@claude Please follow Phase 9 of repository-setup.prompt.md to validate
all configuration files in this repository. Run linters and report any issues.
```

## Contributing

To contribute new prompts or improve existing ones:

1. Fork the repository
2. Create or update prompt files in `.github/prompts/`
3. Test the prompt with an AI agent
4. Update this README if adding a new prompt
5. Submit a PR with your changes

## Tips for Effective Prompts

- **Be explicit**: Don't assume the agent knows context
- **Use examples**: Show what you want, don't just describe it
- **Break into phases**: Make complex tasks manageable
- **Include validation**: Help agents verify their work
- **Reference standards**: Link to style guides and templates
- **Allow flexibility**: Balance standardization with customization

## Additional Resources

- [AGENTS.md](../../AGENTS.md) - General agent guidance
- [CLAUDE.md](../../CLAUDE.md) - Claude-specific configuration
- [Copilot Instructions](../copilot-instructions.md) - Coding standards
- [GitHub Actions Workflows](../workflows/) - Reusable workflows
- [Instructions](../instructions/) - Language-specific guidelines
