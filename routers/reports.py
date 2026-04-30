from fastapi import APIRouter, HTTPException
from database import get_db
from datetime import datetime, timedelta
from typing import Optional, List

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
        return resultado


@router.get("/api/reportes/proyeccion-compras")
def proyeccion_compras(dias_historial: int = 30):
    """
    Sugerencia inteligente de compras basada en Venta Promedio Diaria (VPD).
    """
    with get_db() as conn:
        # 1. Calcular VPD (Venta Promedio Diaria) por producto
        # Dividimos por dias_historial para sacar el promedio diario
        vpd_query = f"""
            SELECT producto_id, SUM(cantidad) as total_vendido
            FROM detalle_venta dv
            JOIN ventas v ON dv.venta_id = v.id
            WHERE v.estado = 'active' 
              AND v.created_at >= date('now', '-{dias_historial} days', 'localtime')
            GROUP BY producto_id
        """
        ventas = {r["producto_id"]: r["total_vendido"] / dias_historial for r in conn.execute(vpd_query).fetchall()}

        # 2. Obtener productos activos
        productos = conn.execute(
            "SELECT id, nombre, stock, stock_minimo, categoria FROM productos WHERE activo=1"
        ).fetchall()

        sugerencias = []
        for p in productos:
            vpd = ventas.get(p["id"], 0)
            dias_cobertura = (p["stock"] / vpd) if vpd > 0 else 999
            
            # Criterio: Cobertura < 7 días O stock < mínimo
            if dias_cobertura < 7 or p["stock"] <= p["stock_minimo"]:
                # Sugerimos comprar para cubrir 15 días + stock mínimo
                cantidad_sugerida = max(0, (vpd * 15) + p["stock_minimo"] - p["stock"])
                if cantidad_sugerida > 0:
                    sugerencias.append({
                        "id": p["id"],
                        "nombre": p["nombre"],
                        "categoria": p["categoria"],
                        "stock_actual": p["stock"],
                        "stock_minimo": p["stock_minimo"],
                        "venta_diaria_promedio": round(vpd, 2),
                        "dias_cobertura_restante": round(dias_cobertura, 1) if vpd > 0 else "∞",
                        "cantidad_sugerida": int(cantidad_sugerida + 0.99) # Redondear hacia arriba
                    })
        
        sugerencias.sort(key=lambda x: x["dias_cobertura_restante"] if isinstance(x["dias_cobertura_restante"], (int, float)) else 999)
        return sugerencias


@router.get("/api/reportes/margenes-categoria")
def margenes_por_categoria():
    """Análisis de rentabilidad agrupado por categoría."""
    with get_db() as conn:
        query = """
            SELECT p.categoria,
                   SUM(d.subtotal) AS ingresos,
                   SUM(d.cantidad * (p.costo + COALESCE(p.costo_envio,0))) AS costos,
                   SUM(d.subtotal - (d.cantidad * (p.costo + COALESCE(p.costo_envio,0)))) AS ganancia
            FROM detalle_venta d
            JOIN productos p ON d.producto_id = p.id
            JOIN ventas v ON d.venta_id = v.id
            WHERE v.estado = 'active'
            GROUP BY p.categoria
            ORDER BY ganancia DESC
        """
        rows = conn.execute(query).fetchall()
        resultado = []
        for r in rows:
            d = dict(r)
            d["margen_pct"] = round((d["ganancia"] / d["ingresos"] * 100), 1) if d["ingresos"] > 0 else 0
            resultado.append(d)
        return resultado


@router.get("/api/reportes/exportar-full")
def exportar_full():
    """Genera un volcado completo de movimientos e inventario para CSV."""
    with get_db() as conn:
        # Movimientos detallados
        movs = conn.execute("""
            SELECT m.id, m.tipo, m.motivo, m.created_at,
                   p.nombre as producto, p.categoria,
                   mi.cantidad, mi.stock_antes, mi.stock_despues
            FROM inventory_movements m
            JOIN inventory_movement_items mi ON mi.movimiento_id = m.id
            JOIN productos p ON mi.producto_id = p.id
            ORDER BY m.created_at DESC
        """).fetchall()
        
        # Inventario actual
        inv = conn.execute("""
            SELECT id, nombre, categoria, stock, costo, precio, stock_minimo
            FROM productos WHERE activo=1
        """).fetchall()
        
        return {
            "movimientos": [dict(m) for m in movs],
            "inventario": [dict(i) for i in inv]
        }
