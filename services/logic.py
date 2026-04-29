from typing import Optional
from fastapi import HTTPException
from database import get_db
from audit_service import log_transaction, snapshot_sale, snapshot_purchase
from schemas.schemas import VentaCrear, CompraCrear
from services.inventory import registrar_movimiento, obtener_stock_actual

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
    if row["corrected_from_id"] is not None:
        raise HTTPException(409, f"La {etiqueta} {row['id']} es una correccion y no puede corregirse de nuevo")

def _crear_venta_en_transaccion(conn, venta: VentaCrear, corrected_from_id: Optional[int] = None):
    items_validados = []
    subtotal_bruto = 0.0
    productos_tocados = set()
    movement_items = []

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

        desc_item = getattr(item, 'descuento_item', 0) or 0
        subtotal = (p["precio"] * item.cantidad) - desc_item
        subtotal_bruto += p["precio"] * item.cantidad
        productos_tocados.add(item.producto_id)

        # Capturar stock antes del cambio
        stock_antes = obtener_stock_actual(conn, item.producto_id, item.variante_id)

        items_validados.append({
            "producto_id": item.producto_id,
            "variante_id": item.variante_id,
            "nombre": p["nombre"],
            "cantidad": item.cantidad,
            "precio_unitario": p["precio"],
            "subtotal": subtotal,
            "descuento_item": desc_item,
            "tiene_variantes": bool(p["tiene_variantes"]),
            "stock_antes": stock_antes,
        })

    # Calcular descuentos globales
    desc_pct = getattr(venta, 'descuento_pct', 0) or 0
    desc_monto = getattr(venta, 'descuento_monto', 0) or 0
    total_items_desc = sum(i["descuento_item"] for i in items_validados)
    subtotal_neto = subtotal_bruto - total_items_desc
    descuento_global = desc_monto + (subtotal_neto * desc_pct / 100)
    total = max(0, subtotal_neto - descuento_global)

    cursor = conn.execute(
        """INSERT INTO ventas (subtotal, total, descuento_pct, descuento_monto,
           metodo_pago, estado, corrected_from_id, corrected_by_id)
           VALUES (?,?,?,?,?,?,?,NULL)""",
        (subtotal_bruto, total, desc_pct, desc_monto, venta.metodo_pago, "active", corrected_from_id),
    )
    venta_id = cursor.lastrowid

    for item in items_validados:
        conn.execute(
            """INSERT INTO detalle_venta
               (venta_id, producto_id, variante_id, cantidad, precio_unitario, subtotal, descuento_item)
               VALUES (?,?,?,?,?,?,?)""",
            (venta_id, item["producto_id"], item["variante_id"], item["cantidad"],
             item["precio_unitario"], item["subtotal"], item["descuento_item"]),
        )
        _aplicar_delta_stock(conn, item["producto_id"], item["variante_id"], -item["cantidad"])
        _validar_consistencia_stock_producto(conn, item["producto_id"])

        stock_despues = obtener_stock_actual(conn, item["producto_id"], item["variante_id"])
        movement_items.append({
            "producto_id": item["producto_id"],
            "variante_id": item["variante_id"],
            "cantidad": -item["cantidad"],
            "stock_antes": item["stock_antes"],
            "stock_despues": stock_despues,
        })

    # Registrar movimiento de inventario
    registrar_movimiento(
        conn, "venta", f"Venta #{venta_id}", movement_items,
        referencia=f"venta:{venta_id}",
    )

    log_transaction(conn, "sale", venta_id, "create", previous_data=None, new_data=snapshot_sale(conn, venta_id))
    return {"venta_id": venta_id, "subtotal": subtotal_bruto, "total": total,
            "descuento_pct": desc_pct, "descuento_monto": desc_monto,
            "metodo_pago": venta.metodo_pago, "items": items_validados}

def _crear_compra_en_transaccion(conn, compra: CompraCrear, corrected_from_id: Optional[int] = None):
    items_validados = []
    subtotal = 0.0
    movement_items = []

    for item in compra.items:
        p = conn.execute("SELECT * FROM productos WHERE id=? AND activo=1", (item.producto_id,)).fetchone()
        if not p:
            raise HTTPException(404, f"Producto {item.producto_id} no encontrado")

        if p["tiene_variantes"]:
            if not item.variante_id:
                raise HTTPException(400, f"Producto '{p['nombre']}' tiene variantes, requiere variante_id")
        elif item.variante_id:
            raise HTTPException(400, f"Producto '{p['nombre']}' no tiene variantes, pero se envió variante_id")

        if item.variante_id:
            v = conn.execute(
                "SELECT * FROM variantes WHERE id=? AND producto_id=? AND activo=1",
                (item.variante_id, item.producto_id),
            ).fetchone()
            if not v:
                raise HTTPException(404, f"Variante {item.variante_id} no encontrada")

        stock_antes = obtener_stock_actual(conn, item.producto_id, item.variante_id)

        sub = item.costo_unitario * item.cantidad
        subtotal += sub
        items_validados.append({
            "producto_id": item.producto_id,
            "variante_id": item.variante_id,
            "cantidad": item.cantidad,
            "costo_unitario": item.costo_unitario,
            "subtotal": sub,
            "stock_antes": stock_antes,
        })

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

        stock_despues = obtener_stock_actual(conn, item["producto_id"], item["variante_id"])
        movement_items.append({
            "producto_id": item["producto_id"],
            "variante_id": item["variante_id"],
            "cantidad": item["cantidad"],
            "stock_antes": item["stock_antes"],
            "stock_despues": stock_despues,
        })

    # Registrar movimiento de inventario
    registrar_movimiento(
        conn, "compra", f"Compra #{compra_id} — {compra.proveedor}", movement_items,
        referencia=f"compra:{compra_id}",
    )

    log_transaction(conn, "purchase", compra_id, "create", previous_data=None, new_data=snapshot_purchase(conn, compra_id))
    return {
        "compra_id": compra_id,
        "proveedor": compra.proveedor,
        "subtotal": subtotal,
        "costo_envio": compra.costo_envio,
        "total": total,
        "items": items_validados,
    }
