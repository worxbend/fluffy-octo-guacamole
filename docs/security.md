# Security Notes

Frostfire acts on physical hardware. Treat this service as sensitive infrastructure.

## Required controls

- Bearer token authentication on mutating power endpoints.
- Request authentication via `Authorization: Bearer <token>`.
- Confirmation required for `force-off`.
- Bounded relay durations and minimum interval checks in service policy.
- No retry of relay pulse commands by default.
- Request and response logging with request IDs but without secret values.

## Operational guidance

- Keep service off public WAN.
- Use VPN/Tailscale/WireGuard for remote management.
- Put a reverse proxy with TLS in front if remote HTTPS is required.
- Rotate `API_TOKEN` if a secret leak is suspected.

## Logging and audit

Important log fields:

- request_id
- method/path
- status code
- duration_ms
- action/duration for power commands

Do not log:

- API token
- `Authorization` header contents
- full secret config dumps
