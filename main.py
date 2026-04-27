"""
main.py — Mini ERP | FastAPI Backend
Sprint 7: Autenticación PIN, backup protegido, lifespan moderno
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, Response, Cookie
from fastapi.responses import HTMLResponse, Response as FastResponse, FileResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from database import init_db, init_compras, get_db, DB_PATH
from audit_service import log_transaction, snapshot_sale, snapshot_purchase, list_logs
import os
import hashlib
import secrets
import time
import sqlite3

# ────────────────────────────────────────────
# CONFIGURACIÓN DE SEGURIDAD
# ────────────────────────────────────────────

APP_PIN       = os.environ.get("APP_PIN", "1234")          # PIN de 4 dígitos
BACKUP_KEY    = os.environ.get("BACKUP_KEY", "")           # Clave backup
SESSION_HOURS = int(os.environ.get("SESSION_HOURS", "8"))  # Duración sesión
SECRET_KEY    = os.environ.get("SECRET_KEY",               # Clave firma tokens
                secrets.token_hex(32))


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


_APP_ENV = os.environ.get("APP_ENV", os.environ.get("ENV", "development")).strip().lower()
COOKIE_SECURE = _env_bool("COOKIE_SECURE", _APP_ENV in {"production", "prod"})
COOKIE_HTTPONLY = _env_bool("COOKIE_HTTPONLY", True)
COOKIE_SAMESITE = os.environ.get("COOKIE_SAMESITE", "lax").strip().lower()
if COOKIE_SAMESITE not in {"lax", "strict", "none"}:
    COOKIE_SAMESITE = "lax"

def _hash_pin(pin: str) -> str:
    return hashlib.sha256(f"{SECRET_KEY}{pin}".encode()).hexdigest()

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
        hash_pin, expira, firma = partes
        if int(expira) < int(time.time()):
            return False
        raw = f"{hash_pin}:{expira}"
        firma_esperada = hashlib.sha256(f"{SECRET_KEY}{raw}".encode()).hexdigest()
        return secrets.compare_digest(firma, firma_esperada)
    except Exception:
        return False

# Rutas que no requieren autenticación
RUTAS_PUBLICAS = {"/", "/login", "/manifest.json",
                  "/service-worker.js", "/icon-192.png", "/icon-512.png"}

# ────────────────────────────────────────────
# LIFESPAN (reemplaza @app.on_event deprecado)
# ────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    init_compras()
    yield

app = FastAPI(title="Fika", version="3.0.0", lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(sqlite3.IntegrityError)
async def sqlite_integrity_error_handler(_: Request, __: sqlite3.IntegrityError):
    return JSONResponse(
        {"detail": "Conflicto de integridad de datos"},
        status_code=409,
    )


@app.exception_handler(sqlite3.OperationalError)
async def sqlite_operational_error_handler(_: Request, exc: sqlite3.OperationalError):
    detail = "Error operativo de base de datos"
    status = 500
    mensaje = str(exc).lower()
    if "locked" in mensaje or "busy" in mensaje:
        detail = "Base de datos ocupada temporalmente, reintenta"
        status = 503
    return JSONResponse({"detail": detail}, status_code=status)

# ────────────────────────────────────────────
# MIDDLEWARE DE AUTENTICACIÓN
# ────────────────────────────────────────────

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path

    # Rutas públicas pasan sin verificar
    if path in RUTAS_PUBLICAS:
        return await call_next(request)

    # Endpoints públicos API que no requieren sesión previa
    if path in {"/api/login", "/api/sesion"}:
        return await call_next(request)

    # Verificar cookie de sesión
    token = request.cookies.get("erp_session")
    if not token or not _validar_token(token):
        # Si es llamada API → 401 JSON
        if path.startswith("/api/"):
            return JSONResponse({"detail": "No autenticado"}, status_code=401)
        # Si es página → redirigir al login
        return RedirectResponse(url="/", status_code=302)

    return await call_next(request)

# ────────────────────────────────────────────
# AUTENTICACIÓN — ENDPOINTS
# ────────────────────────────────────────────

class LoginRequest(BaseModel):
    pin: str = Field(..., min_length=4, max_length=6)

@app.post("/api/login")
def login(datos: LoginRequest, response: Response):
    """Valida el PIN y devuelve una cookie de sesión."""
    if not secrets.compare_digest(datos.pin.strip(), APP_PIN):
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
    return {"mensaje": "Acceso concedido", "horas": SESSION_HOURS}

@app.post("/api/logout")
def logout(response: Response):
    response.delete_cookie("erp_session")
    return {"mensaje": "Sesión cerrada"}

@app.get("/api/sesion")
def verificar_sesion(request: Request):
    token = request.cookies.get("erp_session")
    if token and _validar_token(token):
        return {"autenticado": True}
    return {"autenticado": False}

# ────────────────────────────────────────────
# SCHEMAS
# ────────────────────────────────────────────

class ProductoCrear(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)
    precio: float = Field(..., ge=0)
    costo: float = Field(0, ge=0)
    costo_envio: float = Field(0, ge=0)
    stock: int = Field(0, ge=0)
    stock_minimo: int = Field(5, ge=0)
    categoria: str = Field("General", max_length=50)
    codigo_proveedor: str = Field("", max_length=80)
    tiene_variantes: bool = False

    @validator("nombre")
    def nombre_no_vacio(cls, v):
        if not v.strip():
            raise ValueError("El nombre no puede estar vacío")
        return v.strip()


class ProductoEditar(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=100)
    precio: Optional[float] = Field(None, ge=0)
    costo: Optional[float] = Field(None, ge=0)
    costo_envio: Optional[float] = Field(None, ge=0)
    stock_minimo: Optional[int] = Field(None, ge=0)
    categoria: Optional[str] = Field(None, max_length=50)
    codigo_proveedor: Optional[str] = Field(None, max_length=80)


class AjusteStock(BaseModel):
    cantidad: int
    motivo: Optional[str] = "Ajuste manual"


class VarianteCrear(BaseModel):
    attr1_nombre: str = Field(..., min_length=1, max_length=40)
    attr1_valor: str = Field(..., min_length=1, max_length=60)
    attr2_nombre: Optional[str] = Field(None, max_length=40)
    attr2_valor: Optional[str] = Field(None, max_length=60)
    stock: int = Field(0, ge=0)
    stock_minimo: int = Field(2, ge=0)
    codigo_barras: str = Field("", max_length=80)

    @validator("attr2_valor", always=True)
    def validar_attr2(cls, v, values):
        nombre = values.get("attr2_nombre")
        if nombre and not v:
            raise ValueError("Si hay nombre de atributo 2, debe tener valor")
        if not nombre and v:
            raise ValueError("Si hay valor de atributo 2, debe tener nombre")
        return v


class VarianteEditar(BaseModel):
    attr1_valor: Optional[str] = Field(None, max_length=60)
    attr2_valor: Optional[str] = Field(None, max_length=60)
    stock_minimo: Optional[int] = Field(None, ge=0)
    codigo_barras: Optional[str] = Field(None, max_length=80)


class AjusteVariante(BaseModel):
    cantidad: int
    motivo: Optional[str] = "Ajuste manual"


class ItemVenta(BaseModel):
    producto_id: int
    cantidad: int = Field(..., gt=0)
    variante_id: Optional[int] = None


class VentaCrear(BaseModel):
    items: List[ItemVenta] = Field(..., min_items=1)
    metodo_pago: str = Field("efectivo", pattern="^(efectivo|transferencia|tarjeta)$")


class VentaCorreccion(BaseModel):
    metodo_pago: str = Field("efectivo", pattern="^(efectivo|transferencia|tarjeta)$")
    items: List[ItemVenta] = Field(..., min_items=1)


# ── HELPER ──────────────────────────────────
def _margen(precio, costo, costo_envio):
    costo_real = (costo or 0) + (costo_envio or 0)
    if precio and precio > 0:
        ganancia = precio - costo_real
        pct = round((ganancia / precio) * 100, 1)
    else:
        ganancia = 0
        pct = 0
    return {"costo_real": costo_real, "ganancia": ganancia, "margen_pct": pct}

def _producto_full(row):
    d = dict(row)
    d.update(_margen(d["precio"], d["costo"], d.get("costo_envio", 0)))
    return d

def _to_iso_dt(value):
    if not value:
        return value
    # SQLite datetime('now') => "YYYY-MM-DD HH:MM:SS"
    return value.replace(" ", "T", 1) if " " in value else value


def _aplicar_delta_stock(conn, producto_id: int, variante_id: Optional[int], delta: int):
    if delta == 0:
        return
    if variante_id:
        if delta < 0:
            cur = conn.execute(
                "UPDATE variantes SET stock = stock + ? WHERE id=? AND producto_id=? AND activo=1 AND stock >= ?",
                (delta, variante_id, producto_id, abs(delta)),
            )
            if cur.rowcount != 1:
                raise HTTPException(409, f"Stock insuficiente para variante {variante_id}")
        else:
            cur = conn.execute(
                "UPDATE variantes SET stock = stock + ? WHERE id=? AND producto_id=? AND activo=1",
                (delta, variante_id, producto_id),
            )
            if cur.rowcount != 1:
                raise HTTPException(404, f"Variante {variante_id} no encontrada")
        total_var = conn.execute(
            "SELECT COALESCE(SUM(stock),0) as t FROM variantes WHERE producto_id=? AND activo=1",
            (producto_id,),
        ).fetchone()["t"]
        conn.execute("UPDATE productos SET stock=? WHERE id=?", (total_var, producto_id))
    else:
        if delta < 0:
            cur = conn.execute(
                "UPDATE productos SET stock = stock + ? WHERE id=? AND activo=1 AND stock >= ?",
                (delta, producto_id, abs(delta)),
            )
            if cur.rowcount != 1:
                raise HTTPException(409, f"Stock insuficiente para producto {producto_id}")
        else:
            cur = conn.execute(
                "UPDATE productos SET stock = stock + ? WHERE id=? AND activo=1",
                (delta, producto_id),
            )
            if cur.rowcount != 1:
                raise HTTPException(404, f"Producto {producto_id} no encontrado")


def _validar_consistencia_stock_producto(conn, producto_id: int):
    row = conn.execute(
        "SELECT id, stock, tiene_variantes FROM productos WHERE id=? AND activo=1",
        (producto_id,),
    ).fetchone()
    if not row:
        return
    if row["stock"] < 0:
        raise HTTPException(409, f"Stock negativo detectado para producto {producto_id}")
    if row["tiene_variantes"]:
        total_var = conn.execute(
            "SELECT COALESCE(SUM(stock),0) AS t FROM variantes WHERE producto_id=? AND activo=1",
            (producto_id,),
        ).fetchone()["t"]
        if total_var < 0:
            raise HTTPException(409, f"Stock negativo detectado en variantes del producto {producto_id}")
        if total_var != row["stock"]:
            conn.execute("UPDATE productos SET stock=? WHERE id=?", (total_var, producto_id))


def _validar_operable_para_cancelacion(row, etiqueta: str):
    if row["estado"] != "active":
        raise HTTPException(400, f"La {etiqueta} ya está cancelada")
    if row["corrected_by_id"] is not None:
        raise HTTPException(409, f"La {etiqueta} {row['id']} ya fue corregida por {row['corrected_by_id']}")


def _validar_operable_para_correccion(row, etiqueta: str):
    _validar_operable_para_cancelacion(row, etiqueta)
    # Politica: una sola correccion por transaccion (sin cadena).
    if row["corrected_from_id"] is not None:
        raise HTTPException(409, f"La {etiqueta} {row['id']} es una correccion y no puede corregirse de nuevo")


# ────────────────────────────────────────────
# SPRINT 1 — INVENTARIO
# ────────────────────────────────────────────

@app.get("/api/products")
@app.get("/api/productos")
def listar_productos(categoria: Optional[str] = None, solo_activos: bool = True):
    with get_db() as conn:
        query = """
            SELECT *,
                   CASE WHEN stock <= stock_minimo THEN 1 ELSE 0 END AS stock_bajo
            FROM productos WHERE 1=1
        """
        params = []
        if solo_activos:
            query += " AND activo = 1"
        if categoria:
            query += " AND categoria = ?"
            params.append(categoria)
        query += " ORDER BY nombre"
        rows = conn.execute(query, params).fetchall()
        return [_producto_full(r) for r in rows]


@app.post("/api/products", status_code=201)
@app.post("/api/productos", status_code=201)
def crear_producto(datos: ProductoCrear):
    with get_db() as conn:
        existe = conn.execute(
            "SELECT id FROM productos WHERE nombre = ? AND activo = 1", (datos.nombre,)
        ).fetchone()
        if existe:
            raise HTTPException(400, f"Ya existe un producto llamado '{datos.nombre}'")

        cursor = conn.execute(
            """INSERT INTO productos
               (nombre, precio, costo, costo_envio, stock, stock_minimo,
                categoria, codigo_proveedor, tiene_variantes)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (datos.nombre, datos.precio, datos.costo, datos.costo_envio,
             0 if datos.tiene_variantes else datos.stock,
             datos.stock_minimo, datos.categoria,
             datos.codigo_proveedor, int(datos.tiene_variantes))
        )
        row = conn.execute("SELECT * FROM productos WHERE id=?", (cursor.lastrowid,)).fetchone()
        return _producto_full(row)


