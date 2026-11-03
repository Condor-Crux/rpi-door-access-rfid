# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - Initial Scaffolding Phase
This project is currently in the initial scaffolding and documentation phase. No core Python code has been executed or committed yet.

### Added
- **Core Configuration:**
  - `.gitignore` optimally configured for Python, FastAPI, SQLite, and IDE environments.
  - Minimalistic `README.md`.
  - Environmental setup with secure `.env` separation (`.env.example` committed securely with `ADMIN_PASSWORD` and `JWT` keys as placeholders).
- **AI Agent Infrastructure:**
  - `AGENTS.md` to regulate AI coding behaviors based on the open standard.
  - `skills.sh` as a dedicated bash skill entry point/dispatcher.
  - `/skills/` folder containing systemic tools (`check_solid_compliance.sh`), configuration rules, and boilerplate code generation templates (`hardware_interface.md`).
- **Software Design Documentation (SDD):**
  - `docs/PRD.md`: Outlining the entire workflows for Hardware and Access constraints (Credits checking, Expiry parsing, Relay trigger lengths).
  - `docs/ADRs/0001-initial-architecture.md`: Solidifying FastAPI, SQLite, and hardware abstractions.
  - `docs/ADRs/0002-glossary-and-nomenclature.md`: The SSOT connecting Domain code semantics locally mapped to colloquials.
  - `docs/ADRs/0003-git-and-github-workflow.md`: Strict CI/CD baseline relying on GitHub Flow and Conventional Commits.
