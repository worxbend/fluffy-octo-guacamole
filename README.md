# Frostfire Backend

Frostfire Backend is a production-oriented asyncio service that exposes a safe HTTP API
for controlling an ESP32 relay module connected to a PC power-button circuit.

Warning:
Frostfire controls physical PC power pins through a relay.
Incorrect usage may interrupt running workloads or cause data loss.
Do not expose this service directly to the public Internet.

## Architecture

```text
HTTP Client
   |
   v
Frostfire API (FastAPI)
   |
   +-- API Layer
   |     - routes
   |     - authentication
   |     - request/response schemas
   |
   +-- Application Layer
   |     - PowerService
   |     - DeviceService
   |     - SafetyPolicy
   |
   +-- Domain Layer
   |     - command models
   |     - power actions
   |     - domain errors
   |
   +-- Infrastructure Layer
         - ESP32 HTTP client
         - settings and logging
```

## Hardware warning

This service can force physical power actions and should only be used in a trusted
environment connected to trusted hardware.

## Installation

Requirements:

- Python 3.12+
- `uv`

```bash
git clone <repo-url>
cd frostfire-backend
uv sync
```

## Configuration

Copy `.env.example` to `.env` and adjust values:

```bash
cp .env.example .env
```

Important settings:

- `APP_HOST` / `APP_PORT`
- `API_TOKEN` (required, must not be logged)
- `ESP32_BASE_URL`
- `ESP32_TIMEOUT_SECONDS`
- `POWER_PRESS_DURATION_MS` (safe short press default)
- `FORCE_OFF_PRESS_DURATION_MS` (destructive long press)
- `MIN_COMMAND_INTERVAL_SECONDS`
- `COMMAND_LOCK_TIMEOUT_SECONDS`
- `LOG_LEVEL`

## Running

Run using the package entrypoint:

```bash
uv run frostfire-server
```

Or with uvicorn directly:

```bash
uv run uvicorn frostfire.app:create_app --factory --host 0.0.0.0 --port 8080
```

Default HTTP port is `8080`.

## API usage

Health endpoints:

```bash
curl http://localhost:8080/health
curl http://localhost:8080/ready
```

Device status:

```bash
curl http://localhost:8080/api/v1/device/status
```

Power press:

```bash
curl -X POST http://localhost:8080/api/v1/power/press \
  -H "Authorization: Bearer $FROSTFIRE_API_TOKEN"
```

Force-off requires explicit confirmation:

```bash
curl -X POST http://localhost:8080/api/v1/power/force-off \
  -H "Authorization: Bearer $FROSTFIRE_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"confirm": true}'
```

See [docs/api.md](docs/api.md) for full endpoint, payload, and error schema docs.

## Testing

```bash
uv sync
uv run pytest
```

Quality gates used by this project:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
uv run coverage run -m pytest
uv run coverage report
```

## Deployment

See [docs/deployment.md](docs/deployment.md) for direct process and systemd examples.

## Security notes

- Use bearer-token auth for mutating endpoints.
- Keep `API_TOKEN` secret.
- Prefer reverse proxy + TLS/VPN for remote access.
- Keep safe relay durations and minimum interval settings.
- Do not bypass confirmation on force-off.

## ESP32 firmware expectations

Backend expects an ESP32 exposing:

- `GET /health`
- `GET /status`
- `POST /relay/pulse`

with JSON payloads described in [docs/esp32-protocol.md](docs/esp32-protocol.md).

## License

This project is distributed under the [MIT License](LICENSE).
