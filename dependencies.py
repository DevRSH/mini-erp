import os
import time
import hashlib
import secrets
from fastapi import Request, HTTPException

# ────────────────────────────────────────────
# CONFIGURACIÓN Y CONSTANTES
# ────────────────────────────────────────────
APP_PIN = os.environ.get("APP_PIN", "1234")
BACKUP_KEY = os.environ.get("BACKUP_KEY", "")
SESSION_HOURS = int(os.environ.get("SESSION_HOURS", "24"))
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-12345")
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "false").lower() == "true"
COOKIE_HTTPONLY = os.environ.get("COOKIE_HTTPONLY", "true").lower() == "true"
COOKIE_SAMESITE = os.environ.get("COOKIE_SAMESITE", "lax")

# ────────────────────────────────────────────
# AUTENTICACIÓN
# ────────────────────────────────────────────

def _hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.encode()).hexdigest()

def _generar_token(pin: str) -> str:
    """Token = hash(pin) + timestamp de expiración."""
    expira = int(time.time()) + SESSION_HOURS * 3600
    raw = f"{_hash_pin(pin)}:{expira}"
    firma = hashlib.sha256(f"{SECRET_KEY}{raw}".encode()).hexdigest()
    return f"{raw}:{firma}"

def _validar_token(token: str) -> bool:
    """Verifica que el token es auténtico y no expiró."""
    try:
        partes = token.split(":")
        if len(partes) != 3:
            return False
        raw = f"{partes[0]}:{partes[1]}"
        firma = partes[2]
        firma_esperada = hashlib.sha256(f"{SECRET_KEY}{raw}".encode()).hexdigest()
        if not secrets.compare_digest(firma, firma_esperada):
            return False
        if int(partes[1]) < time.time():
            return False
        return True
    except Exception:
        return False

# ────────────────────────────────────────────
# LIMITADOR DE TASA (RATE LIMITING)
# ────────────────────────────────────────────
LOGIN_ATTEMPTS = {}

def check_rate_limit(request: Request):
    ip = request.client.host if request.client else "127.0.0.1"
    now = time.time()
    # Conservar solo los intentos del último minuto
    LOGIN_ATTEMPTS[ip] = [t for t in LOGIN_ATTEMPTS.get(ip, []) if now - t < 60]
    if len(LOGIN_ATTEMPTS[ip]) >= 5:
        raise HTTPException(status_code=429, detail="Demasiados intentos. Espera 1 minuto.")
    LOGIN_ATTEMPTS[ip].append(now)
