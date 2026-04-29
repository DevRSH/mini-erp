import secrets
from fastapi import APIRouter, HTTPException, Request, Response
from schemas.schemas import LoginRequest
from dependencies import (
    APP_PIN, SESSION_HOURS, COOKIE_HTTPONLY, COOKIE_SAMESITE, COOKIE_SECURE,
    _generar_token, _validar_token, check_rate_limit
)
from logger import log

router = APIRouter(prefix="/api", tags=["Autenticación"])

@router.post("/login")
def login(datos: LoginRequest, response: Response, request: Request):
    """Valida el PIN y devuelve una cookie de sesión con JWT."""
    check_rate_limit(request)
    ip = request.client.host if request.client else "unknown"

    if not secrets.compare_digest(datos.pin.strip(), APP_PIN):
        log.warning("Login fallido — IP: %s", ip)
        raise HTTPException(401, "PIN incorrecto")

    token = _generar_token(datos.pin)
    response.set_cookie(
        key="erp_session",
        value=token,
        max_age=SESSION_HOURS * 3600,
        httponly=COOKIE_HTTPONLY,
        samesite=COOKIE_SAMESITE,
        secure=COOKIE_SECURE,
    )
    log.info("Login exitoso — IP: %s", ip)
    return {"mensaje": "Acceso concedido", "horas": SESSION_HOURS}

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("erp_session")
    log.info("Sesión cerrada")
    return {"mensaje": "Sesión cerrada"}

@router.get("/sesion")
def verificar_sesion(request: Request):
    token = request.cookies.get("erp_session")
    if token and _validar_token(token):
        return {"autenticado": True}
    return {"autenticado": False}
