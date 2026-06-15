# Frostfire HTTP API

Base path: `/api/v1` for control APIs.

## Error format

All errors use the stable schema:

```json
{
  "error": {
    "code": "error_code",
    "message": "Human readable message",
    "details": {}
  }
}
```

Common codes:

- `unauthorized` (401)
- `forbidden` (403)
- `unsafe_command` (422)
- `confirmation_required` (422)
- `command_in_progress` (409)
- `bad_request` (400)
- `device_unavailable` (503)
- `device_protocol_error` (503)
- `internal_error` (500)

## Health

### `GET /health`

```bash
curl -i http://localhost:8080/health
```

Response:

```json
{
  "status": "ok",
  "service": "frostfire-backend",
  "version": "0.1.0"
}
```

## Readiness

### `GET /ready`

```bash
curl -i http://localhost:8080/ready
```

Ready response:

```json
{
  "ready": true,
  "esp32": {
    "online": true
  }
}
```

Offline response:

```json
{
  "ready": false,
  "esp32": {
    "online": false,
    "error": "device unavailable"
  }
}
```

## Metrics

### `GET /metrics`

Exposes basic Prometheus-formatted counters and gauges.

```bash
curl -i http://localhost:8080/metrics
```

Returned metric names include:

- `frostfire_requests_total`
- `frostfire_power_commands_total`
- `frostfire_power_command_failures_total`
- `frostfire_esp32_request_duration_seconds`
- `frostfire_esp32_request_duration_seconds_count`
- `frostfire_esp32_request_duration_seconds_sum`
- `frostfire_esp32_online`

## Device status

### `GET /api/v1/device/status`

```bash
curl -i http://localhost:8080/api/v1/device/status
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

## Power press

### `POST /api/v1/power/press`

Requires authentication.

```bash
curl -X POST http://localhost:8080/api/v1/power/press \
  -H "Authorization: Bearer $FROSTFIRE_API_TOKEN"
```

Response:

```json
{
  "action": "press",
  "accepted": true,
  "executed": true,
  "duration_ms": 500,
  "device_response": {
    "accepted": true,
    "duration_ms": 500,
    "message": "relay pulsed"
  },
  "message": "relay pulsed"
}
```

### Idempotency (optional)

Provide `Idempotency-Key` on mutating power commands to protect against accidental duplicates within a short window.

```bash
curl -X POST http://localhost:8080/api/v1/power/press \
  -H "Authorization: Bearer $FROSTFIRE_API_TOKEN" \
  -H "Idempotency-Key: <uuid>"
```

When a key is reused and the previous result is still within cache retention, the backend returns the prior response without triggering a second relay pulse.

## Force off

### `POST /api/v1/power/force-off`

Requires authentication and confirmation.

```bash
curl -X POST http://localhost:8080/api/v1/power/force-off \
  -H "Authorization: Bearer $FROSTFIRE_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"confirm": true}'
```

Missing confirmation response:

```json
{
  "error": {
    "code": "confirmation_required",
    "message": "force-off requires confirm=true",
    "details": {}
  }
}
```

## Authentication

Mutating power endpoints require:

`Authorization: Bearer <API_TOKEN>`

Status endpoints may be optionally protected by future extension.

Missing token => `401 unauthorized`

Invalid token => `403 forbidden`