@app.put("/api/products/{id}")
@app.put("/api/productos/{id}")
def editar_producto(id: int, datos: ProductoEditar):
    with get_db() as conn:
        producto = conn.execute(
            "SELECT * FROM productos WHERE id=? AND activo=1", (id,)
        ).fetchone()
        if not producto:
            raise HTTPException(404, f"Producto {id} no encontrado")

        campos = {}
        for campo in ["nombre","precio","costo","costo_envio","stock_minimo","categoria","codigo_proveedor"]:
            val = getattr(datos, campo)
            if val is not None:
                campos[campo] = val.strip() if isinstance(val, str) else val

        if not campos:
            raise HTTPException(400, "No se enviaron campos para actualizar")

        set_clause = ", ".join(f"{k}=?" for k in campos)
        conn.execute(f"UPDATE productos SET {set_clause} WHERE id=?", [*campos.values(), id])
        row = conn.execute("SELECT * FROM productos WHERE id=?", (id,)).fetchone()
        return _producto_full(row)


@app.delete("/api/products/{id}")
@app.delete("/api/productos/{id}")
def desactivar_producto(id: int):
    with get_db() as conn:
        p = conn.execute(
            "SELECT id, nombre FROM productos WHERE id=? AND activo=1", (id,)
        ).fetchone()
        if not p:
            raise HTTPException(404, f"Producto {id} no encontrado")
        conn.execute("UPDATE productos SET activo=0 WHERE id=?", (id,))
        conn.execute("UPDATE variantes SET activo=0 WHERE producto_id=?", (id,))
        return {"mensaje": f"Producto '{p['nombre']}' desactivado"}


