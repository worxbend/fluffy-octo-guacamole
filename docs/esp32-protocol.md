# ESP32 Protocol Contract

The Frostfire backend expects this HTTP contract from the ESP32 firmware:

- `GET /health`
- `GET /status`
- `POST /relay/pulse`

All payloads are JSON.

## `GET /health`

Response:

```json
{
  "status": "ok",
  "device": "frostfire-esp32",
  "firmware_version": "0.1.0"
}
```

## `GET /status`

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

## `POST /relay/pulse`

Request body:

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

Notes:

- The relay firmware should reject invalid durations.
- Return one response per request with explicit errors on failure.
- Do not overlap relay pulses at firmware level.
