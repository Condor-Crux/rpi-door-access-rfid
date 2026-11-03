# AI Agent Skills Infrastructure

This directory contains executable scripts ("skills"), templates, and context files designed explicitly to be consumed and executed by AI coding assistants.

The central entry point is the `./skills.sh` dispatcher at the root of the project.

## Directory Structure
- `/skills/system/`: Core systemic tools for the AI (e.g., verifying context, checking standards).
- `/skills/templates/`: Markdown and Code templates (e.g., scaffolding a new hardware interface).
- `/skills/domain/`: Tools specifically meant to interact with our IoT domains.

## How Agents Use Skills
Agents should run `./skills.sh` without arguments to see available commands.
For example:
```bash
./skills.sh system/check_solid_compliance.sh
```

## Adding a New Skill
1. Create an executable bash or python script inside the `skills/` hierarchy.
2. Grant it execute permissions (`chmod +x`).
3. The `skills.sh` dispatcher will automatically pick it up.