@app.post("/api/products/{id}/adjust")
@app.post("/api/productos/{id}/ajuste")
def ajustar_stock(id: int, ajuste: AjusteStock):
    with get_db() as conn:
        p = conn.execute(
            "SELECT * FROM productos WHERE id=? AND activo=1", (id,)
        ).fetchone()
        if not p:
            raise HTTPException(404, f"Producto {id} no encontrado")
        if p["tiene_variantes"]:
            raise HTTPException(400, "Este producto tiene variantes. Ajusta el stock por variante.")

        nuevo = p["stock"] + ajuste.cantidad
        if nuevo < 0:
            raise HTTPException(400, f"Stock insuficiente. Actual: {p['stock']}, descuento: {abs(ajuste.cantidad)}")

        conn.execute("UPDATE productos SET stock=? WHERE id=?", (nuevo, id))
        return {"producto": p["nombre"], "stock_anterior": p["stock"],
                "ajuste": ajuste.cantidad, "stock_nuevo": nuevo}


# ────────────────────────────────────────────
# SPRINT 4 — VARIANTES
# ────────────────────────────────────────────

@app.get("/api/products/{id}/variants")
@app.get("/api/productos/{id}/variantes")
def listar_variantes(id: int):
    with get_db() as conn:
        p = conn.execute("SELECT id, nombre, tiene_variantes FROM productos WHERE id=? AND activo=1", (id,)).fetchone()
        if not p:
            raise HTTPException(404, f"Producto {id} no encontrado")
        rows = conn.execute(
            """SELECT *,
                      CASE WHEN stock <= stock_minimo THEN 1 ELSE 0 END AS stock_bajo
               FROM variantes WHERE producto_id=? AND activo=1
               ORDER BY attr1_valor, attr2_valor""",
            (id,)
        ).fetchall()
        return {"producto": p["nombre"], "variantes": [dict(r) for r in rows]}


@app.post("/api/products/{id}/variants", status_code=201)
@app.post("/api/productos/{id}/variantes", status_code=201)
def crear_variante(id: int, datos: VarianteCrear):
    with get_db() as conn:
        p = conn.execute(
            "SELECT * FROM productos WHERE id=? AND activo=1", (id,)
        ).fetchone()
        if not p:
            raise HTTPException(404, f"Producto {id} no encontrado")

        # Marcar producto como tiene_variantes si no lo está
        if not p["tiene_variantes"]:
            conn.execute("UPDATE productos SET tiene_variantes=1, stock=0 WHERE id=?", (id,))

        # Verificar duplicado
        existe = conn.execute(
            """SELECT id FROM variantes
               WHERE producto_id=? AND attr1_valor=? AND COALESCE(attr2_valor,'')=? AND activo=1""",
            (id, datos.attr1_valor, datos.attr2_valor or "")
        ).fetchone()
        if existe:
            raise HTTPException(400, "Ya existe una variante con esos atributos")

        cursor = conn.execute(
            """INSERT INTO variantes
               (producto_id, attr1_nombre, attr1_valor, attr2_nombre, attr2_valor,
                stock, stock_minimo, codigo_barras)
               VALUES (?,?,?,?,?,?,?,?)""",
            (id, datos.attr1_nombre, datos.attr1_valor,
             datos.attr2_nombre, datos.attr2_valor,
             datos.stock, datos.stock_minimo, datos.codigo_barras)
        )
        total = conn.execute(
            "SELECT COALESCE(SUM(stock),0) as t FROM variantes WHERE producto_id=? AND activo=1",
            (id,)
        ).fetchone()["t"]
        conn.execute("UPDATE productos SET stock=? WHERE id=?", (total, id))
        row = conn.execute("SELECT * FROM variantes WHERE id=?", (cursor.lastrowid,)).fetchone()
        return dict(row)


@app.put("/api/variantes/{id}")
def editar_variante(id: int, datos: VarianteEditar):
    with get_db() as conn:
        v = conn.execute("SELECT * FROM variantes WHERE id=? AND activo=1", (id,)).fetchone()
        if not v:
            raise HTTPException(404, f"Variante {id} no encontrada")

        campos = {}
        for campo in ["attr1_valor","attr2_valor","stock_minimo","codigo_barras"]:
            val = getattr(datos, campo)
            if val is not None:
                campos[campo] = val

        if not campos:
            raise HTTPException(400, "Sin campos para actualizar")

        set_clause = ", ".join(f"{k}=?" for k in campos)
        conn.execute(f"UPDATE variantes SET {set_clause} WHERE id=?", [*campos.values(), id])
        row = conn.execute("SELECT * FROM variantes WHERE id=?", (id,)).fetchone()
        return dict(row)


