"""Console entrypoint for Frostfire backend."""

from __future__ import annotations

import uvicorn

from frostfire.app import create_app
from frostfire.config.settings import load_settings


def main() -> None:
    app_settings = load_settings()
    app = create_app()
    uvicorn.run(
        app,
        host=app_settings.APP_HOST,
        port=app_settings.APP_PORT,
        log_config=None,
    )


if __name__ == "__main__":
    main()
