import json


def _to_iso_dt(value):
    if not value:
        return value
    return value.replace(" ", "T", 1) if " " in value else value


def _to_json_blob(value):
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=True)


def log_transaction(conn, entity_type: str, entity_id: int, action: str, previous_data=None, new_data=None):
    conn.execute(
        """INSERT INTO transaction_logs
           (entity_type, entity_id, action, previous_data, new_data)
           VALUES (?,?,?,?,?)""",
        (entity_type, entity_id, action, _to_json_blob(previous_data), _to_json_blob(new_data)),
    )


def snapshot_sale(conn, sale_id: int):
    sale = conn.execute("SELECT * FROM ventas WHERE id=?", (sale_id,)).fetchone()
    if not sale:
        return None
    details = conn.execute(
        "SELECT producto_id, variante_id, cantidad, precio_unitario, subtotal FROM detalle_venta WHERE venta_id=? ORDER BY id",
        (sale_id,),
    ).fetchall()
    data = dict(sale)
    data["created_at"] = _to_iso_dt(data.get("created_at"))
    data["items"] = [dict(d) for d in details]
    return data


def snapshot_purchase(conn, purchase_id: int):
    purchase = conn.execute("SELECT * FROM compras WHERE id=?", (purchase_id,)).fetchone()
    if not purchase:
        return None
    details = conn.execute(
        "SELECT producto_id, variante_id, cantidad, costo_unitario, subtotal FROM detalle_compra WHERE compra_id=? ORDER BY id",
        (purchase_id,),
    ).fetchall()
    data = dict(purchase)
    data["created_at"] = _to_iso_dt(data.get("created_at"))
    data["items"] = [dict(d) for d in details]
    return data


def list_logs(conn, entity_type=None, entity_id=None, limit=100):
    query = "SELECT * FROM transaction_logs WHERE 1=1"
    params = []
    if entity_type:
        query += " AND entity_type=?"
        params.append(entity_type)
    if entity_id is not None:
        query += " AND entity_id=?"
        params.append(entity_id)
    query += " ORDER BY timestamp DESC, id DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()

    out = []
    for row in rows:
        item = dict(row)
        item["previous_data"] = json.loads(item["previous_data"]) if item["previous_data"] else None
        item["new_data"] = json.loads(item["new_data"]) if item["new_data"] else None
        item["timestamp"] = _to_iso_dt(item.get("timestamp"))
        out.append(item)
    return out