@app.delete("/api/variantes/{id}")
def desactivar_variante(id: int):
    with get_db() as conn:
        v = conn.execute("SELECT * FROM variantes WHERE id=? AND activo=1", (id,)).fetchone()
        if not v:
            raise HTTPException(404, f"Variante {id} no encontrada")
        conn.execute("UPDATE variantes SET activo=0 WHERE id=?", (id,))
        restantes = conn.execute(
            "SELECT COUNT(*) AS c FROM variantes WHERE producto_id=? AND activo=1",
            (v["producto_id"],)
        ).fetchone()["c"]
        if restantes == 0:
            conn.execute(
                "UPDATE productos SET tiene_variantes=0, stock=0 WHERE id=?",
                (v["producto_id"],)
            )
        else:
            total = conn.execute(
                "SELECT COALESCE(SUM(stock),0) AS t FROM variantes WHERE producto_id=? AND activo=1",
                (v["producto_id"],)
            ).fetchone()["t"]
            conn.execute("UPDATE productos SET stock=? WHERE id=?", (total, v["producto_id"]))
        return {"mensaje": "Variante desactivada", "variantes_activas": restantes}


@app.post("/api/variantes/{id}/ajuste")
def ajustar_stock_variante(id: int, ajuste: AjusteVariante):
    with get_db() as conn:
        v = conn.execute("SELECT * FROM variantes WHERE id=? AND activo=1", (id,)).fetchone()
        if not v:
            raise HTTPException(404, f"Variante {id} no encontrada")

        nuevo = v["stock"] + ajuste.cantidad
        if nuevo < 0:
            raise HTTPException(400, f"Stock insuficiente. Actual: {v['stock']}")

        conn.execute("UPDATE variantes SET stock=? WHERE id=?", (nuevo, id))

        # Sincronizar stock total del producto padre (suma de variantes)
        total = conn.execute(
            "SELECT COALESCE(SUM(stock),0) as t FROM variantes WHERE producto_id=? AND activo=1",
            (v["producto_id"],)
        ).fetchone()["t"]
        conn.execute("UPDATE productos SET stock=? WHERE id=?", (total, v["producto_id"]))

        return {"variante_id": id, "stock_anterior": v["stock"],
                "ajuste": ajuste.cantidad, "stock_nuevo": nuevo}


@app.get("/api/buscar")
def buscar_por_codigo(codigo: str):
    """Busca producto o variante por código de proveedor o código de barras. Usado por el escáner."""
    with get_db() as conn:
        # Buscar en variantes primero
        v = conn.execute(
            """SELECT v.*, p.nombre as producto_nombre, p.precio
               FROM variantes v
               JOIN productos p ON v.producto_id = p.id
               WHERE v.codigo_barras = ? AND v.activo=1 AND p.activo=1""",
            (codigo,)
        ).fetchone()
        if v:
            return {"tipo": "variante", "datos": dict(v)}

        # Buscar en productos por código proveedor
        p = conn.execute(
            "SELECT * FROM productos WHERE codigo_proveedor=? AND activo=1", (codigo,)
        ).fetchone()
        if p:
            return {"tipo": "producto", "datos": _producto_full(p)}

        raise HTTPException(404, f"No se encontró ningún producto con código '{codigo}'")


# ────────────────────────────────────────────
# SPRINT 2 — VENTAS
# ────────────────────────────────────────────

def _crear_venta_en_transaccion(conn, venta: VentaCrear, corrected_from_id: Optional[int] = None):
    items_validados = []
    total = 0.0
    productos_tocados = set()

    for item in venta.items:
        p = conn.execute(
            "SELECT * FROM productos WHERE id=? AND activo=1", (item.producto_id,)
        ).fetchone()
        if not p:
            raise HTTPException(404, f"Producto ID {item.producto_id} no existe")

        if p["tiene_variantes"]:
            if not item.variante_id:
                raise HTTPException(400, f"'{p['nombre']}' tiene variantes. Debes seleccionar una.")
            v = conn.execute(
                "SELECT * FROM variantes WHERE id=? AND producto_id=? AND activo=1",
                (item.variante_id, item.producto_id),
            ).fetchone()
            if not v:
                raise HTTPException(404, f"Variante {item.variante_id} no encontrada")
            if v["stock"] < item.cantidad:
                raise HTTPException(400, f"Stock insuficiente en variante {item.variante_id}")
        elif p["stock"] < item.cantidad:
            raise HTTPException(400, f"Stock insuficiente para producto {item.producto_id}")

        subtotal = p["precio"] * item.cantidad
        total += subtotal
        productos_tocados.add(item.producto_id)
        items_validados.append(
            {
                "producto_id": item.producto_id,
                "variante_id": item.variante_id,
                "nombre": p["nombre"],
                "cantidad": item.cantidad,
                "precio_unitario": p["precio"],
                "subtotal": subtotal,
                "tiene_variantes": bool(p["tiene_variantes"]),
            }
        )

    cursor = conn.execute(
        """INSERT INTO ventas (total, metodo_pago, estado, corrected_from_id, corrected_by_id)
           VALUES (?,?,?,?,NULL)""",
        (total, venta.metodo_pago, "active", corrected_from_id),
    )
    venta_id = cursor.lastrowid

    for item in items_validados:
        conn.execute(
            """INSERT INTO detalle_venta
               (venta_id, producto_id, variante_id, cantidad, precio_unitario, subtotal)
               VALUES (?,?,?,?,?,?)""",
            (venta_id, item["producto_id"], item["variante_id"], item["cantidad"], item["precio_unitario"], item["subtotal"]),
        )
        _aplicar_delta_stock(conn, item["producto_id"], item["variante_id"], -item["cantidad"])
        _validar_consistencia_stock_producto(conn, item["producto_id"])

    log_transaction(conn, "sale", venta_id, "create", previous_data=None, new_data=snapshot_sale(conn, venta_id))
    return {"venta_id": venta_id, "total": total, "metodo_pago": venta.metodo_pago, "items": items_validados}


@app.post("/api/ventas", status_code=201)
def registrar_venta(venta: VentaCrear):
    with get_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        return _crear_venta_en_transaccion(conn, venta)


@app.get("/api/ventas")
def historial_ventas(limite: int = 50):
    limite = max(1, min(limite, 200))
    with get_db() as conn:
        ventas = conn.execute(
            "SELECT * FROM ventas ORDER BY created_at DESC LIMIT ?", (limite,)
        ).fetchall()
        resultado = []
        for v in ventas:
            detalles = conn.execute(
                """SELECT d.*, p.nombre,
                          v.attr1_valor, v.attr2_valor, v.attr1_nombre, v.attr2_nombre
                   FROM detalle_venta d
                   JOIN productos p ON d.producto_id = p.id
                   LEFT JOIN variantes v ON d.variante_id = v.id
                   WHERE d.venta_id=?""",
                (v["id"],)
            ).fetchall()
            venta = dict(v)
            venta["created_at"] = _to_iso_dt(venta.get("created_at"))
            resultado.append({**venta, "items": [dict(d) for d in detalles]})
        return resultado


