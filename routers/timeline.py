"""
routers/timeline.py — Timeline unificado del negocio
Combina ventas, compras, movimientos y cancelaciones en una vista cronológica.
"""

from fastapi import APIRouter
from database import get_db
from services.logic import _to_iso_dt

router = APIRouter(tags=["Timeline"])


@router.get("/api/timeline")
def timeline(
    tipo: str = None,
    desde: str = None,
    hasta: str = None,
    page: int = 1,
    limit: int = 30,
):
    limit = max(1, min(limit, 100))
    offset = (max(1, page) - 1) * limit

    with get_db() as conn:
        eventos = []

        # ── Ventas ──
        if not tipo or tipo == "venta":
            ventas = conn.execute(
                _filtrar_fecha("""
                    SELECT v.id, 'venta' as tipo, v.total as monto,
                           v.metodo_pago as detalle, v.estado, v.created_at
                    FROM ventas v WHERE 1=1
                """, desde, hasta)
            ).fetchall()
            for v in ventas:
                d = dict(v)
                estado = d["estado"]
                d["icono"] = "💰" if estado == "active" else "❌"
                d["titulo"] = f"Venta #{d['id']:04d}"
                d["descripcion"] = f"{d['detalle']} — {_fmt_money(d['monto'])}"
                if estado == "cancelled":
                    d["tipo"] = "cancelacion"
                    d["titulo"] += " (cancelada)"
                d["created_at"] = _to_iso_dt(d["created_at"])
                
                # Cargar items de la venta
                items = conn.execute("""
                    SELECT p.nombre, var.attr1_valor, var.attr2_valor, dv.cantidad
                    FROM detalle_venta dv
                    JOIN productos p ON dv.producto_id = p.id
                    LEFT JOIN variantes var ON dv.variante_id = var.id
                    WHERE dv.venta_id = ?
                """, (d["id"],)).fetchall()
                d["items"] = []
                for it in items:
                    etiq = f" ({it['attr1_valor']}{'/' + it['attr2_valor'] if it['attr2_valor'] else ''})" if it['attr1_valor'] else ""
                    d["items"].append(f"{it['nombre']}{etiq} x{it['cantidad']}")
                
                eventos.append(d)

        # ── Compras ──
        if not tipo or tipo == "compra":
            compras = conn.execute(
                _filtrar_fecha("""
                    SELECT c.id, 'compra' as tipo, c.total as monto,
                           c.proveedor as detalle, c.estado, c.created_at
                    FROM compras c WHERE 1=1
                """, desde, hasta)
            ).fetchall()
            for c in compras:
                d = dict(c)
                estado = d["estado"]
                d["icono"] = "🚚" if estado == "active" else "❌"
                d["titulo"] = f"Compra #{d['id']:04d}"
                d["descripcion"] = f"{d['detalle']} — {_fmt_money(d['monto'])}"
                if estado == "cancelled":
                    d["tipo"] = "cancelacion"
                    d["titulo"] += " (cancelada)"
                d["created_at"] = _to_iso_dt(d["created_at"])
                
                # Cargar items de la compra
                items = conn.execute("""
                    SELECT p.nombre, var.attr1_valor, var.attr2_valor, dc.cantidad
                    FROM detalle_compra dc
                    JOIN productos p ON dc.producto_id = p.id
                    LEFT JOIN variantes var ON dc.variante_id = var.id
                    WHERE dc.compra_id = ?
                """, (d["id"],)).fetchall()
                d["items"] = []
                for it in items:
                    etiq = f" ({it['attr1_valor']}{'/' + it['attr2_valor'] if it['attr2_valor'] else ''})" if it['attr1_valor'] else ""
                    d["items"].append(f"{it['nombre']}{etiq} x{it['cantidad']}")
                
                eventos.append(d)

        # ── Movimientos de inventario (ajustes/merma) ──
        if not tipo or tipo in ("ajuste", "merma"):
            tipo_filtro = ""
            if tipo:
                tipo_filtro = f" AND m.tipo = '{tipo}'"
            movs = conn.execute(
                _filtrar_fecha(f"""
                    SELECT m.id, m.tipo, m.motivo as detalle, m.referencia, m.created_at
                    FROM inventory_movements m
                    WHERE m.tipo IN ('ajuste', 'merma'){tipo_filtro}
                """, desde, hasta)
            ).fetchall()
            for m in movs:
                d = dict(m)
                d["icono"] = "📦" if d["tipo"] == "ajuste" else "⚠️"
                d["titulo"] = f"{'Ajuste' if d['tipo'] == 'ajuste' else 'Merma'} #{d['id']:04d}"
                d["descripcion"] = d["detalle"]
                d["monto"] = None
                d["estado"] = "active"
                d["created_at"] = _to_iso_dt(d["created_at"])
                
                # Cargar items del movimiento
                items = conn.execute("""
                    SELECT p.nombre, var.attr1_valor, var.attr2_valor, mi.cantidad, mi.stock_antes, mi.stock_despues
                    FROM inventory_movement_items mi
                    JOIN productos p ON mi.producto_id = p.id
                    LEFT JOIN variantes var ON mi.variante_id = var.id
                    WHERE mi.movimiento_id = ?
                """, (d["id"],)).fetchall()
                d["items"] = []
                for it in items:
                    etiq = f" ({it['attr1_valor']}{'/' + it['attr2_valor'] if it['attr2_valor'] else ''})" if it['attr1_valor'] else ""
                    cambio = f"{it['stock_antes']} ➡️ {it['stock_despues']}"
                    d["items"].append(f"{it['nombre']}{etiq}: {cambio} ({'+' if it['cantidad'] > 0 else ''}{it['cantidad']})")
                
                eventos.append(d)

        # Ordenar por fecha descendente
        eventos.sort(key=lambda e: e.get("created_at", ""), reverse=True)

        total = len(eventos)
        paginated = eventos[offset:offset + limit]

        return {
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit,
            "eventos": paginated,
        }


def _filtrar_fecha(query: str, desde: str = None, hasta: str = None) -> str:
    if desde:
        query += f" AND date(created_at) >= '{desde}'"
    if hasta:
        query += f" AND date(created_at) <= '{hasta}'"
    return query


def _fmt_money(amount) -> str:
    if amount is None:
        return "$0"
    return f"${int(amount):,}".replace(",", ".")