@router.get("/api/reportes/tablero")
def tablero(desde: str, hasta: str):
    """Reporte de Tablero de Control con comparación de periodos."""
    try:
        dt_desde = datetime.strptime(desde, "%Y-%m-%d")
        dt_hasta = datetime.strptime(hasta, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(400, "Formato de fecha inválido. Use YYYY-MM-DD")

    if dt_hasta < dt_desde:
        raise HTTPException(400, "La fecha 'hasta' no puede ser anterior a 'desde'")
    
    # Calcular periodo anterior (mismo número de días)
    dias = (dt_hasta - dt_desde).days + 1
    dt_desde_ant = dt_desde - timedelta(days=dias)
    dt_hasta_ant = dt_desde - timedelta(days=1)
    
    desde_ant = dt_desde_ant.strftime("%Y-%m-%d")
    hasta_ant = dt_hasta_ant.strftime("%Y-%m-%d")
    
    def get_period_stats(conn, d, h):
        where = f"date(created_at, 'localtime') BETWEEN date('{d}') AND date('{h}') AND estado='active'"
        
        # Básicos
        rv = conn.execute(
            f"""SELECT COUNT(*) AS total_ventas,
                       COALESCE(SUM(total),0) AS ingresos,
                       COALESCE(AVG(total),0) AS ticket_promedio
                FROM ventas WHERE {where}"""
        ).fetchone()
        
        # Ganancia
        ganancia = conn.execute(
            f"""SELECT COALESCE(SUM(
                    d.subtotal - (d.cantidad * (p.costo + COALESCE(p.costo_envio,0)))
                ), 0) AS ganancia_estimada
                FROM detalle_venta d
                JOIN productos p ON d.producto_id = p.id
                JOIN ventas v ON d.venta_id = v.id
                WHERE date(v.created_at, 'localtime') BETWEEN date('{d}') AND date('{h}') AND v.estado='active'"""
        ).fetchone()
        
        return {
            "ventas": rv["total_ventas"],
            "ingresos": float(rv["ingresos"]),
            "ticket_promedio": float(round(rv["ticket_promedio"], 2)),
            "ganancia_estimada": float(round(ganancia["ganancia_estimada"], 2))
        }

    with get_db() as conn:
        actual = get_period_stats(conn, desde, hasta)
        anterior = get_period_stats(conn, desde_ant, hasta_ant)
        
        def calc_variation(act, ant):
            if ant == 0: return None
            return round(((act - ant) / ant) * 100, 1)
        
        variacion = {
            "ventas_pct": calc_variation(actual["ventas"], anterior["ventas"]),
            "ingresos_pct": calc_variation(actual["ingresos"], anterior["ingresos"]),
            "ganancia_pct": calc_variation(actual["ganancia_estimada"], anterior["ganancia_estimada"])
        }
        
        # Desglose por método
        por_metodo = {}
        for m in ["efectivo", "transferencia", "tarjeta"]:
            row = conn.execute(
                f"""SELECT COUNT(*) AS v, COALESCE(SUM(total),0) AS t
                    FROM ventas 
                    WHERE date(created_at, 'localtime') BETWEEN date('{desde}') AND date('{hasta}') 
                      AND estado='active' AND metodo_pago=?""",
                (m,)
            ).fetchone()
            por_metodo[m] = {
                "ventas": row["v"],
                "total": float(row["t"]),
                "pct": round((row["t"] / actual["ingresos"] * 100), 1) if actual["ingresos"] > 0 else 0
            }
            
        # Top 5 productos
        top = conn.execute(
            f"""SELECT p.nombre, SUM(d.cantidad) AS total_vendido, SUM(d.subtotal) AS ingresos
                FROM detalle_venta d
                JOIN productos p ON d.producto_id = p.id
                JOIN ventas v ON d.venta_id = v.id
                WHERE date(v.created_at, 'localtime') BETWEEN date('{desde}') AND date('{hasta}') 
                  AND v.estado='active'
                GROUP BY p.id
                ORDER BY total_vendido DESC
                LIMIT 5"""
        ).fetchall()
        
        # Alertas de stock total (badge)
        alertas = conn.execute(
            "SELECT COUNT(*) AS c FROM productos WHERE activo=1 AND stock <= stock_minimo"
        ).fetchone()
        
        return {
            "periodo": {"desde": desde, "hasta": hasta, "desde_ant": desde_ant, "hasta_ant": hasta_ant},
            "actual": actual,
            "anterior": anterior,
            "variacion": variacion,
            "por_metodo": por_metodo,
            "top_productos": [dict(t) for t in top],
            "alertas_stock": alertas["c"]
        }

@router.get("/api/reportes/rentabilidad")
def rentabilidad(desde: str, hasta: str):
    """Reporte de Rentabilidad detallado."""
    try:
        datetime.strptime(desde, "%Y-%m-%d")
        datetime.strptime(hasta, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(400, "Formato de fecha inválido. Use YYYY-MM-DD")

    with get_db() as conn:
        # 1. Resumen General
        resumen_ventas = conn.execute(
            f"""SELECT 
                    COALESCE(SUM(total), 0) as ingresos,
                    COALESCE(SUM(subtotal), 0) as subtotal_bruto
                FROM ventas 
                WHERE date(created_at, 'localtime') BETWEEN date('{desde}') AND date('{hasta}') 
                  AND estado='active'"""
        ).fetchone()

        costos_prod = conn.execute(
            f"""SELECT 
                    COALESCE(SUM(d.cantidad * p.costo), 0) as costo_mercaderia,
                    COALESCE(SUM(d.cantidad * COALESCE(p.costo_envio, 0)), 0) as costo_envios
                FROM detalle_venta d
                JOIN productos p ON d.producto_id = p.id
                JOIN ventas v ON d.venta_id = v.id
                WHERE date(v.created_at, 'localtime') BETWEEN date('{desde}') AND date('{hasta}') 
                  AND v.estado='active'"""
        ).fetchone()

        total_compras = conn.execute(
            f"""SELECT COALESCE(SUM(total), 0) as total
                FROM compras 
                WHERE date(created_at, 'localtime') BETWEEN date('{desde}') AND date('{hasta}') 
                  AND estado='active'"""
        ).fetchone()

        ingresos = float(resumen_ventas["ingresos"])
        c_mercaderia = float(costos_prod["costo_mercaderia"])
        c_envios = float(costos_prod["costo_envios"])
        ganancia = ingresos - c_mercaderia - c_envios
        margen_pct = round((ganancia / ingresos * 100), 1) if ingresos > 0 else 0

        resumen = {
            "ingresos": ingresos,
            "costo_mercaderia": c_mercaderia,
            "costo_envios": c_envios,
            "ganancia": ganancia,
            "margen_pct": margen_pct,
            "total_invertido_compras": float(total_compras["total"])
        }

        # 2. Por Producto
        productos_rows = conn.execute(
            f"""SELECT 
                    p.id, p.nombre, p.categoria,
                    SUM(d.cantidad) as unidades_vendidas,
                    SUM(d.cantidad * d.precio_unitario) as ingresos,
                    SUM(d.cantidad * (p.costo + COALESCE(p.costo_envio, 0))) as costo_total
                FROM detalle_venta d
                JOIN productos p ON d.producto_id = p.id
                JOIN ventas v ON d.venta_id = v.id
                WHERE date(v.created_at, 'localtime') BETWEEN date('{desde}') AND date('{hasta}') 
                  AND v.estado='active'
                GROUP BY p.id
                ORDER BY (SUM(d.cantidad * d.precio_unitario) - SUM(d.cantidad * (p.costo + COALESCE(p.costo_envio, 0)))) DESC"""
        ).fetchall()

        por_producto = []
        for r in productos_rows:
            d = dict(r)
            d["ganancia"] = round(d["ingresos"] - d["costo_total"], 2)
            d["margen_pct"] = round((d["ganancia"] / d["ingresos"] * 100), 1) if d["ingresos"] > 0 else 0
            por_producto.append(d)

        # 3. Evolución Semanal
        semanal_rows = conn.execute(
            f"""SELECT 
                    strftime('%Y-%W', v.created_at, 'localtime') as semana,
                    SUM(v.total) as ingresos,
                    SUM(v.total) - SUM(costos_venta.costo_v) as ganancia
                FROM ventas v
                JOIN (
                    SELECT venta_id, SUM(cantidad * (p.costo + COALESCE(p.costo_envio, 0))) as costo_v
                    FROM detalle_venta d
                    JOIN productos p ON d.producto_id = p.id
                    GROUP BY venta_id
                ) AS costos_venta ON v.id = costos_venta.venta_id
                WHERE date(v.created_at, 'localtime') BETWEEN date('{desde}') AND date('{hasta}') 
                  AND v.estado='active'
                GROUP BY semana
                ORDER BY semana ASC
                LIMIT 12"""
        ).fetchall()

        return {
            "periodo": {"desde": desde, "hasta": hasta},
            "resumen": resumen,
            "por_producto": por_producto,
            "evolucion_semanal": [dict(r) for r in semanal_rows]
        }

@router.get("/api/reportes/categorias")
def reporte_categorias(desde: str, hasta: str, categorias: Optional[str] = None):
    try:
        datetime.strptime(desde, "%Y-%m-%d")
        datetime.strptime(hasta, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(400, "Formato de fecha inválido")

    filtro_cat = []
    if categorias:
        filtro_cat = [c.strip() for c in categorias.split(",") if c.strip()]

    with get_db() as conn:
        # Query base para agrupar por categoría
        sql = f"""
            SELECT 
                COALESCE(p.categoria, 'Sin categoría') as nombre,
                COUNT(DISTINCT p.id) as productos_activos,
                SUM(d.cantidad) as unidades_vendidas,
                SUM(d.cantidad * d.precio_unitario) as ingresos,
                SUM(d.cantidad * (d.precio_unitario - (p.costo + COALESCE(p.costo_envio,0)))) as ganancia
            FROM detalle_venta d
            JOIN productos p ON d.producto_id = p.id
            JOIN ventas v ON d.venta_id = v.id
            WHERE date(v.created_at, 'localtime') BETWEEN date('{desde}') AND date('{hasta}')
              AND v.estado='active'
            GROUP BY nombre
        """
        rows = conn.execute(sql).fetchall()
        
        total_ingresos = sum(r["ingresos"] for r in rows) if rows else 0
        
        result_cats = []
        sin_cat = None
        
        for r in rows:
            d = dict(r)
            d["margen_pct"] = round((d["ganancia"] / d["ingresos"] * 100), 1) if d["ingresos"] > 0 else 0
            d["participacion_ingresos_pct"] = round((d["ingresos"] / total_ingresos * 100), 1) if total_ingresos > 0 else 0
            
            # Obtener top producto de esta categoría
            top_p = conn.execute(f"""
                SELECT p.nombre 
                FROM detalle_venta d
                JOIN productos p ON d.producto_id = p.id
                JOIN ventas v ON d.venta_id = v.id
                WHERE COALESCE(p.categoria, 'Sin categoría') = ?
                  AND date(v.created_at, 'localtime') BETWEEN date('{desde}') AND date('{hasta}')
                  AND v.estado='active'
                GROUP BY p.id
                ORDER BY SUM(d.cantidad) DESC
                LIMIT 1
            """, (r["nombre"],)).fetchone()
            d["top_producto"] = top_p["nombre"] if top_p else "—"
            
            if r["nombre"] == "Sin categoría":
                sin_cat = d
            else:
                if not filtro_cat or r["nombre"] in filtro_cat:
                    result_cats.append(d)

        return {
            "periodo": {"desde": desde, "hasta": hasta},
            "categorias": sorted(result_cats, key=lambda x: x["ingresos"], reverse=True),
            "sin_categoria": sin_cat or {
                "nombre": "Sin categoría", "productos_activos": 0, "unidades_vendidas": 0,
                "ingresos": 0, "ganancia": 0, "margen_pct": 0, "participacion_ingresos_pct": 0, "top_producto": "—"
            }
        }

@router.get("/api/reportes/inventario")
def reporte_inventario(fecha_corte: Optional[str] = None):
    hoy = datetime.now().date()
    if not fecha_corte:
        fecha_corte = hoy.isoformat()
    
    try:
        corte_dt = datetime.strptime(fecha_corte, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(400, "Formato de fecha_corte inválido")

    with get_db() as conn:
        # 1. Datos base de productos
        productos = conn.execute("""
            SELECT id, nombre, categoria, precio, costo, stock, stock_minimo, tiene_variantes
            FROM productos WHERE activo = 1
        """).fetchall()

        # 2. Última venta por producto/variante
        # Obtenemos la última fecha de venta para cada producto y variante (si aplica)
        # filtrada por la fecha de corte
        ultimas_ventas_raw = conn.execute("""
            SELECT 
                dv.producto_id, 
                dv.variante_id, 
                MAX(v.created_at) as ultima
            FROM detalle_venta dv
            JOIN ventas v ON dv.venta_id = v.id
            WHERE v.estado = 'active' AND date(v.created_at, 'localtime') <= date(?)
            GROUP BY dv.producto_id, dv.variante_id
        """, (fecha_corte,)).fetchall()
        
        # Mapear a dict para búsqueda rápida {(prod_id, var_id): fecha}
        ultimas_map = {}
        for r in ultimas_ventas_raw:
            ultimas_map[(r["producto_id"], r["variante_id"])] = r["ultima"]

        listado = []
        criticos = []
        resumen = {
            "valor_bodega": 0.0,
            "total_productos": 0,
            "agotados": 0,
            "bajo_minimo": 0,
            "sin_movimiento_30d": 0
        }
        
        rotacion = {"alta": [], "media": [], "baja": [], "sin_movimiento": []}

        for p in productos:
            p_id = p["id"]
            tiene_vars = bool(p["tiene_variantes"])
            
            # Para el listado completo, calculamos la última venta global del producto
            # (la más reciente entre todas sus variantes)
            ultima_p = None
            for key, val in ultimas_map.items():
                if key[0] == p_id:
                    if not ultima_p or val > ultima_p:
                        ultima_p = val
            
            dias = None
            if ultima_p:
                try:
                    ultima_dt = datetime.fromisoformat(ultima_p.replace(' ', 'T')).date()
                    dias = (corte_dt - ultima_dt).days
                except:
                    dias = None
            
            p_data = {
                "id": p_id,
                "nombre": p["nombre"],
                "categoria": p["categoria"],
                "precio": p["precio"],
                "costo": p["costo"],
                "margen_pct": round(((p["precio"] - p["costo"]) / p["precio"] * 100), 1) if p["precio"] > 0 else 0,
                "stock": p["stock"],
                "stock_minimo": p["stock_minimo"],
                "valor_bodega": round(p["stock"] * p["costo"], 2),
                "ultima_venta": ultima_p[:10] if ultima_p else None,
                "dias_sin_vender": dias,
                "tiene_variantes": tiene_vars
            }
            
            listado.append(p_data)
            
            # Resumen
            resumen["valor_bodega"] += p_data["valor_bodega"]
            resumen["total_productos"] += 1
            if p["stock"] == 0: resumen["agotados"] += 1
            if p["stock"] <= p["stock_minimo"]: resumen["bajo_minimo"] += 1
            if dias is None or dias >= 30: resumen["sin_movimiento_30d"] += 1

            # Rotación
            if dias is None or dias >= 30: rotacion["sin_movimiento"].append(p_data)
            elif dias <= 3: rotacion["alta"].append(p_data)
            elif dias <= 14: rotacion["media"].append(p_data)
            else: rotacion["baja"].append(p_data)

            # Críticos (si tiene variantes, revisar cada una)
            if tiene_vars:
                vars_rows = conn.execute("""
                    SELECT id, attr1_valor, attr2_valor, stock, stock_minimo
                    FROM variantes WHERE producto_id = ? AND activo = 1
                """, (p_id,)).fetchall()
                for v in vars_rows:
                    if v["stock"] <= v["stock_minimo"]:
                        var_nombre = v["attr2_valor"] if v["attr2_valor"] else v["attr1_valor"]
                        if v["attr2_valor"] and v["attr1_valor"]:
                            var_nombre = f"{v['attr1_valor']} / {v['attr2_valor']}"
                        
                        criticos.append({
                            "id": p_id,
                            "nombre": p["nombre"],
                            "stock": v["stock"],
                            "stock_minimo": v["stock_minimo"],
                            "variante": var_nombre
                        })
            else:
                if p["stock"] <= p["stock_minimo"]:
                    criticos.append({
                        "id": p_id,
                        "nombre": p["nombre"],
                        "stock": p["stock"],
                        "stock_minimo": p["stock_minimo"],
                        "variante": None
                    })

        resumen["valor_bodega"] = round(resumen["valor_bodega"], 2)

        return {
            "fecha_corte": fecha_corte,
            "resumen": resumen,
            "criticos": sorted(criticos, key=lambda x: x["stock"]),
            "por_rotacion": rotacion,
            "listado_completo": sorted(listado, key=lambda x: x["nombre"])
        }

@router.get("/api/reportes/compras")
def reporte_compras(desde: str, hasta: str):
    try:
        datetime.strptime(desde, "%Y-%m-%d")
        datetime.strptime(hasta, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(400, "Formato de fecha inválido")

    with get_db() as conn:
        # 1. Resumen Global
        res_global = conn.execute(f"""
            SELECT 
                COUNT(*) as num_compras,
                COALESCE(SUM(total), 0) as total_invertido,
                COALESCE(SUM(costo_envio), 0) as total_envios,
                COUNT(DISTINCT COALESCE(proveedor, 'Sin nombre')) as num_proveedores
            FROM compras
            WHERE date(created_at, 'localtime') BETWEEN date('{desde}') AND date('{hasta}')
              AND estado = 'active'
        """).fetchone()

        # 2. Por Proveedor
        rows_prov = conn.execute(f"""
            SELECT 
                COALESCE(proveedor, 'Sin nombre') as nombre,
                COUNT(*) as num_compras,
                SUM(total) as total_invertido,
                SUM(costo_envio) as total_envios,
                COUNT(DISTINCT dc.producto_id) as productos_distintos,
                MAX(c.created_at) as ultima_compra
            FROM compras c
            LEFT JOIN detalle_compra dc ON c.id = dc.compra_id
            WHERE date(c.created_at, 'localtime') BETWEEN date('{desde}') AND date('{hasta}')
              AND c.estado = 'active'
            GROUP BY nombre
            ORDER BY total_invertido DESC
        """).fetchall()

        # 3. Productos más comprados (costo promedio ponderado)
        rows_prods = conn.execute(f"""
            SELECT 
                p.nombre,
                p.categoria,
                p.costo as costo_actual,
                SUM(dc.cantidad) as unidades_compradas,
                SUM(dc.cantidad * dc.costo_unitario) as gasto_total
            FROM detalle_compra dc
            JOIN productos p ON dc.producto_id = p.id
            JOIN compras c ON dc.compra_id = c.id
            WHERE date(c.created_at, 'localtime') BETWEEN date('{desde}') AND date('{hasta}')
              AND c.estado = 'active'
            GROUP BY p.id
            ORDER BY unidades_compradas DESC
            LIMIT 20
        """).fetchall()
        
        prods_data = []
        for r in rows_prods:
            d = dict(r)
            costo_prom = d["gasto_total"] / d["unidades_compradas"] if d["unidades_compradas"] > 0 else 0
            d["costo_promedio"] = round(costo_prom, 2)
            if costo_prom > 0:
                d["variacion_costo_pct"] = round(((d["costo_actual"] - costo_prom) / costo_prom * 100), 1)
            else:
                d["variacion_costo_pct"] = None
            prods_data.append(d)

        # 4. Frecuencia y Detalle por Proveedor
        rows_freq = conn.execute(f"""
            SELECT 
                COALESCE(proveedor, 'Sin nombre') as nombre,
                id,
                total,
                created_at
            FROM compras
            WHERE date(created_at, 'localtime') BETWEEN date('{desde}') AND date('{hasta}')
              AND estado = 'active'
            ORDER BY created_at DESC
        """).fetchall()
        
        freq_map = {}
        for r in rows_freq:
            prov = r["nombre"]
            if prov not in freq_map:
                freq_map[prov] = []
            freq_map[prov].append({"id": r["id"], "fecha": r["created_at"][:10], "total": r["total"]})

        frecuencia = [{"proveedor": k, "compras": v} for k, v in freq_map.items()]

        return {
            "periodo": {"desde": desde, "hasta": hasta},
            "resumen": dict(res_global),
            "por_proveedor": [dict(r) for r in rows_prov],
            "productos_mas_comprados": prods_data,
            "frecuencia_por_proveedor": frecuencia
        }

@router.get("/api/reportes/productos")
def reporte_productos(
    categoria: Optional[str] = None,
    estado: str = "activos",
    con_stock_bajo: bool = False
):
    query = "SELECT * FROM productos WHERE 1=1"
    params = []

    if estado == "activos":
        query += " AND activo = 1"
    elif estado == "inactivos":
        query += " AND activo = 0"
    
    if categoria:
        query += " AND categoria = ?"
        params.append(categoria)
    
    if con_stock_bajo:
        query += " AND stock <= stock_minimo"

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        resultado = []
        for r in rows:
            d = dict(r)
            costo_envio = d.get("costo_envio", 0)
            costo_real = d["costo"] + costo_envio
            ganancia = d["precio"] - costo_real
            margen_pct = round((ganancia / d["precio"] * 100), 1) if d["precio"] > 0 else 0
            
            estado_stock = "ok"
            if d["stock"] == 0: estado_stock = "agotado"
            elif d["stock"] <= d["stock_minimo"]: estado_stock = "bajo"
            
            num_vars = 0
            if d["tiene_variantes"]:
                num_vars = conn.execute(
                    "SELECT COUNT(*) FROM variantes WHERE producto_id = ? AND activo = 1",
                    (d["id"],)
                ).fetchone()[0]
            
            resultado.append({
                "id": d["id"],
                "nombre": d["nombre"],
                "categoria": d["categoria"],
                "precio": d["precio"],
                "costo": d["costo"],
                "costo_envio": costo_envio,
                "costo_real": costo_real,
                "ganancia": ganancia,
                "margen_pct": margen_pct,
                "stock": d["stock"],
                "stock_minimo": d["stock_minimo"],
                "stock_estado": estado_stock,
                "codigo_proveedor": d["codigo_proveedor"],
                "tiene_variantes": bool(d["tiene_variantes"]),
                "num_variantes": num_vars,
                "activo": bool(d["activo"]),
                "created_at": d["created_at"]
            })
        
        return resultado

@router.get("/api/reportes/productos/{producto_id}/variantes")
def reporte_producto_variantes(producto_id: int):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM variantes WHERE producto_id = ? AND activo = 1",
            (producto_id,)
        ).fetchall()
        return [dict(r) for r in rows]