@app.put("/api/ventas/{venta_id}/correccion")
def corregir_venta(venta_id: int, datos: VentaCorreccion):
    with get_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        venta = conn.execute("SELECT * FROM ventas WHERE id=?", (venta_id,)).fetchone()
        if not venta:
            raise HTTPException(404, f"Venta {venta_id} no encontrada")
        _validar_operable_para_correccion(venta, "venta")

        previa = snapshot_sale(conn, venta_id)
        for item in previa["items"]:
            _aplicar_delta_stock(conn, item["producto_id"], item.get("variante_id"), item["cantidad"])
            _validar_consistencia_stock_producto(conn, item["producto_id"])

        conn.execute("UPDATE ventas SET estado='cancelled' WHERE id=?", (venta_id,))
        nueva = snapshot_sale(conn, venta_id)
        log_transaction(conn, "sale", venta_id, "cancel", previous_data=previa, new_data=nueva)

        nueva_venta = _crear_venta_en_transaccion(conn, VentaCrear(items=datos.items, metodo_pago=datos.metodo_pago), corrected_from_id=venta_id)
        conn.execute("UPDATE ventas SET corrected_by_id=? WHERE id=?", (nueva_venta["venta_id"], venta_id))
        log_transaction(
            conn,
            "sale",
            venta_id,
            "link_correction",
            previous_data={"corrected_by_id": None, "original_id": venta_id},
            new_data={"corrected_by_id": nueva_venta["venta_id"], "corrected_id": nueva_venta["venta_id"]},
        )
        return {"original_sale_id": venta_id, "corrected_sale_id": nueva_venta["venta_id"]}


@app.post("/api/ventas/{venta_id}/cancelar")
def cancelar_venta(venta_id: int):
    with get_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        venta = conn.execute("SELECT * FROM ventas WHERE id=?", (venta_id,)).fetchone()
        if not venta:
            raise HTTPException(404, f"Venta {venta_id} no encontrada")
        _validar_operable_para_cancelacion(venta, "venta")

        previa = snapshot_sale(conn, venta_id)
        for item in previa["items"]:
            _aplicar_delta_stock(conn, item["producto_id"], item.get("variante_id"), item["cantidad"])
            _validar_consistencia_stock_producto(conn, item["producto_id"])

        conn.execute("UPDATE ventas SET estado='cancelled' WHERE id=?", (venta_id,))
        nueva = snapshot_sale(conn, venta_id)
        log_transaction(conn, "sale", venta_id, "cancel", previous_data=previa, new_data=nueva)
        return {"venta_id": venta_id, "estado": "cancelled"}


# ────────────────────────────────────────────
# SPRINT 3 — REPORTES
# ────────────────────────────────────────────

@app.get("/api/reportes/stock-bajo")
def stock_bajo():
    with get_db() as conn:
        productos = conn.execute(
            """SELECT id, nombre, stock, stock_minimo, categoria, tiene_variantes
               FROM productos
               WHERE activo=1
               ORDER BY nombre"""
        ).fetchall()

        resultado = []
        for p in productos:
            item = dict(p)
            incluir = p["stock"] <= p["stock_minimo"]
            if p["tiene_variantes"]:
                vars_bajas = conn.execute(
                    """SELECT attr1_nombre, attr1_valor, attr2_nombre, attr2_valor,
                              stock, stock_minimo
                       FROM variantes
                       WHERE producto_id=? AND activo=1 AND stock <= stock_minimo""",
                    (p["id"],)
                ).fetchall()
                item["variantes_bajas"] = [dict(v) for v in vars_bajas]
                if item["variantes_bajas"]:
                    incluir = True
            if incluir:
                item["unidades_faltantes"] = max(0, p["stock_minimo"] - p["stock"])
                resultado.append(item)
        resultado.sort(key=lambda x: x["unidades_faltantes"], reverse=True)
        return resultado


@app.get("/api/reportes/mas-vendidos")
def mas_vendidos(limite: int = 10, periodo: str = "todo"):
    limite = max(1, min(limite, 100))
    filtros = {
        "todo": "1=1",
        "hoy": "date(v.created_at) = date('now','localtime')",
        "semana": "v.created_at >= date('now','-7 days','localtime')",
        "mes": "strftime('%Y-%m', v.created_at) = strftime('%Y-%m', 'now','localtime')",
    }
    if periodo not in filtros:
        raise HTTPException(400, "periodo debe ser: todo, hoy, semana o mes")

    with get_db() as conn:
        rows = conn.execute(
            """SELECT p.id, p.nombre, p.categoria,
                      SUM(d.cantidad) AS total_vendido,
                      SUM(d.subtotal) AS ingresos_totales
               FROM detalle_venta d
               JOIN productos p ON d.producto_id = p.id
               JOIN ventas v ON d.venta_id = v.id
               WHERE """ + filtros[periodo] + """ AND v.estado='active'
               GROUP BY p.id
               ORDER BY total_vendido DESC
               LIMIT ?""",
            (limite,)
        ).fetchall()
        return [dict(r) for r in rows]


@app.get("/api/reportes/resumen")
def resumen(periodo: str = "hoy"):
    filtros = {
        "hoy":    "date(created_at) = date('now','localtime')",
        "semana": "created_at >= date('now','-7 days','localtime')",
        "mes":    "strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now','localtime')"
    }
    if periodo not in filtros:
        raise HTTPException(400, "periodo debe ser: hoy, semana o mes")

    with get_db() as conn:
        rv = conn.execute(
            f"""SELECT COUNT(*) AS total_ventas,
                       COALESCE(SUM(total),0) AS ingresos,
                       COALESCE(AVG(total),0) AS ticket_promedio
                FROM ventas WHERE {filtros[periodo]} AND estado='active'"""
        ).fetchone()
        alertas = conn.execute(
            "SELECT COUNT(*) AS c FROM productos WHERE activo=1 AND stock <= stock_minimo"
        ).fetchone()
        total_p = conn.execute(
            "SELECT COUNT(*) AS c FROM productos WHERE activo=1"
        ).fetchone()

        # Ganancia estimada del período
        ganancia = conn.execute(
            f"""SELECT COALESCE(SUM(
                    d.subtotal - (d.cantidad * (p.costo + COALESCE(p.costo_envio,0)))
                ), 0) AS ganancia_estimada
                FROM detalle_venta d
                JOIN productos p ON d.producto_id = p.id
                JOIN ventas v ON d.venta_id = v.id
                WHERE {filtros[periodo].replace('created_at', 'v.created_at')}"""
        ).fetchone()

        return {
            "periodo": periodo,
            "ventas": dict(rv),
            "alertas_stock": alertas["c"],
            "total_productos_activos": total_p["c"],
            "ganancia_estimada": round(ganancia["ganancia_estimada"], 0),
        }


