# Deployment

Default port: `8080`.

## Direct process

```bash
uv run frostfire-server
```

Useful for local tests and single-node containers.

## Environment file

Keep secrets in `/etc/frostfire/frostfire.env` and load with `EnvironmentFile`.

```bash
APP_HOST=0.0.0.0
APP_PORT=8080
API_TOKEN=change-me
ESP32_BASE_URL=http://192.168.1.50
```

## systemd service (system scope)

`/etc/systemd/system/frostfire-backend.service`

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

Commands:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now frostfire-backend
sudo systemctl status frostfire-backend
```

## systemd service (user scope)

`~/.config/systemd/user/frostfire-backend.service`

```ini
[Unit]
Description=Frostfire Backend

[Service]
ExecStart=%h/.local/bin/frostfire-server
EnvironmentFile=%h/.config/frostfire/frostfire.env
Restart=on-failure

[Install]
WantedBy=default.target
```

Enable:

```bash
systemctl --user daemon-reload
systemctl --user enable --now frostfire-backend
```

## Firewall notes

Expose only trusted LAN/VPN networks.

- Allow incoming traffic on `8080` only from trusted sources.
- If needed, terminate TLS at a reverse proxy and forward to Frostfire over loopback.
- Never publish on the public Internet without strict network segmentation.
