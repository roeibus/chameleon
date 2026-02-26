# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Custom Instructions
You are a senior software engineer reviewing my work. Do not act as a sycophant. Never agree with me just to be polite or helpful. Your primary goal is to find edge cases, point out bad architectural decisions, and challenge my assumptions. If my approach is flawed, tell me directly and bluntly why it's bad before offering any code.

## Project Overview

This is an IoT honeypot system ("Chameleon") that emulates vulnerable services (Telnet, HTTP proxy) to detect and analyze malicious activity. It bridges incoming connections to containerized services or remote network hosts, logging all interactions per attacker IP.

## Commands

```bash
# Install dependencies
uv sync

# Run the honeypot
uv run python src/main.py

# Run all tests
uv run --extra test pytest ./

# Run a single test file
uv run --extra test pytest tests/test_client.py

# Lint
uv run ruff check src/

# Type check
uv run basedpyright src/
```

## Architecture

The system follows a **bridge pattern** with modular backends:

```
Client → Bridge (TelnetBridge / HttpProxyBridge)
              ↓
         SessionBridge (base abstraction)
              ↓
         Backend (ContainerBackend or StreamBackend)
              ↓
    Docker Container OR Remote TCP Host
```

**Key components:**

- `src/main.py` — Entry point. Configures hosts/ports, starts async servers for Telnet (port 2323) and HTTP proxy (port 8080).
- `src/honeypot/backend.py` — Abstract async context manager `Backend` with `read()`/`write()` interface.
- `src/honeypot/bridge.py` — Abstract `SessionBridge` base. Manages the bidirectional data relay and per-IP logging.
- `src/honeypot/builder.py` — `BackendBuilder` factory for constructing `ContainerBackend` or `StreamBackend`.
- `src/honeypot/containers/` — Docker-based backend: `ContainerWrapper` handles container lifecycle; `TelnetBridge` emulates a login prompt via a container.
- `src/honeypot/proxy/` — TCP proxy backend: `StreamBackend` connects to a remote host; `HttpProxyBridge` forwards HTTP requests to the real IoT device.
- `src/honeypot/logger/logger.py` — Loguru setup with per-IP log routing to `/var/log/{ip}.log` (10 MB rotation, 10-day retention, zip compression).
- `src/honeypot/utils/race_group.py` — `RaceGroup` utility: runs concurrent async tasks and cancels all when the first completes (used for bidirectional relay).
- `src/honeypot/exc.py` — Custom exceptions.

**Adding a new protocol:**
1. Implement a `Backend` subclass (or reuse `ContainerBackend`/`StreamBackend`).
2. Implement a `SessionBridge` subclass with protocol-specific logic.
3. Wire it up in `main.py` using `BackendBuilder`.

## Tooling

- **Python 3.14+** required
- **uv** for dependency/environment management
- **Ruff** for linting (line length 88, `ruff.toml`)
- **basedpyright** for type checking
- **pytest-asyncio** for async tests
- **Docker** must be running for container-based tests and the Telnet honeypot

## CI/CD

GitHub Actions (`.github/workflows/ci.yml`) runs on pull requests with three parallel jobs:
1. **ruff**: `ruff check src/`
2. **basedpyright**: `basedpyright src/`
3. **test**: `pytest ./`
