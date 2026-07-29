"""
app/utils/logging_config.py
-----------------------------
Bonus feature: basic production-style logging setup. Writes to stdout
(so it's captured by Docker/Render/Railway logs automatically) and, in
addition, to a rotating file under logs/ for local debugging.

This intentionally stays simple - swap in structlog or a hosted log
sink (e.g. Papertrail, Datadog) later without changing any call site,
since routes/services only ever call `current_app.logger`.
"""

import logging
import os
from logging.handlers import RotatingFileHandler


def configure_logging(app):
    log_level = logging.DEBUG if app.debug else logging.INFO

    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
    )

    # Always log to stdout - this is what container platforms capture.
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(log_level)
    app.logger.addHandler(stream_handler)

    # Also log to a rotating file for local development convenience.
    try:
        os.makedirs("logs", exist_ok=True)
        file_handler = RotatingFileHandler(
            "logs/app.log", maxBytes=1_000_000, backupCount=3
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level)
        app.logger.addHandler(file_handler)
    except OSError:
        # Read-only filesystem (some hosting platforms) - stdout logging still works.
        pass

    app.logger.setLevel(log_level)