# ────────────────────────────────────────────
# SPRINT 5 — COMPRAS A PROVEEDOR
# ────────────────────────────────────────────

class ItemCompra(BaseModel):
    producto_id: int
    variante_id: Optional[int] = None
    cantidad: int = Field(..., gt=0)
    costo_unitario: float = Field(..., ge=0)

class CompraCrear(BaseModel):
    proveedor: str = Field("Sin nombre", max_length=100)
    notas: str = Field("", max_length=300)
    costo_envio: float = Field(0, ge=0)
    items: List[ItemCompra] = Field(..., min_items=1)
    actualizar_costo: bool = Field(True, description="Si true, actualiza el costo del producto con el de esta compra")


class CompraCorreccion(BaseModel):
    proveedor: str = Field("Sin nombre", max_length=100)
    notas: str = Field("", max_length=300)
    costo_envio: float = Field(0, ge=0)
    items: List[ItemCompra] = Field(..., min_items=1)
    actualizar_costo: bool = Field(True)


def _crear_compra_en_transaccion(conn, compra: CompraCrear, corrected_from_id: Optional[int] = None):
    items_validados = []
    subtotal = 0.0
    for item in compra.items:
        p = conn.execute(
            "SELECT * FROM productos WHERE id=? AND activo=1", (item.producto_id,)
        ).fetchone()
        if not p:
            raise HTTPException(404, f"Producto ID {item.producto_id} no existe")

        if p["tiene_variantes"] and not item.variante_id:
            raise HTTPException(400, f"'{p['nombre']}' tiene variantes. Debes seleccionar una.")
        if item.variante_id:
            v = conn.execute(
                "SELECT * FROM variantes WHERE id=? AND producto_id=? AND activo=1",
                (item.variante_id, item.producto_id),
            ).fetchone()
            if not v:
                raise HTTPException(404, f"Variante {item.variante_id} no encontrada")

        sub = item.costo_unitario * item.cantidad
        subtotal += sub
        items_validados.append(
            {
                "producto_id": item.producto_id,
                "variante_id": item.variante_id,
                "cantidad": item.cantidad,
                "costo_unitario": item.costo_unitario,
                "subtotal": sub,
            }
        )

    total = subtotal + compra.costo_envio
    cursor = conn.execute(
        """INSERT INTO compras (proveedor, notas, subtotal, costo_envio, total, estado, corrected_from_id, corrected_by_id)
           VALUES (?,?,?,?,?,?,?,NULL)""",
        (compra.proveedor, compra.notas, subtotal, compra.costo_envio, total, "active", corrected_from_id),
    )
    compra_id = cursor.lastrowid
    for item in items_validados:
        conn.execute(
            """INSERT INTO detalle_compra
               (compra_id, producto_id, variante_id, cantidad, costo_unitario, subtotal)
               VALUES (?,?,?,?,?,?)""",
            (compra_id, item["producto_id"], item["variante_id"], item["cantidad"], item["costo_unitario"], item["subtotal"]),
        )
        _aplicar_delta_stock(conn, item["producto_id"], item["variante_id"], item["cantidad"])
        _validar_consistencia_stock_producto(conn, item["producto_id"])
        if compra.actualizar_costo and not item["variante_id"]:
            conn.execute("UPDATE productos SET costo=? WHERE id=?", (item["costo_unitario"], item["producto_id"]))

    log_transaction(conn, "purchase", compra_id, "create", previous_data=None, new_data=snapshot_purchase(conn, compra_id))
    return {
        "compra_id": compra_id,
        "proveedor": compra.proveedor,
        "subtotal": subtotal,
        "costo_envio": compra.costo_envio,
        "total": total,
        "items": items_validados,
    }


@app.post("/api/compras", status_code=201)
def registrar_compra(compra: CompraCrear):
    """
    Registra una compra a proveedor.
    Sube el stock de cada producto/variante atómicamente.
    Opcionalmente actualiza el costo unitario del producto.
    """
    with get_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        return _crear_compra_en_transaccion(conn, compra)


@app.get("/api/compras")
def historial_compras(limite: int = 50):
    limite = max(1, min(limite, 200))
    with get_db() as conn:
        compras = conn.execute(
            "SELECT * FROM compras ORDER BY created_at DESC LIMIT ?", (limite,)
        ).fetchall()
        resultado = []
        for c in compras:
            detalles = conn.execute(
                """SELECT dc.*, p.nombre,
                          v.attr1_valor, v.attr2_valor
                   FROM detalle_compra dc
                   JOIN productos p ON dc.producto_id = p.id
                   LEFT JOIN variantes v ON dc.variante_id = v.id
                   WHERE dc.compra_id=?""",
                (c["id"],)
            ).fetchall()
            compra = dict(c)
            compra["created_at"] = _to_iso_dt(compra.get("created_at"))
            resultado.append({**compra, "items": [dict(d) for d in detalles]})
        return resultado


@app.get("/api/compras/{id}")
def detalle_compra(id: int):
    with get_db() as conn:
        c = conn.execute("SELECT * FROM compras WHERE id=?", (id,)).fetchone()
        if not c:
            raise HTTPException(404, f"Compra {id} no encontrada")
        detalles = conn.execute(
            """SELECT dc.*, p.nombre, v.attr1_valor, v.attr2_valor
               FROM detalle_compra dc
               JOIN productos p ON dc.producto_id = p.id
               LEFT JOIN variantes v ON dc.variante_id = v.id
               WHERE dc.compra_id=?""",
            (id,)
        ).fetchall()
        compra = dict(c)
        compra["created_at"] = _to_iso_dt(compra.get("created_at"))
        return {**compra, "items": [dict(d) for d in detalles]}


