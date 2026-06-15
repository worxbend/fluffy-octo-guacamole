# Frostfire Backend Implementation Plan

## 1. Project Goal

Implement a production-quality Python backend service for the Frostfire project.

Frostfire is an ESP32-based remote PC power-control system. The ESP32 controls a relay module connected to the PC motherboard power-button pins. The backend must expose a clean HTTP API that allows trusted clients to request PC power actions such as short press, long press, status query, health check, and optional scheduling.

The backend is responsible for:

1. Exposing a secure HTTP API.
2. Communicating with the ESP32 device over Wi-Fi.
3. Abstracting relay-level operations into domain-level PC power actions.
4. Providing safe command execution semantics.
5. Preventing accidental repeated relay triggers.
6. Logging, monitoring, and auditing control actions.
7. Being maintainable, testable, and suitable for Linux deployment.

The backend must be implemented in Python using `asyncio`.

---

## 2. Core Architecture

Use a layered architecture.

```text
HTTP Client
    |
    v
Python asyncio HTTP API Server
    |
    +--> API Layer
    |       - request validation
    |       - authentication
    |       - response formatting
    |
    +--> Application Layer
    |       - use cases
    |       - command orchestration
    |       - safety policies
    |
    +--> Domain Layer
    |       - PC power actions
    |       - relay command model
    |       - device status model
    |
    +--> Infrastructure Layer
            - ESP32 HTTP client
            - configuration loader
            - logging
            - persistence, if enabled
```

The backend must not expose raw relay toggling as the primary public API. It should expose safe PC-oriented actions.

Examples:

```text
POST /api/v1/power/press
POST /api/v1/power/force-off
GET  /api/v1/device/status
GET  /api/v1/health
```

The relay is only an implementation detail.

---

## 3. Technology Requirements

Use Python 3.12+.

Preferred stack:

```text
aiohttp
pydantic
pydantic-settings
structlog or logging
pytest
pytest-asyncio
ruff
mypy
coverage
```

Recommended HTTP framework:

```text
aiohttp.web
```

Reason: it is native to `asyncio`, lightweight, explicit, and suitable for a small control-plane service.

Do not use Flask.

Do not use synchronous HTTP clients.

Use:

```text
aiohttp.ClientSession
```

for communication with the ESP32.

---

## 4. Repository Structure

Use this structure:

```text
frostfire-backend/
  pyproject.toml
  README.md
  LICENSE
  .gitignore
  .env.example

  src/
    frostfire/
      __init__.py

      main.py
      app.py

      config/
        __init__.py
        settings.py

      api/
        __init__.py
        routes.py
        handlers.py
        middleware.py
        errors.py
        schemas.py

      application/
        __init__.py
        power_service.py
        safety_policy.py
        device_service.py

      domain/
        __init__.py
        models.py
        enums.py
        errors.py

      infrastructure/
        __init__.py
        esp32_client.py
        logging.py
        clock.py

      runtime/
        __init__.py
        lifecycle.py

  tests/
    unit/
      test_safety_policy.py
      test_power_service.py
      test_settings.py

    integration/
      test_api_power.py
      test_api_health.py
      test_esp32_client.py

  docs/
    api.md
    deployment.md
    esp32-protocol.md
    security.md
```

No god modules.

No business logic in route handlers.

No direct ESP32 calls from HTTP handlers.

---

## 5. Runtime Model

The backend is a long-running process.

It should be executable as:

```bash
frostfire-server
```

or:

```bash
python -m frostfire.main
```

The service must:

1. Load configuration.
2. Configure logging.
3. Create the ESP32 client.
4. Create application services.
5. Register HTTP routes.
6. Start the HTTP server.
7. Gracefully shut down.
8. Close all network sessions.

The application must handle `SIGINT` and `SIGTERM` correctly.

---

## 6. Configuration

Use environment-based configuration with `.env` support for local development.

Create `Settings` using `pydantic-settings`.

Required settings:

```python
APP_HOST="0.0.0.0"
APP_PORT=8080

API_TOKEN="change-me"

ESP32_BASE_URL="http://192.168.1.50"
ESP32_TIMEOUT_SECONDS=3.0

POWER_PRESS_DURATION_MS=500
FORCE_OFF_PRESS_DURATION_MS=5000

MIN_COMMAND_INTERVAL_SECONDS=2.0
COMMAND_LOCK_TIMEOUT_SECONDS=10.0

LOG_LEVEL="INFO"
```

Optional settings:

```python
CORS_ENABLED=false
CORS_ALLOWED_ORIGINS=""
ENABLE_AUDIT_LOG=true
ENABLE_OPENAPI_DOCS=false
DEVICE_NAME="frostfire-esp32-main-pc"
```

Rules:

1. Never hardcode secrets.
2. Never commit `.env`.
3. Provide `.env.example`.
4. Validate all durations and timeouts.
5. Reject invalid configuration at startup.

---

## 7. Domain Model

Create domain enums:

```python
class PowerAction(str, Enum):
    PRESS = "press"
    FORCE_OFF = "force_off"
    RESET = "reset"
```

Create device status model:

```python
class DeviceStatus(BaseModel):
    online: bool
    device_name: str | None
    ip_address: str | None
    firmware_version: str | None
    relay_state: str | None
    uptime_seconds: int | None
    rssi: int | None
```

Create command result model:

```python
class PowerCommandResult(BaseModel):
    action: PowerAction
    accepted: bool
    executed: bool
    duration_ms: int
    device_response: dict[str, Any] | None
    message: str
```

Create explicit domain exceptions:

```python
class FrostfireError(Exception): ...
class DeviceUnavailableError(FrostfireError): ...
class CommandRejectedError(FrostfireError): ...
class CommandInProgressError(FrostfireError): ...
class UnsafeCommandError(FrostfireError): ...
```

Do not leak low-level HTTP client exceptions directly to API responses.

---

## 8. ESP32 Communication Contract

Assume the ESP32 exposes a small HTTP API.

The backend should support this default protocol:

```text
GET  /health
GET  /status
POST /relay/pulse
```

Expected ESP32 endpoints:

### `GET /health`

Response:

```json
{
  "status": "ok",
  "device": "frostfire-esp32",
  "firmware_version": "0.1.0"
}
```

### `GET /status`

Response:

```json
{
  "device": "frostfire-esp32",
  "firmware_version": "0.1.0",
  "relay_state": "idle",
  "uptime_seconds": 12345,
  "rssi": -55
}
```

### `POST /relay/pulse`

Request:

```json
{
  "duration_ms": 500
}
```

Response:

```json
{
  "accepted": true,
  "duration_ms": 500,
  "message": "relay pulsed"
}
```

The backend must encapsulate this protocol inside `Esp32Client`.

No route handler may manually build ESP32 URLs.

---

## 9. ESP32 Client

Implement `Esp32Client`.

Responsibilities:

1. Own one `aiohttp.ClientSession`.
2. Apply request timeout.
3. Send JSON requests.
4. Parse JSON responses.
5. Convert low-level errors into infrastructure/domain errors.
6. Provide typed methods.

Interface:

```python
class Esp32Client:
    async def health(self) -> dict[str, Any]: ...

    async def status(self) -> dict[str, Any]: ...

    async def pulse_relay(self, duration_ms: int) -> dict[str, Any]: ...

    async def close(self) -> None: ...
```

Timeout rules:

1. Connection timeout must be bounded.
2. Total request timeout must be bounded.
3. A device that does not respond must return a controlled error.
4. Do not retry relay pulse commands automatically unless explicitly configured.

Important: automatic retries for relay actions can accidentally trigger multiple power-button presses. Do not retry unsafe commands by default.

---

## 10. Application Services

Create `PowerService`.

Responsibilities:

1. Accept domain-level power actions.
2. Resolve action to relay pulse duration.
3. Apply safety policy.
4. Acquire command lock.
5. Send command to ESP32.
6. Return command result.

Pseudo-flow:

