from typing import Optional
from fastapi import APIRouter, HTTPException
from database import get_db
from schemas.schemas import ProductoCrear, ProductoEditar, AjusteStock, VarianteCrear, VarianteEditar, AjusteVariante
from services.logic import _producto_full
from services.inventory import registrar_movimiento

router = APIRouter(tags=["Productos"])

@router.get("/api/products")
@router.get("/api/productos")
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

@router.post("/api/products", status_code=201)
@router.post("/api/productos", status_code=201)
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

@router.put("/api/products/{id}")
@router.put("/api/productos/{id}")
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

@router.delete("/api/products/{id}")
@router.delete("/api/productos/{id}")
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

@router.post("/api/products/{id}/adjust")
@router.post("/api/productos/{id}/ajuste")
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
        
        # RF03: Registrar en Timeline
        registrar_movimiento(conn, "ajuste", ajuste.motivo or "Ajuste manual", [{
            "producto_id": id,
            "variante_id": None,
            "cantidad": ajuste.cantidad,
            "stock_antes": p["stock"],
            "stock_despues": nuevo
        }], referencia="ajuste_manual")

        return {"producto": p["nombre"], "stock_anterior": p["stock"],
                "ajuste": ajuste.cantidad, "stock_nuevo": nuevo}

@router.get("/api/products/{id}/variants")
@router.get("/api/productos/{id}/variantes")
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

@router.post("/api/products/{id}/variants", status_code=201)
@router.post("/api/productos/{id}/variantes", status_code=201)
def crear_variante(id: int, datos: VarianteCrear):
    with get_db() as conn:
        p = conn.execute(
            "SELECT * FROM productos WHERE id=? AND activo=1", (id,)
        ).fetchone()
        if not p:
            raise HTTPException(404, f"Producto {id} no encontrado")

        if not p["tiene_variantes"]:
            conn.execute("UPDATE productos SET tiene_variantes=1, stock=0 WHERE id=?", (id,))

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

@router.put("/api/variantes/{id}")
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

@router.delete("/api/variantes/{id}")
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

@router.post("/api/variantes/{id}/ajuste")
def ajustar_stock_variante(id: int, ajuste: AjusteVariante):
    with get_db() as conn:
        v = conn.execute("SELECT * FROM variantes WHERE id=? AND activo=1", (id,)).fetchone()
        if not v:
            raise HTTPException(404, f"Variante {id} no encontrada")

        nuevo = v["stock"] + ajuste.cantidad
        if nuevo < 0:
            raise HTTPException(400, f"Stock insuficiente. Actual: {v['stock']}")

        conn.execute("UPDATE variantes SET stock=? WHERE id=?", (nuevo, id))

        total = conn.execute(
            "SELECT COALESCE(SUM(stock),0) as t FROM variantes WHERE producto_id=? AND activo=1",
            (v["producto_id"],)
        ).fetchone()["t"]
        conn.execute("UPDATE productos SET stock=? WHERE id=?", (total, v["producto_id"]))

        # RF03: Registrar en Timeline
        registrar_movimiento(conn, "ajuste", ajuste.motivo or "Ajuste manual", [{
            "producto_id": v["producto_id"],
            "variante_id": id,
            "cantidad": ajuste.cantidad,
            "stock_antes": v["stock"],
            "stock_despues": nuevo
        }], referencia="ajuste_manual")

        return {"variante_id": id, "stock_anterior": v["stock"],
                "ajuste": ajuste.cantidad, "stock_nuevo": nuevo}

@router.get("/api/buscar")
def buscar_por_codigo(codigo: str):
    """Busca producto o variante por código de proveedor o código de barras. Usado por el escáner."""
    with get_db() as conn:
        v = conn.execute(
            """SELECT v.*, p.nombre as producto_nombre, p.precio
               FROM variantes v
               JOIN productos p ON v.producto_id = p.id
               WHERE v.codigo_barras = ? AND v.activo=1 AND p.activo=1""",
            (codigo,)
        ).fetchone()
        if v:
            return {"tipo": "variante", "datos": dict(v)}

        p = conn.execute(
            "SELECT * FROM productos WHERE codigo_proveedor=? AND activo=1", (codigo,)
        ).fetchone()
        if p:
            return {"tipo": "producto", "datos": _producto_full(p)}

        raise HTTPException(404, f"No se encontró ningún producto con código '{codigo}'")

@router.get("/api/categorias")
def listar_categorias():
    with get_db() as conn:
        rows = conn.execute("SELECT DISTINCT categoria FROM productos WHERE activo=1 ORDER BY categoria").fetchall()
        return [r["categoria"] for r in rows if r["categoria"]]

@router.put("/api/categorias/renombrar")
def renombrar_categoria(datos: dict):
    nombre_actual = datos.get("nombre_actual")
    nombre_nuevo = datos.get("nombre_nuevo")
    if not nombre_actual or not nombre_nuevo:
        raise HTTPException(400, "nombre_actual y nombre_nuevo son requeridos")
    
    with get_db() as conn:
        conn.execute("UPDATE productos SET categoria=? WHERE categoria=?", (nombre_nuevo, nombre_actual))
        return {"mensaje": f"Categoría '{nombre_actual}' renombrada a '{nombre_nuevo}'"}