@app.put("/api/compras/{compra_id}/correccion")
def corregir_compra(compra_id: int, datos: CompraCorreccion):
    with get_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        compra = conn.execute("SELECT * FROM compras WHERE id=?", (compra_id,)).fetchone()
        if not compra:
            raise HTTPException(404, f"Compra {compra_id} no encontrada")
        _validar_operable_para_correccion(compra, "compra")

        previa = snapshot_purchase(conn, compra_id)
        for item in previa["items"]:
            _aplicar_delta_stock(conn, item["producto_id"], item.get("variante_id"), -item["cantidad"])
            _validar_consistencia_stock_producto(conn, item["producto_id"])

        conn.execute("UPDATE compras SET estado='cancelled' WHERE id=?", (compra_id,))
        nueva = snapshot_purchase(conn, compra_id)
        log_transaction(conn, "purchase", compra_id, "cancel", previous_data=previa, new_data=nueva)

        nueva_compra = _crear_compra_en_transaccion(
            conn,
            CompraCrear(
                proveedor=datos.proveedor,
                notas=datos.notas,
                costo_envio=datos.costo_envio,
                items=datos.items,
                actualizar_costo=datos.actualizar_costo,
            ),
            corrected_from_id=compra_id,
        )
        conn.execute("UPDATE compras SET corrected_by_id=? WHERE id=?", (nueva_compra["compra_id"], compra_id))
        log_transaction(
            conn,
            "purchase",
            compra_id,
            "link_correction",
            previous_data={"corrected_by_id": None, "original_id": compra_id},
            new_data={"corrected_by_id": nueva_compra["compra_id"], "corrected_id": nueva_compra["compra_id"]},
        )
        return {"original_purchase_id": compra_id, "corrected_purchase_id": nueva_compra["compra_id"]}


@app.post("/api/compras/{compra_id}/cancelar")
def cancelar_compra(compra_id: int):
    with get_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        compra = conn.execute("SELECT * FROM compras WHERE id=?", (compra_id,)).fetchone()
        if not compra:
            raise HTTPException(404, f"Compra {compra_id} no encontrada")
        _validar_operable_para_cancelacion(compra, "compra")

        previa = snapshot_purchase(conn, compra_id)
        for item in previa["items"]:
            _aplicar_delta_stock(conn, item["producto_id"], item.get("variante_id"), -item["cantidad"])
            _validar_consistencia_stock_producto(conn, item["producto_id"])

        conn.execute("UPDATE compras SET estado='cancelled' WHERE id=?", (compra_id,))
        nueva = snapshot_purchase(conn, compra_id)
        log_transaction(conn, "purchase", compra_id, "cancel", previous_data=previa, new_data=nueva)
        return {"compra_id": compra_id, "estado": "cancelled"}


@app.get("/api/transaction-logs")
def historial_logs(entity_type: Optional[str] = None, entity_id: Optional[int] = None, limite: int = 100):
    limite = max(1, min(limite, 300))
    with get_db() as conn:
        if entity_type and entity_type not in {"purchase", "sale"}:
            raise HTTPException(400, "entity_type debe ser purchase o sale")
        return list_logs(conn, entity_type=entity_type, entity_id=entity_id, limit=limite)


# ────────────────────────────────────────────
# SPRINT 5 — EXPORTACIÓN DE REPORTES
# ────────────────────────────────────────────

