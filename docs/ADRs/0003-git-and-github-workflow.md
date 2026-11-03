# ADR 0003: Version Control and GitHub Workflow

## Status
Accepted

## Context
To ensure a clean history and facilitate automated deployments, code review by AI agents, and CI/CD pipelines, we must define a strict workflow for how code is committed, formatted, versioned, and pushed to GitHub. This prevents messy commit logs and standardizes interactions with version control so there are **zero deviations**.

## Decisions

### 1. Commit Message Format (Conventional Commits)
All commit messages **MUST** follow the Conventional Commits specification. This allows automated changelog generation and deterministic history parsing.

**Format:**
`<type>(<optional scope>): <description>`

**Allowed Types:**
- `feat`: A new feature (e.g., `feat(api): add endpoint for uploading RFID codes`).
- `fix`: A bug fix (e.g., `fix(hardware): resolve relay overlapping timeout`).
- `docs`: Documentation changes (e.g., `docs(adr): add git workflow specifications`).
- `style`: Changes that do not affect the meaning of the code (formatting, linting).
- `refactor`: A code change that neither fixes a bug nor adds a feature.
- `test`: Adding missing tests or correcting existing tests.
- `chore`: Changes to the build process, scripts, or auxiliary tools (e.g., `chore: update skills.sh`).

### 2. Branching & Merging Strategy (GitHub Flow)
We will follow a simplified, highly robust GitHub Flow.
- **`main`**: The definitive, production-ready representation of the system. The Raspberry Pi will pull directly from this branch (or tagged releases of it). Code pushed here must be functional and passing all checks.
- **Feature Branches (`feat/*`, `fix/*`, `chore/*`)**: All development happens in isolated branches branching off `main`.
- **Pull Requests (PRs)**: 
  - Code merges into `main` **only** via PRs. 
  - PRs must be squashed when merged (`Squash and merge`). This keeps the `main` branch timeline linear, where each commit equals one atomic feature or fix.

### 3. CI/CD & Automated Skill Verification
Before any code is accepted or committed, it must pass the AI infrastructure baseline:
- Code must comply with SOLID guidelines (verified via `/skills/system/check_solid_compliance.sh`).
- Tests must pass. 
- A GitHub Action CI workflow (to be implemented) will enforce these checks automatically on all Pull Requests.

### 4. Versioning Strategy (Semantic Versioning)
We adhere to **Semantic Versioning (SemVer) 2.0.0** (`MAJOR.MINOR.PATCH`).
- **MAJOR**: Breaking changes to the API or Hardware structure.
- **MINOR**: New features (like AWS Sync) added in a backward-compatible manner.
- **PATCH**: Backward-compatible bug fixes.
- Releases will be tagged in GitHub (e.g., `v1.0.0`) marking stable milestones for Raspberry Pi deployment.

### 5. Security and Secrets Management
**ZERO TOLERANCE** for checked-in secrets.
- AWS Credentials, database keys, or local passwords must NEVER be committed.
- All secrets live exclusively in `.env` files locally on the RPi. 
- The `.gitignore` acts as the first line of defense; agents must actively ensure no temporary credential files slip into commits.

## Enforcement
AI Assistants or Developers executing git functions must validate their `git commit -m` arguments against the Conventional Commits format, and must never push directly to `main` without a Pull Request context unless strictly designated during scaffolding phases.
