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
    """
    Timeline unificado del negocio.
    
    Params:
        tipo: filtrar por 'venta', 'compra', 'ajuste', 'merma', 'cancelacion'
        desde: fecha inicio (YYYY-MM-DD)
        hasta: fecha fin (YYYY-MM-DD)
        page: página (1-indexed)
        limit: items por página (max 100)
    """
    limit = max(1, min(limit, 100))
    offset = (max(1, page) - 1) * limit

    with get_db() as conn:
        eventos = []

        # ── Ventas ──
        if not tipo or tipo == "venta":
            ventas = conn.execute(
                _filtrar_fecha("""
                    SELECT id, 'venta' as tipo, total as monto,
                           metodo_pago as detalle, estado, created_at
                    FROM ventas WHERE 1=1
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
                eventos.append(d)

        # ── Compras ──
        if not tipo or tipo == "compra":
            compras = conn.execute(
                _filtrar_fecha("""
                    SELECT id, 'compra' as tipo, total as monto,
                           proveedor as detalle, estado, created_at
                    FROM compras WHERE 1=1
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
                eventos.append(d)

        # ── Movimientos de inventario (ajustes/merma) ──
        if not tipo or tipo in ("ajuste", "merma"):
            tipo_filtro = ""
            if tipo:
                tipo_filtro = f" AND tipo = '{tipo}'"
            movs = conn.execute(
                _filtrar_fecha(f"""
                    SELECT id, tipo, motivo as detalle, referencia, created_at
                    FROM inventory_movements
                    WHERE tipo IN ('ajuste', 'merma'){tipo_filtro}
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
    """Agrega filtros de fecha al query."""
    if desde:
        query += f" AND date(created_at) >= '{desde}'"
    if hasta:
        query += f" AND date(created_at) <= '{hasta}'"
    return query


def _fmt_money(amount) -> str:
    if amount is None:
        return "$0"
    return f"${int(amount):,}".replace(",", ".")
