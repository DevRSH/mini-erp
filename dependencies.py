"""
dependencies.py — Autenticación JWT y utilidades de seguridad
"""

import time
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Request, HTTPException
from jose import jwt, JWTError

from config import settings
from logger import log


# ────────────────────────────────────────────
# CONSTANTES (leídas de Settings para retrocompatibilidad)
# ────────────────────────────────────────────
APP_PIN = settings.app_pin
BACKUP_KEY = settings.backup_key
SESSION_HOURS = settings.session_hours
SECRET_KEY = settings.secret_key
COOKIE_SECURE = settings.cookie_secure
COOKIE_HTTPONLY = settings.cookie_httponly
COOKIE_SAMESITE = settings.cookie_samesite


# ────────────────────────────────────────────
# AUTENTICACIÓN JWT
# ────────────────────────────────────────────

def _hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.encode()).hexdigest()


def _generar_token(pin: str) -> str:
    """Genera un JWT firmado con HS256."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": _hash_pin(pin),
        "iat": now,
        "exp": now + timedelta(hours=SESSION_HOURS),
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=settings.jwt_algorithm)
    log.info("JWT generado — expira en %dh", SESSION_HOURS)
    return token


def _validar_token(token: str) -> bool:
    """Verifica que el JWT es auténtico y no ha expirado."""
    try:
        jwt.decode(token, SECRET_KEY, algorithms=[settings.jwt_algorithm])
        return True
    except JWTError as e:
        log.debug("JWT inválido: %s", e)
        return False


# ────────────────────────────────────────────
# LIMITADOR DE TASA (RATE LIMITING)
# ────────────────────────────────────────────
LOGIN_ATTEMPTS: dict[str, list[float]] = {}


def check_rate_limit(request: Request):
    ip = request.client.host if request.client else "127.0.0.1"
    now = time.time()
    # Conservar solo los intentos del último minuto
    LOGIN_ATTEMPTS[ip] = [t for t in LOGIN_ATTEMPTS.get(ip, []) if now - t < 60]
    if len(LOGIN_ATTEMPTS[ip]) >= 5:
        log.warning("Rate limit excedido — IP: %s", ip)
        raise HTTPException(status_code=429, detail="Demasiados intentos. Espera 1 minuto.")
    LOGIN_ATTEMPTS[ip].append(now)
