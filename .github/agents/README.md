# Custom Agents

This folder contains custom agents designed to enhance your development workflow.
These agents are tailored to specific tasks and integrate seamlessly with GitHub Copilot and MCP servers.

## Available Agents

### [Copilot Plus](copilot-plus.agent.md)

Enhanced agent with critical thinking, robust problem-solving, and context-aware resource management. Features:

- Automatic file size checking before viewing
- Smart filtering for long outputs
- Command installation fallback logic
- Self-improvement capabilities
- Never-give-up problem-solving approach

### [Code Tour Expert](code-tour.agent.md)

Specialized agent for creating and maintaining VSCode CodeTour files. Use this agent for:

- Creating `.tours/` files with proper CodeTour schema
- Designing step-by-step walkthroughs for complex codebases
- Implementing interactive tours with command links and code snippets
- Setting up primary tours and tour linking sequences

**When to use**: Anytime you need to create or update `.tour` files for repository onboarding.

## How to Use Custom Agents

### Using Agents in VS Code

Reference agents in your Copilot chat using the agent's name or description. For example:
"@workspace Use the Code Tour Expert agent to create a getting-started tour"

### Using Agents in GitHub (Claude Code)

Custom agents are available when using `@claude` in comments on PRs and issues. The workflows
automatically provide agent instructions to Claude based on the task context.

## Reference Documentation

- [About custom agents](https://docs.github.com/en/copilot/concepts/agents/coding-agent/about-custom-agents)
- [Create custom agents](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/coding-agent/create-custom-agents)
- [Copilot CLI](https://gh.io/customagents/cli)
- [GitHub Awesome Copilot repository](https://github.com/github/awesome-copilot)

## Customizing Development Environment

See: [Customizing the development environment for GitHub Copilot coding agent][customize-env]

## Firewall Configuration

See: [Customizing or disabling the firewall for GitHub Copilot coding agent][firewall-config]

<!-- Named links -->

[customize-env]: https://docs.github.com/en/copilot/how-tos/use-copilot-agents/coding-agent/customize-the-agent-environment
[firewall-config]: https://gh.io/copilot/firewall-config
