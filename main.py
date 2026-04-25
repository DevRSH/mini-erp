"""
main.py — Mini ERP | FastAPI Backend
Sprint 4: Variantes, código proveedor, costo envío, margen, escáner
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from database import init_db, init_compras, get_db
import os

app = FastAPI(title="Mini ERP", version="2.0.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def startup():
    init_db()
    init_compras()

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


# ────────────────────────────────────────────
# SPRINT 1 — INVENTARIO
# ────────────────────────────────────────────

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
        return {"mensaje": "Variante desactivada"}


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

@app.post("/api/ventas", status_code=201)
def registrar_venta(venta: VentaCrear):
    with get_db() as conn:
        items_validados = []
        total = 0.0

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
                    (item.variante_id, item.producto_id)
                ).fetchone()
                if not v:
                    raise HTTPException(404, f"Variante {item.variante_id} no encontrada")
                if v["stock"] < item.cantidad:
                    etiqueta = f"{v['attr1_valor']}"
                    if v["attr2_valor"]:
                        etiqueta += f" / {v['attr2_valor']}"
                    raise HTTPException(400,
                        f"Stock insuficiente: '{p['nombre']}' ({etiqueta}). "
                        f"Disponible: {v['stock']}, solicitado: {item.cantidad}")
            else:
                if p["stock"] < item.cantidad:
                    raise HTTPException(400,
                        f"Stock insuficiente: '{p['nombre']}'. "
                        f"Disponible: {p['stock']}, solicitado: {item.cantidad}")

            subtotal = p["precio"] * item.cantidad
            total += subtotal
            items_validados.append({
                "producto_id": item.producto_id,
                "variante_id": item.variante_id,
                "nombre": p["nombre"],
                "cantidad": item.cantidad,
                "precio_unitario": p["precio"],
                "subtotal": subtotal,
                "tiene_variantes": bool(p["tiene_variantes"]),
            })

        # Persistencia atómica
        cursor = conn.execute(
            "INSERT INTO ventas (total, metodo_pago) VALUES (?,?)", (total, venta.metodo_pago)
        )
        venta_id = cursor.lastrowid

        for item in items_validados:
            conn.execute(
                """INSERT INTO detalle_venta
                   (venta_id, producto_id, variante_id, cantidad, precio_unitario, subtotal)
                   VALUES (?,?,?,?,?,?)""",
                (venta_id, item["producto_id"], item["variante_id"],
                 item["cantidad"], item["precio_unitario"], item["subtotal"])
            )
            if item["tiene_variantes"]:
                conn.execute(
                    "UPDATE variantes SET stock = stock - ? WHERE id=?",
                    (item["cantidad"], item["variante_id"])
                )
                # Resincronizar stock total del producto
                total_var = conn.execute(
                    "SELECT COALESCE(SUM(stock),0) as t FROM variantes WHERE producto_id=? AND activo=1",
                    (item["producto_id"],)
                ).fetchone()["t"]
                conn.execute("UPDATE productos SET stock=? WHERE id=?",
                             (total_var, item["producto_id"]))
            else:
                conn.execute(
                    "UPDATE productos SET stock = stock - ? WHERE id=?",
                    (item["cantidad"], item["producto_id"])
                )

        return {"venta_id": venta_id, "total": total,
                "metodo_pago": venta.metodo_pago, "items": items_validados}


@app.get("/api/ventas")
def historial_ventas(limite: int = 50):
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
            resultado.append({**dict(v), "items": [dict(d) for d in detalles]})
        return resultado


# ────────────────────────────────────────────
# SPRINT 3 — REPORTES
# ────────────────────────────────────────────

@app.get("/api/reportes/stock-bajo")
def stock_bajo():
    with get_db() as conn:
        productos = conn.execute(
            """SELECT id, nombre, stock, stock_minimo, categoria, tiene_variantes,
                      (stock_minimo - stock) AS unidades_faltantes
               FROM productos
               WHERE activo=1 AND stock <= stock_minimo
               ORDER BY unidades_faltantes DESC"""
        ).fetchall()

        resultado = []
        for p in productos:
            item = dict(p)
            if p["tiene_variantes"]:
                vars_bajas = conn.execute(
                    """SELECT attr1_nombre, attr1_valor, attr2_nombre, attr2_valor,
                              stock, stock_minimo
                       FROM variantes
                       WHERE producto_id=? AND activo=1 AND stock <= stock_minimo""",
                    (p["id"],)
                ).fetchall()
                item["variantes_bajas"] = [dict(v) for v in vars_bajas]
            resultado.append(item)
        return resultado


@app.get("/api/reportes/mas-vendidos")
def mas_vendidos(limite: int = 10):
    with get_db() as conn:
        rows = conn.execute(
            """SELECT p.id, p.nombre, p.categoria,
                      SUM(d.cantidad) AS total_vendido,
                      SUM(d.subtotal) AS ingresos_totales
               FROM detalle_venta d
               JOIN productos p ON d.producto_id = p.id
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
                FROM ventas WHERE {filtros[periodo]}"""
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


@app.post("/api/compras", status_code=201)
def registrar_compra(compra: CompraCrear):
    """
    Registra una compra a proveedor.
    Sube el stock de cada producto/variante atómicamente.
    Opcionalmente actualiza el costo unitario del producto.
    """
    with get_db() as conn:
        items_validados = []
        subtotal = 0.0

        # Fase 1: validar todos los ítems
        for item in compra.items:
            p = conn.execute(
                "SELECT * FROM productos WHERE id=? AND activo=1", (item.producto_id,)
            ).fetchone()
            if not p:
                raise HTTPException(404, f"Producto ID {item.producto_id} no existe")

            if item.variante_id:
                v = conn.execute(
                    "SELECT * FROM variantes WHERE id=? AND producto_id=? AND activo=1",
                    (item.variante_id, item.producto_id)
                ).fetchone()
                if not v:
                    raise HTTPException(404, f"Variante {item.variante_id} no encontrada")

            sub = item.costo_unitario * item.cantidad
            subtotal += sub
            items_validados.append({
                "producto_id": item.producto_id,
                "variante_id": item.variante_id,
                "cantidad": item.cantidad,
                "costo_unitario": item.costo_unitario,
                "subtotal": sub,
                "nombre": p["nombre"],
                "tiene_variantes": bool(p["tiene_variantes"]),
            })

        total = subtotal + compra.costo_envio

        # Fase 2: persistir
        cursor = conn.execute(
            "INSERT INTO compras (proveedor, notas, subtotal, costo_envio, total) VALUES (?,?,?,?,?)",
            (compra.proveedor, compra.notas, subtotal, compra.costo_envio, total)
        )
        compra_id = cursor.lastrowid

        for item in items_validados:
            conn.execute(
                """INSERT INTO detalle_compra
                   (compra_id, producto_id, variante_id, cantidad, costo_unitario, subtotal)
                   VALUES (?,?,?,?,?,?)""",
                (compra_id, item["producto_id"], item["variante_id"],
                 item["cantidad"], item["costo_unitario"], item["subtotal"])
            )

            if item["tiene_variantes"] and item["variante_id"]:
                conn.execute(
                    "UPDATE variantes SET stock = stock + ? WHERE id=?",
                    (item["cantidad"], item["variante_id"])
                )
                # Resincronizar stock total del producto
                total_var = conn.execute(
                    "SELECT COALESCE(SUM(stock),0) as t FROM variantes WHERE producto_id=? AND activo=1",
                    (item["producto_id"],)
                ).fetchone()["t"]
                conn.execute("UPDATE productos SET stock=? WHERE id=?",
                             (total_var, item["producto_id"]))
            else:
                conn.execute(
                    "UPDATE productos SET stock = stock + ? WHERE id=?",
                    (item["cantidad"], item["producto_id"])
                )

            # Actualizar costo del producto si se solicita
            if compra.actualizar_costo and not item["variante_id"]:
                conn.execute(
                    "UPDATE productos SET costo=? WHERE id=?",
                    (item["costo_unitario"], item["producto_id"])
                )

        return {
            "compra_id": compra_id,
            "proveedor": compra.proveedor,
            "subtotal": subtotal,
            "costo_envio": compra.costo_envio,
            "total": total,
            "items": items_validados,
        }


@app.get("/api/compras")
def historial_compras(limite: int = 50):
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
            resultado.append({**dict(c), "items": [dict(d) for d in detalles]})
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
        return {**dict(c), "items": [dict(d) for d in detalles]}


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
                FROM ventas v WHERE {filtros[periodo]}"""
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
                FROM ventas v WHERE {filtros[periodo]}
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
  <h1>🏪 Reporte Mini ERP</h1>
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
  Mini ERP — Generado automáticamente el {ahora}
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