```python
async def execute_power_action(action: PowerAction) -> PowerCommandResult:
    validate_action(action)

    duration_ms = resolve_duration(action)

    await safety_policy.ensure_command_allowed(action)

    async with command_lock:
        result = await esp32_client.pulse_relay(duration_ms)

    return PowerCommandResult(...)
```

Create `DeviceService`.

Responsibilities:

1. Check backend health.
2. Check ESP32 health.
3. Fetch ESP32 status.
4. Normalize status response.

Create `SafetyPolicy`.

Responsibilities:

1. Prevent overlapping commands.
2. Enforce minimum interval between commands.
3. Reject unsupported actions.
4. Reject suspicious durations.
5. Optionally require confirmation for dangerous actions.

Rules:

```text
short press: 300-1000 ms
force off: 3000-10000 ms
minimum interval between commands: configurable, default 2 seconds
only one command may run at a time
```

---

## 11. HTTP API

Base path:

```text
/api/v1
```

### Health

```text
GET /health
```

Response:

```json
{
  "status": "ok",
  "service": "frostfire-backend",
  "version": "0.1.0"
}
```

### Readiness

```text
GET /ready
```

Checks whether the backend can reach the ESP32.

Response when ready:

```json
{
  "ready": true,
  "esp32": {
    "online": true
  }
}
```

Response when ESP32 unavailable:

```json
{
  "ready": false,
  "esp32": {
    "online": false,
    "error": "device unavailable"
  }
}
```

### Device Status

```text
GET /api/v1/device/status
```

Response:

```json
{
  "online": true,
  "device_name": "frostfire-esp32",
  "ip_address": "192.168.1.50",
  "firmware_version": "0.1.0",
  "relay_state": "idle",
  "uptime_seconds": 12345,
  "rssi": -55
}
```

### Short Power Press

```text
POST /api/v1/power/press
```

Semantics:

Equivalent to pressing the physical PC power button briefly.

Typical use:

1. Power on PC.
2. Request graceful shutdown if OS is running and ACPI handles the power button.

Response:

```json
{
  "action": "press",
  "accepted": true,
  "executed": true,
  "duration_ms": 500,
  "message": "power button pressed"
}
```

### Force Off

```text
POST /api/v1/power/force-off
```

Semantics:

Equivalent to holding the physical PC power button.

This is potentially destructive. Require explicit confirmation.

Request:

```json
{
  "confirm": true
}
```

If confirmation is missing:

```json
{
  "error": {
    "code": "confirmation_required",
    "message": "force-off requires confirm=true"
  }
}
```

### Optional: Reset

```text
POST /api/v1/power/reset
```

Only implement if hardware wiring supports reset pins separately.

Do not emulate reset using force-off and power-on unless explicitly requested.

---

## 12. Authentication

Protect all mutating endpoints.

Use bearer token authentication.

Required header:

```text
Authorization: Bearer <token>
```

Protected endpoints:

```text
POST /api/v1/power/press
POST /api/v1/power/force-off
POST /api/v1/power/reset
```

Optionally protect status endpoints too.

Authentication behavior:

```text
missing token       -> 401
invalid token       -> 403
valid token         -> request continues
```

Use constant-time token comparison:

```python
hmac.compare_digest(...)
```

Never log the token.

---

## 13. Error Response Format

All API errors must use one stable schema:

```json
{
  "error": {
    "code": "device_unavailable",
    "message": "ESP32 device is unavailable",
    "details": {}
  }
}
```

Recommended status mapping:

```text
400 bad_request
401 unauthorized
403 forbidden
404 not_found
409 command_in_progress
422 unsafe_command
503 device_unavailable
500 internal_error
```

Do not expose stack traces in HTTP responses.

Do log stack traces server-side for unexpected errors.

---

## 14. Concurrency Safety

Power commands must be serialized.

Use:

```python
asyncio.Lock
```

Inside `PowerService`.

Required behavior:

1. If one command is executing, another command should either wait briefly or fail with `409`.
2. Prefer fail-fast with `409 command_in_progress`.
3. Prevent relay pulse overlap.
4. Enforce minimum interval between successful commands.
5. Keep timestamp of last command completion.

No concurrent relay pulse commands may reach the ESP32.

---

## 15. Idempotency and Duplicate Protection

Power control is not naturally idempotent.

Do not claim that `POST /power/press` is idempotent.

Optional support:

Allow clients to provide:

```text
Idempotency-Key: <uuid>
```

If implemented:

1. Cache command result for a short TTL.
2. Return the same result for duplicate key.
3. Do not execute relay pulse twice for the same key.
4. Keep implementation simple and in-memory initially.

This feature is optional for v1.

---

## 16. Logging

Use structured logging.

Every request should log:

```text
request_id
method
path
status_code
duration_ms
remote_addr
```

Every power command should log:

```text
request_id
action
duration_ms
result
esp32_status
```

Never log:

```text
API_TOKEN
Authorization header
Wi-Fi credentials
full secret config
```

Add request ID middleware.

If incoming request has:

```text
X-Request-ID
```

reuse it.

Otherwise generate UUID.

---

## 17. Observability

Expose:

```text
GET /metrics
```

Optional for v1.

If implemented, provide simple Prometheus-compatible metrics:

```text
frostfire_requests_total
frostfire_power_commands_total
frostfire_power_command_failures_total
frostfire_esp32_request_duration_seconds
frostfire_esp32_online
```

Do not overcomplicate metrics in the first version.

---

## 18. Testing Requirements

Use `pytest` and `pytest-asyncio`.

Minimum tests:

### Settings

1. Loads valid configuration.
2. Rejects missing API token.
3. Rejects invalid durations.
4. Rejects invalid ESP32 URL.

### Safety Policy

1. Allows first command.
2. Rejects command inside minimum interval.
3. Rejects dangerous duration.
4. Requires confirmation for force-off.
5. Prevents concurrent command execution.

### ESP32 Client

Use fake aiohttp server or mocked client.

Test:

1. Successful health request.
2. Successful status request.
3. Successful relay pulse.
4. Timeout handling.
5. Non-JSON response handling.
6. 500 response handling.
7. Connection failure handling.

### HTTP API

Test:

1. `GET /health`.
2. `GET /ready` when ESP32 online.
3. `GET /ready` when ESP32 offline.
4. `POST /power/press` without token returns 401.
5. `POST /power/press` with invalid token returns 403.
6. `POST /power/press` with valid token executes command.
7. `POST /power/force-off` without confirmation returns 422.
8. Concurrent power commands return controlled response.

---

## 19. Code Quality

Use strict static and style checks.

`pyproject.toml` should configure:

```text
ruff
mypy
pytest
coverage
```

Expected commands:

```bash
ruff check .
ruff format --check .
mypy src
pytest
coverage run -m pytest
coverage report
```

Prefer type hints everywhere.

Avoid `Any` except at API boundaries or raw JSON boundaries.

Use `Final` where useful.

Avoid global mutable state.

Avoid hidden singletons.

---

## 20. Packaging

Use `pyproject.toml`.

Expose CLI entry point:

```toml
[project.scripts]
frostfire-server = "frostfire.main:main"
```

The `main()` function should start the asyncio runtime.

Example:

```python
def main() -> None:
    asyncio.run(run_server())
```

---

## 21. Deployment

Provide Linux deployment documentation.

Target deployment options:

1. Direct process.
2. systemd user service.
3. systemd system service.
4. Docker, optional.

Example systemd service:

```ini
[Unit]
Description=Frostfire Backend
After=network-online.target
Wants=network-online.target

[Service]
ExecStart=/usr/local/bin/frostfire-server
EnvironmentFile=/etc/frostfire/frostfire.env
Restart=on-failure
RestartSec=5
User=frostfire
Group=frostfire
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/frostfire /var/log/frostfire

[Install]
WantedBy=multi-user.target
```

Document firewall assumptions.

Default port:

```text
8080
```

---

## 22. Security Requirements

