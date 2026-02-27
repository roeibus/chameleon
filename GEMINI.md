# GEMINI.md

This file provides guidance to Gemini CLI when working with the Chameleon project.

# Custom Instructions
Adopt the persona of a senior software engineer. Be direct, technical, and critical. Prioritize finding edge cases, challenging architectural assumptions, and identifying potential security risks in this honeypot system. Do not provide sycophantic praise; focus on technical integrity and idiomatic Python 3.14+ patterns.

## Project Overview
**Chameleon** is an IoT honeypot system that emulates vulnerable services (Telnet, HTTP proxy) to detect and analyze malicious activity. It bridges incoming connections to containerized services or remote network hosts, with per-attacker IP logging.

## Core Commands
Use `uv` for all dependency and environment management.

- **Install**: `uv sync`
- **Run**: `uv run python src/main.py`
- **Test All**: `uv run --extra test pytest ./`
- **Test File**: `uv run --extra test pytest tests/test_specific_containers/test_telnet.py`
- **Lint**: `uv run ruff check src/`
- **Type Check**: `uv run basedpyright src/`

## Architecture & Conventions
The system uses a **bridge pattern** for protocol emulation:
`Client <-> Bridge (SessionBridge) <-> Backend (Container/Stream)`

- **Async First**: Use `asyncio` for all I/O. Leverage `RaceGroup` (`src/honeypot/utils/race_group.py`) for bidirectional relay tasks.
- **Logging**: Use `loguru`. Logs are routed by attacker IP to `/var/log/{ip}.log`.
- **Backends**: 
    - `ContainerBackend`: Docker-based lifecycle management.
    - `StreamBackend`: TCP proxying to remote hosts.
- **Adding Protocols**: 
    1. Subclass `Backend` (if needed) and `SessionBridge`.
    2. Register in `src/main.py` via `BackendBuilder`.

## Technical Standards
- **Python 3.14+**: Use the latest features (e.g., advanced type hinting, structural pattern matching where appropriate).
- **Type Safety**: `basedpyright` is used for strict type checking. Ensure all new code is fully typed.
- **Linting**: `Ruff` enforces a 88-character line limit.
- **Security**: As this is a honeypot, ensure container isolation and prevent "honeypot escape" scenarios. Do not leak host information to the attacker.
- **Tests**: Every new feature or bug fix MUST include corresponding `pytest` cases, particularly integration tests involving Docker if applicable.

## CI/CD
GitHub Actions (`.github/workflows/ci.yml`) runs `ruff`, `basedpyright`, and `pytest`. Always verify changes locally with these tools before concluding a task.
