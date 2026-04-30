"""
config.py — Configuración centralizada con Pydantic Settings
Carga automáticamente variables desde .env y entorno del sistema.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Configuración de la aplicación. Las variables de entorno
    tienen prioridad sobre los valores de .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Autenticación ──
    app_pin: str = Field(default="1234", description="PIN de acceso a la app")
    secret_key: str = Field(
        default="dev-secret-key-cambiar-en-produccion",
        description="Clave secreta para firmar JWT",
    )
    session_hours: int = Field(default=2, description="Duración de sesión en horas")

    # ── Cookies ──
    cookie_secure: bool = Field(default=False, description="Cookie solo HTTPS")
    cookie_httponly: bool = Field(default=True, description="Cookie no accesible por JS")
    cookie_samesite: str = Field(default="lax", description="Política SameSite")

    # ── Backup ──
    backup_key: str = Field(default="", description="Clave para descargar backup")

    # ── Base de datos ──
    db_path: str = Field(default="data/erp.db", description="Ruta del archivo SQLite")

    # ── Logging ──
    log_level: str = Field(default="INFO", description="Nivel de logging")
    log_dir: str = Field(default="logs", description="Directorio para archivos de log")

    # ── JWT ──
    jwt_algorithm: str = Field(default="HS256", description="Algoritmo JWT")


# Instancia global — se importa desde cualquier módulo
settings = Settings()
