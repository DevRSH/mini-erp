from fastapi import APIRouter, HTTPException
from database import get_db
from schemas.schemas import CompraCrear, CompraCorreccion
from services.logic import (
    _crear_compra_en_transaccion, _to_iso_dt, _validar_operable_para_correccion,
    _validar_operable_para_cancelacion, _aplicar_delta_stock,
    _validar_consistencia_stock_producto
)
from audit_service import snapshot_purchase, log_transaction

router = APIRouter(tags=["Compras"])

@router.post("/api/compras", status_code=201)
def registrar_compra(compra: CompraCrear):
    with get_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        return _crear_compra_en_transaccion(conn, compra)

@router.get("/api/compras")
def historial_compras(limite: int = 50):
    limite = max(1, min(limite, 200))
    with get_db() as conn:
        compras = conn.execute(
            """SELECT c.*, p.nombre as proveedor_nombre
               FROM compras c
               LEFT JOIN proveedores p ON c.proveedor_id = p.id
               ORDER BY c.created_at DESC LIMIT ?""", (limite,)
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

@router.get("/api/compras/{id}")
def detalle_compra(id: int):
    with get_db() as conn:
        c = conn.execute(
            """SELECT c.*, p.nombre as proveedor_nombre
               FROM compras c
               LEFT JOIN proveedores p ON c.proveedor_id = p.id
               WHERE c.id=?""", (id,)
        ).fetchone()
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

@router.put("/api/compras/{compra_id}/correccion")
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
                proveedor_id=datos.proveedor_id,
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

@router.post("/api/compras/{compra_id}/cancelar")
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
