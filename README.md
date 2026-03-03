# Chameleon

An IoT honeypot that emulates vulnerable network services (Telnet, SSH, HTTP proxy) to detect and analyze malicious activity. Each attacker session is bridged to an isolated Docker container or remote TCP host, with all interactions logged per attacker IP.

## Features

- **Multi-protocol support** — Telnet, SSH, and HTTP proxy emulation
- **Container isolation** — Each connection spawns a fresh Docker container with strict resource limits (memory, CPU, PID, network)
- **Per-IP logging** — All session data written to separate log files per attacker IP using loguru
- **Prometheus metrics** — Active sessions, connection counts, and bytes transferred per protocol
- **Connection limiting** — Semaphore-based per-protocol connection caps
- **Resilient supervision** — Exponential backoff restart on server crash, graceful SIGINT/SIGTERM shutdown
- **Secure Docker access** — `docker-socket-proxy` restricts the honeypot to only build images and manage containers

## Architecture

```
Client → Protocol Bridge (TelnetBridge / SshBridge / HttpProxyBridge)
              ↓
         SessionBridge (base abstraction)
              ↓
         Backend (ContainerBackend or StreamBackend)
              ↓
    Docker Container OR Remote TCP Host
```

**Key components:**

| Path | Description |
|------|-------------|
| `src/main.py` | Entry point — configures services, starts servers |
| `src/honeypot/backends/` | `ContainerBackend` and `StreamBackend` implementations |
| `src/honeypot/core/backend/` | `Backend` interface and `BackendFactory` ABC |
| `src/honeypot/core/bridge/` | `ProtocolServer` and `SessionBridge` base classes |
| `src/honeypot/core/builder/` | `BackendBuilder` and factory implementations |
| `src/honeypot/protocols/` | `TelnetBridge`, `SshBridge`, `HttpProxyBridge` |
| `src/honeypot/config/` | Pydantic settings and service config models |
| `src/honeypot/logger/logger.py` | Loguru setup with per-IP log routing |
| `src/honeypot/core/metrics.py` | Prometheus metrics and HTTP server |
| `src/honeypot/core/runner.py` | `HoneypotRunner` with backoff and signal handling |
| `src/honeypot/utils/race_group.py` | `RaceGroup` — cancels all tasks when the first completes |

## Requirements

- Python 3.14+
- [uv](https://github.com/astral-sh/uv)
- Docker (running daemon)

## Installation

```bash
git clone <repo-url>
cd chameleon
uv sync
```

## Running

### Directly

```bash
uv run python src/main.py
```

### With Docker Compose (recommended)

```bash
docker-compose up -d
```

This starts two containers:
- **docker-proxy** — restricts Docker socket access to only what the honeypot needs
- **chameleon** — the honeypot itself

Default exposed ports:

| Port | Service |
|------|---------|
| 2323 | Telnet |
| 2222 | SSH |
| 8080 | HTTP Proxy |
| 9090 | Prometheus metrics |

## Configuration

Configuration is handled via environment variables (pydantic-settings). All variables are prefixed with `CHAMELEON_`.

| Variable | Default | Description |
|----------|---------|-------------|
| `CHAMELEON_BIND_HOST` | `0.0.0.0` | Address to bind all servers |
| `CHAMELEON_LOG_DIR` | `/var/log/chameleon` | Directory for log files |
| `CHAMELEON_ENABLE_METRICS` | `true` | Enable Prometheus metrics server |
| `CHAMELEON_METRICS_HOST` | `127.0.0.1` | Metrics server bind address |
| `CHAMELEON_METRICS_PORT` | `9090` | Metrics server port |
| `CHAMELEON_CONTAINER_SERVICES` | See below | JSON list of container service configs |
| `CHAMELEON_PROXY_SERVICES` | `[]` | JSON list of HTTP proxy service configs |

### Container service config

```json
[
  {
    "protocol": "telnet",
    "listen_port": 2323,
    "max_connections": 100,
    "mem_limit": "128m",
    "cpu_period": 100000,
    "cpu_quota": 50000,
    "pids_limit": 64
  },
  {
    "protocol": "ssh",
    "listen_port": 2222,
    "max_connections": 100
  }
]
```

### HTTP proxy service config

```json
[
  {
    "protocol": "http_proxy",
    "listen_port": 8080,
    "target_host": "example.com",
    "target_port": 80,
    "max_connections": 100
  }
]
```

## Logging

Logs are written to three sinks:

- **Stderr** — colored INFO+ output
- **`{LOG_DIR}/chameleon.log`** — central log (10 MB rotation, 10-day retention, zip compressed)
- **`{LOG_DIR}/{attacker_ip}.log`** — per-IP session log (same rotation policy)

All log records include the attacker's IP and the protocol bridge name as structured fields.

## Metrics

Prometheus metrics are exposed at `http://{METRICS_HOST}:{METRICS_PORT}/metrics`.

| Metric | Type | Description |
|--------|------|-------------|
| `chameleon_active_sessions` | Gauge | Currently active sessions by protocol |
| `chameleon_connections_total` | Counter | Total connections (labels: `protocol`, `status`) |
| `chameleon_bytes_total` | Counter | Bytes transferred (labels: `protocol`, `direction`) |
| `chameleon_backend_up` | Gauge | Backend health — 1 up, 0 down (labels: `protocol`, `backend_type`) |

## Development

```bash
# Install all extras
uv sync --extra dev --extra test

# Lint
uv run ruff check src/

# Type check
uv run basedpyright src/

# Run all tests
uv run --extra test pytest ./

# Run a single test file
uv run --extra test pytest tests/test_client.py
```

Integration tests require a running Docker daemon. Tests that need Docker are marked `@pytest.mark.integration` and are skipped automatically if Docker is unavailable.

## Adding a New Protocol

1. Implement a `Backend` subclass, or reuse `ContainerBackend`/`StreamBackend`.
2. Implement a `SessionBridge` subclass with protocol-specific `greet()` and `_handle_client()` logic.
3. Add a corresponding `BackendFactory` if needed.
4. Register it in `src/main.py` under `BRIDGE_CLASSES` and wire up the builder.

## CI/CD

GitHub Actions runs three parallel jobs on every pull request:

1. **ruff** — `ruff check src/`
2. **basedpyright** — `basedpyright src/`
3. **pytest** — `pytest ./`

All jobs run on Python 3.14.