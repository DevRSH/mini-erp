"""
logger.py — Logging estructurado con rotación semanal
Los logs se guardan en archivos fuera de la DB para auditoría independiente.
"""

import os
import logging
from logging.handlers import TimedRotatingFileHandler
from config import settings


def setup_logger(name: str = "mini-erp") -> logging.Logger:
    """Configura y retorna el logger principal de la aplicación."""
    logger = logging.getLogger(name)

    # Evitar duplicar handlers si se llama múltiples veces
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    # ── Formato ──
    formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] [%(name)s.%(module)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # ── Consola ──
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # ── Archivo con rotación semanal ──
    os.makedirs(settings.log_dir, exist_ok=True)
    log_path = os.path.join(settings.log_dir, "app.log")

    file_handler = TimedRotatingFileHandler(
        filename=log_path,
        when="W0",           # Rotar cada lunes
        interval=1,
        backupCount=12,       # Mantener 12 semanas (3 meses)
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.suffix = "%Y-%m-%d"
    logger.addHandler(file_handler)

    return logger


# Logger global — importar desde cualquier módulo
log = setup_logger()