@app.get("/api/exportar/reporte")
def exportar_reporte(periodo: str = "mes"):
    """
    Genera un archivo HTML autocontenido con el reporte completo.
    Listo para compartir por WhatsApp o guardar en el celular.
    """
    filtros = {
        "hoy":    "date(v.created_at) = date('now','localtime')",
        "semana": "v.created_at >= date('now','-7 days','localtime')",
        "mes":    "strftime('%Y-%m', v.created_at) = strftime('%Y-%m', 'now','localtime')"
    }
    nombres_periodo = {"hoy": "Hoy", "semana": "Últimos 7 días", "mes": "Este mes"}
    if periodo not in filtros:
        raise HTTPException(400, "periodo debe ser: hoy, semana o mes")

    with get_db() as conn:
        # Resumen
        rv = conn.execute(
            f"""SELECT COUNT(*) AS total_ventas,
                       COALESCE(SUM(total),0) AS ingresos,
                       COALESCE(AVG(total),0) AS ticket_promedio
                FROM ventas v WHERE {filtros[periodo]} AND v.estado='active'"""
        ).fetchone()

        # Ganancia estimada
        gan = conn.execute(
            f"""SELECT COALESCE(SUM(
                    d.subtotal - (d.cantidad * (p.costo + COALESCE(p.costo_envio,0)))
                ),0) AS ganancia
                FROM detalle_venta d
                JOIN productos p ON d.producto_id = p.id
                JOIN ventas v ON d.venta_id = v.id
                WHERE {filtros[periodo]}"""
        ).fetchone()

        # Stock bajo
        stock_bajo = conn.execute(
            """SELECT nombre, stock, stock_minimo, categoria
               FROM productos WHERE activo=1 AND stock <= stock_minimo
               ORDER BY stock ASC LIMIT 20"""
        ).fetchall()

        # Más vendidos
        mas_vendidos = conn.execute(
            """SELECT p.nombre, SUM(d.cantidad) AS total_vendido,
                      SUM(d.subtotal) AS ingresos_totales
               FROM detalle_venta d
               JOIN productos p ON d.producto_id = p.id
               GROUP BY p.id ORDER BY total_vendido DESC LIMIT 10"""
        ).fetchall()

        # Últimas ventas
        ultimas = conn.execute(
            f"""SELECT v.id, v.total, v.metodo_pago, v.created_at
                FROM ventas v WHERE {filtros[periodo]} AND v.estado='active'
                ORDER BY v.created_at DESC LIMIT 20"""
        ).fetchall()

    from datetime import datetime
    ahora = datetime.now().strftime("%d/%m/%Y %H:%M")
    nombre_per = nombres_periodo[periodo]

    def fmt_num(n):
        return f"${int(n):,}".replace(",", ".")

    # ── Construir secciones HTML ──────────────────
    filas_stock = "".join(
        f"""<tr>
              <td>{r['nombre']}</td>
              <td style="color:{'#991B1B' if r['stock']==0 else '#92400E'};font-weight:700;">
                {'⛔ Agotado' if r['stock']==0 else f"⚠️ {r['stock']} uds"}
              </td>
              <td>{r['stock_minimo']}</td>
              <td>{r['categoria']}</td>
            </tr>"""
        for r in stock_bajo
    ) or "<tr><td colspan='4' style='text-align:center;color:#065F46;'>✅ Stock en orden</td></tr>"

    filas_vendidos = "".join(
        f"""<tr>
              <td><strong>#{i+1}</strong> {r['nombre']}</td>
              <td style="font-weight:700;">{r['total_vendido']} uds</td>
              <td style="color:#2D9B5E;font-weight:700;">{fmt_num(r['ingresos_totales'])}</td>
            </tr>"""
        for i, r in enumerate(mas_vendidos)
    ) or "<tr><td colspan='3' style='text-align:center;'>Sin datos</td></tr>"

    metodo_ic = {"efectivo": "💵", "transferencia": "📱", "tarjeta": "💳"}
    filas_ventas = "".join(
        f"""<tr>
              <td>#{str(r['id']).zfill(4)}</td>
              <td>{r['created_at'][:16].replace('T',' ')}</td>
              <td style="color:#2D9B5E;font-weight:700;">{fmt_num(r['total'])}</td>
              <td>{metodo_ic.get(r['metodo_pago'],'')}&nbsp;{r['metodo_pago']}</td>
            </tr>"""
        for r in ultimas
    ) or "<tr><td colspan='4' style='text-align:center;'>Sin ventas</td></tr>"

    ganancia = gan["ganancia"]
    margen_color = "#2D9B5E" if ganancia >= 0 else "#D63B3B"

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Reporte ERP — {nombre_per}</title>
<style>
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background:#F7F5F0; color:#1A1612; padding:16px; font-size:14px; }}
  .header {{ background:#1B3A6B; color:white; border-radius:14px;
             padding:20px; margin-bottom:16px; }}
  .header h1 {{ font-size:22px; font-weight:800; margin-bottom:4px; }}
  .header p  {{ font-size:13px; opacity:.8; }}
  .stats {{ display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:16px; }}
  .stat {{ background:white; border-radius:12px; padding:14px; text-align:center;
           border:1px solid #E8E3DA; }}
  .stat-value {{ font-size:24px; font-weight:800; line-height:1; margin-bottom:4px; }}
  .stat-label {{ font-size:11px; color:#7D7168; font-weight:600;
                 text-transform:uppercase; letter-spacing:.4px; }}
  .section {{ background:white; border-radius:12px; padding:16px;
              margin-bottom:14px; border:1px solid #E8E3DA; }}
  .section h2 {{ font-size:15px; font-weight:800; margin-bottom:12px;
                 padding-bottom:8px; border-bottom:1px solid #E8E3DA; }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  th {{ background:#F7F5F0; padding:8px; text-align:left; font-size:11px;
        font-weight:700; color:#7D7168; text-transform:uppercase; }}
  td {{ padding:9px 8px; border-bottom:1px solid #F0EDE6; vertical-align:top; }}
  tr:last-child td {{ border-bottom:none; }}
  .footer {{ text-align:center; font-size:11px; color:#7D7168; padding:12px 0; }}
  @media print {{ body {{ background:white; padding:0; }} }}
</style>
</head>
<body>

<div class="header">
    <h1>🏪 Reporte Fika</h1>
  <p>Período: <strong>{nombre_per}</strong> &nbsp;|&nbsp; Generado: {ahora}</p>
</div>

<div class="stats">
  <div class="stat">
    <div class="stat-value" style="color:#E8821A;">{rv['total_ventas']}</div>
    <div class="stat-label">Ventas</div>
  </div>
  <div class="stat">
    <div class="stat-value" style="color:#2D9B5E;">{fmt_num(rv['ingresos'])}</div>
    <div class="stat-label">Ingresos</div>
  </div>
  <div class="stat">
    <div class="stat-value" style="color:{margen_color};">{fmt_num(ganancia)}</div>
    <div class="stat-label">Ganancia est.</div>
  </div>
  <div class="stat">
    <div class="stat-value" style="color:#2A7DC9;">{fmt_num(rv['ticket_promedio'])}</div>
    <div class="stat-label">Ticket prom.</div>
  </div>
</div>

<div class="section">
  <h2>⚠️ Alertas de stock bajo ({len(stock_bajo)})</h2>
  <table>
    <tr><th>Producto</th><th>Stock</th><th>Mínimo</th><th>Categoría</th></tr>
    {filas_stock}
  </table>
</div>

<div class="section">
  <h2>🏆 Productos más vendidos</h2>
  <table>
    <tr><th>Producto</th><th>Cantidad</th><th>Ingresos</th></tr>
    {filas_vendidos}
  </table>
</div>

<div class="section">
  <h2>📋 Últimas ventas ({len(ultimas)})</h2>
  <table>
    <tr><th>#</th><th>Fecha</th><th>Total</th><th>Pago</th></tr>
    {filas_ventas}
  </table>
</div>

<div class="footer">
    Fika — Generado automáticamente el {ahora}
</div>

</body>
</html>"""

    filename = f"reporte_{periodo}_{datetime.now().strftime('%Y%m%d_%H%M')}.html"
    return Response(
        content=html,
        media_type="text/html",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ────────────────────────────────────────────
# SPRINT 7 — BACKUP PROTEGIDO
# ────────────────────────────────────────────

@app.get("/api/backup")
def descargar_backup(request: Request, clave: str = ""):
    """
    Descarga el archivo erp.db completo.
    Requiere clave secreta configurada en variable de entorno BACKUP_KEY.
    """
    if not BACKUP_KEY:
        raise HTTPException(403, "Backup no configurado. Define BACKUP_KEY en Railway.")
    clave_header = request.headers.get("X-Backup-Key", "")
    clave_efectiva = clave_header or clave
    if not secrets.compare_digest(clave_efectiva, BACKUP_KEY):
        raise HTTPException(403, "Clave incorrecta")
    if not os.path.exists(DB_PATH):
        raise HTTPException(404, "Base de datos no encontrada")

    from datetime import datetime
    fecha = datetime.now().strftime("%Y%m%d_%H%M")
    return FileResponse(
        DB_PATH,
        media_type="application/octet-stream",
        filename=f"backup_erp_{fecha}.db"
    )


# ────────────────────────────────────────────
# PWA — Archivos estáticos
# ────────────────────────────────────────────

@app.get("/manifest.json")
def manifest():
    path = os.path.join(os.path.dirname(__file__), "manifest.json")
    return FileResponse(path, media_type="application/manifest+json")

@app.get("/service-worker.js")
def service_worker():
    path = os.path.join(os.path.dirname(__file__), "service-worker.js")
    return FileResponse(path, media_type="application/javascript")

@app.get("/icon-192.png")
def icon_192():
    path = os.path.join(os.path.dirname(__file__), "icon-192.png")
    return FileResponse(path, media_type="image/png")

@app.get("/icon-512.png")
def icon_512():
    path = os.path.join(os.path.dirname(__file__), "icon-512.png")
    return FileResponse(path, media_type="image/png")


# ────────────────────────────────────────────
# FRONTEND
# ────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def frontend():
    html_path = os.path.join(os.path.dirname(__file__), "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
