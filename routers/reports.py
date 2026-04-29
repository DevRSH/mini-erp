from fastapi import APIRouter, HTTPException
from database import get_db

router = APIRouter(tags=["Reportes"])

@router.get("/api/reportes/stock-bajo")
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

@router.get("/api/reportes/mas-vendidos")
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

@router.get("/api/reportes/resumen")
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

@router.get("/api/reportes/ventas-diarias")
def ventas_diarias(dias: int = 7):
    """Retorna ventas e ingresos agrupados por día para gráficas."""
    dias = max(1, min(dias, 30))
    with get_db() as conn:
        rows = conn.execute(
            """SELECT date(created_at, 'localtime') AS fecha,
                      COUNT(*) AS total_ventas,
                      COALESCE(SUM(total), 0) AS ingresos
               FROM ventas
               WHERE created_at >= date('now', ? || ' days', 'localtime')
                 AND estado = 'active'
               GROUP BY fecha
               ORDER BY fecha""",
            (f"-{dias}",)
        ).fetchall()
        return [dict(r) for r in rows]

@router.get("/api/reportes/sin-movimiento")
def productos_sin_movimiento(dias: int = 30):
    """
    Busca productos que no han tenido ningún movimiento (venta, compra, ajuste)
    en los últimos X días.
    """
    dias = max(1, min(dias, 365))
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT p.id, p.nombre, p.stock, p.categoria,
                   MAX(COALESCE(m.created_at, '1970-01-01')) as ultimo_movimiento
            FROM productos p
            LEFT JOIN inventory_movement_items mi ON mi.producto_id = p.id
            LEFT JOIN inventory_movements m ON mi.movimiento_id = m.id
            WHERE p.activo = 1
            GROUP BY p.id
            HAVING ultimo_movimiento < date('now', ? || ' days', 'localtime')
            ORDER BY ultimo_movimiento ASC
            """,
            (f"-{dias}",)
        ).fetchall()
        
        resultado = []
        for r in rows:
            d = dict(r)
            if d["ultimo_movimiento"] == "1970-01-01":
                d["ultimo_movimiento"] = "Nunca"
            resultado.append(d)
        return resultado

