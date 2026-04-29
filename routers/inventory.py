"""
routers/inventory.py — Movimientos de inventario y conteo físico
"""

from fastapi import APIRouter, HTTPException
from database import get_db
from schemas.schemas import ConteoFisico
from services.inventory import comparar_conteo_fisico, confirmar_conteo_fisico
from services.logic import _to_iso_dt

router = APIRouter(tags=["Inventario"])


@router.get("/api/movimientos")
def listar_movimientos(tipo: str = None, limite: int = 50):
    """Lista movimientos de inventario con filtro opcional por tipo."""
    limite = max(1, min(limite, 200))
    with get_db() as conn:
        query = """
            SELECT m.*, GROUP_CONCAT(
                p.nombre || ':' || mi.cantidad || ':' || mi.stock_antes || '→' || mi.stock_despues,
                ' | '
            ) AS resumen_items
            FROM inventory_movements m
            LEFT JOIN inventory_movement_items mi ON mi.movimiento_id = m.id
            LEFT JOIN productos p ON mi.producto_id = p.id
            WHERE 1=1
        """
        params = []
        if tipo:
            query += " AND m.tipo = ?"
            params.append(tipo)
        query += " GROUP BY m.id ORDER BY m.created_at DESC, m.id DESC LIMIT ?"
        params.append(limite)

        rows = conn.execute(query, params).fetchall()
        resultado = []
        for r in rows:
            d = dict(r)
            d["created_at"] = _to_iso_dt(d.get("created_at"))
            resultado.append(d)
        return resultado


@router.get("/api/movimientos/{id}")
def detalle_movimiento(id: int):
    """Detalle de un movimiento con todos sus items."""
    with get_db() as conn:
        mov = conn.execute(
            "SELECT * FROM inventory_movements WHERE id=?", (id,)
        ).fetchone()
        if not mov:
            raise HTTPException(404, f"Movimiento {id} no encontrado")

        items = conn.execute(
            """SELECT mi.*, p.nombre as producto_nombre,
                      v.attr1_valor, v.attr2_valor
               FROM inventory_movement_items mi
               JOIN productos p ON mi.producto_id = p.id
               LEFT JOIN variantes v ON mi.variante_id = v.id
               WHERE mi.movimiento_id = ?
               ORDER BY mi.id""",
            (id,),
        ).fetchall()

        result = dict(mov)
        result["created_at"] = _to_iso_dt(result.get("created_at"))
        result["items"] = [dict(i) for i in items]
        return result


@router.post("/api/inventario/conteo")
def comparar_conteo(conteo: ConteoFisico):
    """Compara cantidades físicas vs sistema. No modifica datos."""
    with get_db() as conn:
        items_raw = [
            {"producto_id": i.producto_id, "variante_id": i.variante_id,
             "cantidad_fisica": i.cantidad_fisica}
            for i in conteo.items
        ]
        return comparar_conteo_fisico(conn, items_raw)


@router.post("/api/inventario/confirmar-conteo", status_code=201)
def confirmar_conteo(conteo: ConteoFisico):
    """Aplica las diferencias del conteo físico y genera documento de ajuste."""
    with get_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        items_raw = [
            {"producto_id": i.producto_id, "variante_id": i.variante_id,
             "cantidad_fisica": i.cantidad_fisica}
            for i in conteo.items
        ]
        return confirmar_conteo_fisico(conn, items_raw, motivo=conteo.motivo)
