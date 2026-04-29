from fastapi import APIRouter, HTTPException
from database import get_db
from schemas.schemas import VentaCrear, VentaCorreccion
from services.logic import (
    _crear_venta_en_transaccion, _to_iso_dt, _validar_operable_para_correccion,
    _validar_operable_para_cancelacion, _aplicar_delta_stock,
    _validar_consistencia_stock_producto
)
from audit_service import snapshot_sale, log_transaction

router = APIRouter(tags=["Ventas"])

@router.post("/api/ventas", status_code=201)
def registrar_venta(venta: VentaCrear):
    with get_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        return _crear_venta_en_transaccion(conn, venta)

@router.get("/api/ventas")
def historial_ventas(limite: int = 50):
    limite = max(1, min(limite, 200))
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
            venta = dict(v)
            venta["created_at"] = _to_iso_dt(venta.get("created_at"))
            resultado.append({**venta, "items": [dict(d) for d in detalles]})
        return resultado

@router.put("/api/ventas/{venta_id}/correccion")
def corregir_venta(venta_id: int, datos: VentaCorreccion):
    with get_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        venta = conn.execute("SELECT * FROM ventas WHERE id=?", (venta_id,)).fetchone()
        if not venta:
            raise HTTPException(404, f"Venta {venta_id} no encontrada")
        _validar_operable_para_correccion(venta, "venta")

        previa = snapshot_sale(conn, venta_id)
        for item in previa["items"]:
            _aplicar_delta_stock(conn, item["producto_id"], item.get("variante_id"), item["cantidad"])
            _validar_consistencia_stock_producto(conn, item["producto_id"])

        conn.execute("UPDATE ventas SET estado='cancelled' WHERE id=?", (venta_id,))
        nueva = snapshot_sale(conn, venta_id)
        log_transaction(conn, "sale", venta_id, "cancel", previous_data=previa, new_data=nueva)

        nueva_venta = _crear_venta_en_transaccion(conn, VentaCrear(items=datos.items, metodo_pago=datos.metodo_pago), corrected_from_id=venta_id)
        conn.execute("UPDATE ventas SET corrected_by_id=? WHERE id=?", (nueva_venta["venta_id"], venta_id))
        log_transaction(
            conn,
            "sale",
            venta_id,
            "link_correction",
            previous_data={"corrected_by_id": None, "original_id": venta_id},
            new_data={"corrected_by_id": nueva_venta["venta_id"], "corrected_id": nueva_venta["venta_id"]},
        )
        return {"original_sale_id": venta_id, "corrected_sale_id": nueva_venta["venta_id"]}

@router.post("/api/ventas/{venta_id}/cancelar")
def cancelar_venta(venta_id: int):
    with get_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        venta = conn.execute("SELECT * FROM ventas WHERE id=?", (venta_id,)).fetchone()
        if not venta:
            raise HTTPException(404, f"Venta {venta_id} no encontrada")
        _validar_operable_para_cancelacion(venta, "venta")

        previa = snapshot_sale(conn, venta_id)
        for item in previa["items"]:
            _aplicar_delta_stock(conn, item["producto_id"], item.get("variante_id"), item["cantidad"])
            _validar_consistencia_stock_producto(conn, item["producto_id"])

        conn.execute("UPDATE ventas SET estado='cancelled' WHERE id=?", (venta_id,))
        nueva = snapshot_sale(conn, venta_id)
        log_transaction(conn, "sale", venta_id, "cancel", previous_data=previa, new_data=nueva)
        return {"venta_id": venta_id, "estado": "cancelled"}