This backend controls physical hardware. Treat it as sensitive.

Required:

1. Bearer token authentication.
2. No unauthenticated mutating endpoint.
3. No secrets in logs.
4. Confirmation required for force-off.
5. Bounded relay durations.
6. Bounded request sizes.
7. Bounded HTTP timeouts.
8. Safe shutdown.
9. Clear audit logs for power actions.

Recommended:

1. Run only inside trusted LAN.
2. Use reverse proxy with HTTPS if exposed outside localhost.
3. Do not expose directly to the public Internet.
4. Use VPN or Tailscale/WireGuard for remote access.
5. Rotate API token if leaked.

Explicitly document that exposing the service to the public Internet is unsafe.

---

## 23. ESP32 Firmware Compatibility Notes

The backend assumes the ESP32 firmware implements:

```text
GET /health
GET /status
POST /relay/pulse
```

If current firmware does not implement this, add a compatibility layer or update firmware.

The ESP32 should itself enforce:

1. Maximum pulse duration.
2. No overlapping relay actions.
3. JSON response for every command.
4. Stable error format.
5. Optional shared secret between backend and ESP32.

Backend-side validation is mandatory, but firmware-side validation is still required.

Safety must exist on both sides.

---

## 24. API Documentation

Create `docs/api.md`.

Include:

1. Endpoint list.
2. Authentication.
3. Request examples.
4. Response examples.
5. Error examples.
6. Curl examples.

Example:

```bash
curl -X POST http://localhost:8080/api/v1/power/press \
  -H "Authorization: Bearer $FROSTFIRE_API_TOKEN"
```

Force-off example:

```bash
curl -X POST http://localhost:8080/api/v1/power/force-off \
  -H "Authorization: Bearer $FROSTFIRE_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"confirm": true}'
```

---

## 25. README Requirements

The README must include:

1. What Frostfire is.
2. Architecture diagram.
3. Hardware warning.
4. Installation.
5. Configuration.
6. Running locally.
7. Running with systemd.
8. API usage.
9. Testing.
10. Security notes.
11. ESP32 firmware expectations.
12. License.

Include a clear warning:

```text
Frostfire controls physical PC power pins through a relay.
Incorrect usage may interrupt running workloads or cause data loss.
Do not expose this service directly to the public Internet.
```

---

## 26. Implementation Order

Implement in this order:

### Phase 1: Project Skeleton

1. Create package structure.
2. Add `pyproject.toml`.
3. Add linting and typing configuration.
4. Add minimal app startup.
5. Add `GET /health`.

Acceptance:

```bash
frostfire-server
curl http://localhost:8080/health
```

returns healthy response.

### Phase 2: Configuration

1. Add `Settings`.
2. Add `.env.example`.
3. Validate all config.
4. Add tests.

Acceptance:

Invalid config fails at startup with clear error.

### Phase 3: ESP32 Client

1. Implement `Esp32Client`.
2. Add health/status/pulse methods.
3. Add timeout handling.
4. Add error mapping.
5. Add tests.

Acceptance:

Client can talk to fake ESP32 test server.

### Phase 4: Domain and Application Services

1. Add domain models.
2. Add safety policy.
3. Add `PowerService`.
4. Add `DeviceService`.
5. Add tests.

Acceptance:

Power actions are serialized and validated.

### Phase 5: HTTP API

1. Add API routes.
2. Add authentication middleware.
3. Add request ID middleware.
4. Add error middleware.
5. Add schemas.
6. Add integration tests.

Acceptance:

All API endpoints work with typed responses and stable errors.

### Phase 6: Documentation and Deployment

1. Add README.
2. Add API docs.
3. Add deployment docs.
4. Add systemd unit example.
5. Add security docs.

Acceptance:

A user can install, configure, run, and test the backend using docs only.

---

## 27. Acceptance Criteria

The implementation is complete when:

1. The server starts with valid configuration.
2. The server rejects invalid configuration.
3. `GET /health` works without ESP32 dependency.
4. `GET /ready` reports ESP32 reachability.
5. `GET /api/v1/device/status` returns normalized status.
6. `POST /api/v1/power/press` requires auth and triggers one safe relay pulse.
7. `POST /api/v1/power/force-off` requires auth and explicit confirmation.
8. Concurrent power commands cannot overlap.
9. Relay pulse durations are bounded.
10. ESP32 communication uses async HTTP only.
11. All network calls have timeouts.
12. Errors use one stable JSON format.
13. Logs contain request IDs.
14. Secrets are never logged.
15. Unit and integration tests pass.
16. `ruff`, `mypy`, and `pytest` pass.
17. README and deployment docs are complete.

---

## 28. Non-Goals for First Version

Do not implement these unless explicitly requested:

1. User accounts.
2. OAuth.
3. Public cloud access.
4. Database persistence.
5. Complex scheduling.
6. Home Assistant integration.
7. Mobile application.
8. Web frontend.
9. MQTT.
10. Wake-on-LAN fallback.
11. Multi-device orchestration.

Keep v1 focused and reliable.

---

## 29. Important Engineering Constraints

1. Prefer correctness over cleverness.
2. Prefer explicit code over magic.
3. Keep route handlers thin.
4. Keep domain logic independent from aiohttp.
5. Keep ESP32 protocol isolated.
6. Treat relay actions as dangerous side effects.
7. Never auto-retry physical power commands by default.
8. Never allow arbitrary pulse duration from public API.
9. Never expose raw relay toggle as unauthenticated endpoint.
10. Every dangerous action must be visible in logs.

---

## 30. Final Agent Instruction

Implement the Frostfire backend as a clean, typed, tested Python `asyncio` HTTP service.

The result must be production-oriented, not a toy script.

The codebase must be understandable for future maintenance, with clear naming, clear module boundaries, tests, documentation, and safe handling of physical relay commands.

Use the architecture and acceptance criteria above as the source of truth.


# Frostfire Backend Plan Addendum: uv, Libraries, and No Reinvented Infrastructure

## 1. Package and Environment Manager

Use `uv` as the mandatory Python project/package manager.

`uv` must be used for:

1. Python version management.
2. Virtual environment management.
3. Dependency resolution.
4. Lockfile generation.
5. Running development commands.
6. Packaging workflow.

Do not use raw `pip`, `pip-tools`, Poetry, Pipenv, or Conda for this project unless explicitly justified.

Required files:

```text
pyproject.toml
uv.lock
.python-version
```

Recommended Python version:

```text
3.12
```

or newer if all selected libraries support it.

Project bootstrap commands:

```bash
uv init frostfire-backend
cd frostfire-backend
uv python pin 3.12
uv sync
```

Development commands must be documented using `uv run`:

```bash
uv run frostfire-server
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy src
```

Rationale: `uv` is a modern Python package and project manager from Astral, written in Rust, and intended to handle fast dependency management and project workflows.

---

## 2. Preferred Library Stack

Use popular, maintained libraries. Do not implement framework-level functionality manually.

### HTTP API Framework

Use:

```text
fastapi
uvicorn[standard]
```

Instead of manually building the whole API layer with bare `aiohttp.web`.

FastAPI is a modern Python API framework based on standard type hints and supports async path operations. It also provides request validation, serialization, dependency injection, and OpenAPI generation.

Use FastAPI for:

1. Routing.
2. Request validation.
3. Response schemas.
4. Dependency injection.
5. Error handling.
6. OpenAPI documentation.
7. Auth dependencies.

Do not manually parse JSON request bodies unless there is a strong reason.

### ASGI Server

Use:

```text
uvicorn[standard]
```

Run locally as:

```bash
uv run uvicorn frostfire.app:create_app --factory --host 0.0.0.0 --port 8080
```

Or expose a console entry point:

```toml
[project.scripts]
frostfire-server = "frostfire.main:main"
```

### Async HTTP Client

Use:

```text
httpx
```

Use `httpx.AsyncClient` for backend-to-ESP32 communication.

