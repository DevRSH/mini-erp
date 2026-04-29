"""
services/inventory.py — Lógica de movimientos de inventario
Toda operación de stock queda documentada con trazabilidad completa.
"""

from typing import Optional, List
from logger import log


def registrar_movimiento(conn, tipo: str, motivo: str, items: list,
                         referencia: Optional[str] = None):
    """
    Registra un movimiento de inventario con sus items.
    
    Args:
        conn: conexión SQLite (dentro de transacción)
        tipo: 'venta', 'compra', 'ajuste', 'merma', 'cancelacion'
        motivo: descripción del movimiento
        items: lista de dicts con {producto_id, variante_id, cantidad, stock_antes, stock_despues}
        referencia: ej "venta:123", "compra:45"
    
    Returns:
        ID del movimiento creado
    """
    cursor = conn.execute(
        """INSERT INTO inventory_movements (tipo, referencia, motivo)
           VALUES (?, ?, ?)""",
        (tipo, referencia, motivo),
    )
    movimiento_id = cursor.lastrowid

    for item in items:
        conn.execute(
            """INSERT INTO inventory_movement_items
               (movimiento_id, producto_id, variante_id, cantidad, stock_antes, stock_despues)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                movimiento_id,
                item["producto_id"],
                item.get("variante_id"),
                item["cantidad"],
                item["stock_antes"],
                item["stock_despues"],
            ),
        )

    log.info(
        "Movimiento #%d [%s] — %s — %d items — ref: %s",
        movimiento_id, tipo, motivo, len(items), referencia or "n/a",
    )
    return movimiento_id


def obtener_stock_actual(conn, producto_id: int, variante_id: Optional[int] = None) -> int:
    """Obtiene el stock actual de un producto o variante."""
    if variante_id:
        row = conn.execute(
            "SELECT stock FROM variantes WHERE id=? AND producto_id=? AND activo=1",
            (variante_id, producto_id),
        ).fetchone()
        return row["stock"] if row else 0
    else:
        row = conn.execute(
            "SELECT stock FROM productos WHERE id=? AND activo=1",
            (producto_id,),
        ).fetchone()
        return row["stock"] if row else 0


def comparar_conteo_fisico(conn, conteo: list) -> dict:
    """
    Compara cantidades físicas contra stock del sistema.
    
    Args:
        conteo: lista de {producto_id, variante_id?, cantidad_fisica}
    
    Returns:
        {items: [{producto_id, variante_id, nombre, stock_sistema, cantidad_fisica, diferencia}],
         total_diferencias: int, total_items: int}
    """
    resultado = []
    total_diffs = 0

    for item in conteo:
        pid = item["producto_id"]
        vid = item.get("variante_id")

        p = conn.execute(
            "SELECT id, nombre, stock, tiene_variantes FROM productos WHERE id=? AND activo=1",
            (pid,),
        ).fetchone()
        if not p:
            continue

        if vid:
            v = conn.execute(
                "SELECT id, stock, attr1_valor, attr2_valor FROM variantes WHERE id=? AND producto_id=? AND activo=1",
                (vid, pid),
            ).fetchone()
            if not v:
                continue
            stock_sistema = v["stock"]
            nombre = f"{p['nombre']} ({v['attr1_valor']}{' / ' + v['attr2_valor'] if v['attr2_valor'] else ''})"
        else:
            stock_sistema = p["stock"]
            nombre = p["nombre"]

        diferencia = item["cantidad_fisica"] - stock_sistema
        if diferencia != 0:
            total_diffs += 1

        resultado.append({
            "producto_id": pid,
            "variante_id": vid,
            "nombre": nombre,
            "stock_sistema": stock_sistema,
            "cantidad_fisica": item["cantidad_fisica"],
            "diferencia": diferencia,
        })

    return {
        "items": resultado,
        "total_diferencias": total_diffs,
        "total_items": len(resultado),
    }


def confirmar_conteo_fisico(conn, conteo: list, motivo: str = "Toma de inventario físico") -> dict:
    """
    Aplica las diferencias del conteo físico al stock y genera movimiento.
    Solo ajusta los items con diferencia != 0.
    """
    from services.logic import _validar_consistencia_stock_producto

    comparacion = comparar_conteo_fisico(conn, conteo)
    items_ajustados = []
    movement_items = []

    for item in comparacion["items"]:
        diff = item["diferencia"]
        if diff == 0:
            continue

        pid = item["producto_id"]
        vid = item["variante_id"]
        stock_antes = item["stock_sistema"]
        stock_despues = item["cantidad_fisica"]

        # Aplicar el ajuste directamente
        if vid:
            conn.execute(
                "UPDATE variantes SET stock=? WHERE id=? AND producto_id=?",
                (stock_despues, vid, pid),
            )
            # Recalcular total del producto
            total_var = conn.execute(
                "SELECT COALESCE(SUM(stock),0) as t FROM variantes WHERE producto_id=? AND activo=1",
                (pid,),
            ).fetchone()["t"]
            conn.execute("UPDATE productos SET stock=? WHERE id=?", (total_var, pid))
        else:
            conn.execute(
                "UPDATE productos SET stock=? WHERE id=?",
                (stock_despues, pid),
            )

        _validar_consistencia_stock_producto(conn, pid)

        items_ajustados.append(item)
        movement_items.append({
            "producto_id": pid,
            "variante_id": vid,
            "cantidad": diff,
            "stock_antes": stock_antes,
            "stock_despues": stock_despues,
        })

    movimiento_id = None
    if movement_items:
        movimiento_id = registrar_movimiento(
            conn, "ajuste", motivo, movement_items, referencia="conteo_fisico"
        )

    return {
        "movimiento_id": movimiento_id,
        "items_ajustados": len(items_ajustados),
        "items": items_ajustados,
    }

def registrar_merma(conn, items: list, motivo: str) -> dict:
    """
    Registra pérdida de stock por merma.
    
    Args:
        items: lista de {producto_id, variante_id?, cantidad}
        motivo: descripción de la merma
    """
    from services.logic import _validar_consistencia_stock_producto
    
    movement_items = []
    
    for item in items:
        pid = item["producto_id"]
        vid = item.get("variante_id")
        cantidad = item["cantidad"]
        
        stock_antes = obtener_stock_actual(conn, pid, vid)
        if stock_antes < cantidad:
             # Si no hay suficiente stock, limitamos la merma al stock actual
             # para evitar stock negativo, o lanzamos error? 
             # Decisión: dejar stock negativo si es necesario (merma forzada), 
             # o limitar? Limitemos a 0 para consistencia básica.
             cantidad = stock_antes
        
        stock_despues = stock_antes - cantidad
        
        if vid:
            conn.execute(
                "UPDATE variantes SET stock=? WHERE id=? AND producto_id=?",
                (stock_despues, vid, pid)
            )
            total_var = conn.execute(
                "SELECT COALESCE(SUM(stock),0) as t FROM variantes WHERE producto_id=? AND activo=1",
                (pid,)
            ).fetchone()["t"]
            conn.execute("UPDATE productos SET stock=? WHERE id=?", (total_var, pid))
        else:
            conn.execute("UPDATE productos SET stock=? WHERE id=?", (stock_despues, pid))
            
        _validar_consistencia_stock_producto(conn, pid)
        
        movement_items.append({
            "producto_id": pid,
            "variante_id": vid,
            "cantidad": -cantidad, # Es una salida
            "stock_antes": stock_antes,
            "stock_despues": stock_despues
        })
        
    movimiento_id = registrar_movimiento(
        conn, "merma", motivo, movement_items, referencia="merma"
    )
    
    return {"movimiento_id": movimiento_id, "items": len(movement_items)}