HTTPX supports both sync and async APIs and provides a proper async client for outgoing HTTP requests from async applications.

Do not use:

```text
requests
urllib
raw sockets
manual HTTP parsing
```

### Configuration

Use:

```text
pydantic-settings
```

Use `BaseSettings` for typed environment configuration. Pydantic Settings is designed for loading settings from environment variables and secrets files.

### Data Validation and Schemas

Use:

```text
pydantic
```

Use Pydantic models for:

1. API request bodies.
2. API responses.
3. ESP32 response normalization.
4. Config validation.
5. Domain DTOs where useful.

### Testing

Use:

```text
pytest
pytest-asyncio
httpx
respx
pytest-cov
```

`pytest-asyncio` provides pytest support for coroutine-based asyncio tests.

Use `httpx.AsyncClient` with ASGI transport for testing FastAPI endpoints.

Use `respx` or `pytest-httpx` to mock outbound HTTPX calls to the ESP32.

### Logging

Use:

```text
structlog
```

or standard `logging` with JSON formatter.

Preferred:

```text
structlog
```

Do not hand-roll custom JSON logging.

### Retry/Timeout Policy

Use `httpx.Timeout`.

For retry behavior, prefer explicit logic or a small maintained library only for safe read-only operations.

Important:

Do not automatically retry relay pulse commands.

Read-only endpoints like ESP32 `/health` and `/status` may retry once if configured.

Mutating relay commands must be single-shot by default.

### CLI Entrypoint

Use:

```text
typer
```

only if a CLI beyond `frostfire-server` is required.

For v1, a minimal entry point is enough.

Do not build a custom CLI parser manually.

---

## 3. Required Dependency Set

Add dependencies with `uv`.

Runtime dependencies:

```bash
uv add fastapi "uvicorn[standard]" httpx pydantic pydantic-settings structlog
```

Development dependencies:

```bash
uv add --dev pytest pytest-asyncio pytest-cov respx ruff mypy
```

Optional but acceptable:

```bash
uv add --dev pre-commit
```

Potential later dependencies:

```bash
uv add prometheus-client
uv add typer
uv add orjson
```

Do not add optional dependencies prematurely.

---

## 4. Updated Repository Structure

Use FastAPI-oriented structure:

```text
frostfire-backend/
  pyproject.toml
  uv.lock
  .python-version
  README.md
  .env.example

  src/
    frostfire/
      __init__.py
      main.py
      app.py

      config/
        __init__.py
        settings.py

      api/
        __init__.py
        routes.py
        dependencies.py
        errors.py
        schemas.py

      application/
        __init__.py
        power_service.py
        device_service.py
        safety_policy.py

      domain/
        __init__.py
        models.py
        enums.py
        errors.py

      infrastructure/
        __init__.py
        esp32_client.py
        logging.py

  tests/
    unit/
    integration/
```

`app.py` owns FastAPI app creation.

`main.py` owns process startup.

Route handlers must be thin.

---

## 5. FastAPI Application Design

Implement an app factory:

```python
def create_app() -> FastAPI:
    ...
```

Use FastAPI lifespan for startup/shutdown.

Responsibilities during startup:

1. Load settings.
2. Configure logging.
3. Create one shared `httpx.AsyncClient`.
4. Create `Esp32Client`.
5. Create services.
6. Store dependencies in `app.state`.

Responsibilities during shutdown:

1. Close `httpx.AsyncClient`.
2. Flush logs if needed.

Do not create a new HTTP client per request.

---

## 6. Dependency Injection

Use FastAPI dependencies instead of global mutable state.

Example dependency shape:

```python
def get_power_service(request: Request) -> PowerService:
    return request.app.state.power_service
```

Authentication dependency:

```python
async def require_api_token(
    authorization: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
) -> None:
    ...
```

Use `hmac.compare_digest` for token comparison.

---

## 7. ESP32 Client with HTTPX

Implement `Esp32Client` using `httpx.AsyncClient`.

Required behavior:

```python
class Esp32Client:
    def __init__(self, base_url: str, client: httpx.AsyncClient) -> None:
        ...

    async def health(self) -> Esp32HealthResponse:
        ...

    async def status(self) -> Esp32StatusResponse:
        ...

    async def pulse_relay(self, duration_ms: int) -> Esp32PulseResponse:
        ...
```

Rules:

1. Use typed Pydantic response models.
2. Use bounded timeouts.
3. Convert `httpx.TimeoutException` to `DeviceUnavailableError`.
4. Convert `httpx.ConnectError` to `DeviceUnavailableError`.
5. Convert invalid JSON to `InvalidDeviceResponseError`.
6. Convert unexpected HTTP status to `DeviceProtocolError`.
7. Do not leak raw HTTPX exceptions through API handlers.

---

## 8. API Schema Rules

Use Pydantic models for every public response.

Do not return unstructured dicts from route handlers except for trivial health response.

Preferred:

```python
class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    version: str
```

Use explicit response models:

```python
@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    ...
```

---

## 9. OpenAPI

Keep FastAPI OpenAPI enabled by default for local development.

Config options:

```text
ENABLE_OPENAPI=true
```

When disabled in production:

```python
docs_url=None
redoc_url=None
openapi_url=None
```

Do not manually write OpenAPI JSON.

FastAPI must generate it from typed routes and Pydantic schemas.

---

## 10. Updated `pyproject.toml` Requirements

The agent must configure:

```toml
[project]
name = "frostfire-backend"
version = "0.1.0"
requires-python = ">=3.12"

[project.scripts]
frostfire-server = "frostfire.main:main"

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = [
  "E",
  "F",
  "I",
  "B",
  "UP",
  "SIM",
  "C4",
  "PIE",
  "RUF"
]

[tool.mypy]
python_version = "3.12"
strict = true
packages = ["frostfire"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

Use `ruff format`.

Do not use Black and Ruff formatter together.

---

## 11. No-Reinventing-Wheels Rules

The implementation must not manually implement these unless explicitly justified:

1. HTTP routing.
2. JSON body parsing.
3. Request validation.
4. Response serialization.
5. OpenAPI generation.
6. Environment config parsing.
7. Async HTTP connection pooling.
8. CLI parsing beyond a trivial entry point.
9. Test HTTP server plumbing when library test clients are enough.
10. JSON logging if a maintained formatter or `structlog` is used.

Use well-known libraries.

Keep custom code focused on Frostfire-specific domain behavior:

1. Power command semantics.
2. Relay safety policy.
3. ESP32 protocol mapping.
4. Error mapping.
5. Audit logging semantics.

---

## 12. Revised Implementation Stack

Final required stack:

```text
Python 3.12+
uv
FastAPI
Uvicorn
HTTPX
Pydantic
Pydantic Settings
Structlog
Pytest
Pytest-asyncio
RESPX or pytest-httpx
Ruff
Mypy
```

The coding agent must check current library documentation where needed and use stable public APIs.

Do not use abandoned, niche, or unnecessary dependencies.

---

## 13. Revised Acceptance Criteria

The implementation is acceptable only if:

1. Project is managed by `uv`.
2. `uv.lock` is committed.
3. Runtime dependencies are declared in `pyproject.toml`.
4. Development dependencies are declared in `pyproject.toml`.
5. Server runs with `uv run frostfire-server`.
6. Tests run with `uv run pytest`.
7. Formatting check runs with `uv run ruff format --check .`.
8. Lint check runs with `uv run ruff check .`.
9. Type check runs with `uv run mypy src`.
10. FastAPI is used for HTTP API.
11. HTTPX async client is used for ESP32 communication.
12. Pydantic Settings is used for config.
13. Pydantic models are used for API schemas.
14. No manual HTTP framework code exists.
15. No synchronous network client is used.
16. No raw relay action is exposed without safety policy.
17. Mutating power endpoints are authenticated.
18. Relay commands are serialized.
19. Dangerous force-off requires explicit confirmation.
20. No automatic retry is performed for relay pulse commands.
