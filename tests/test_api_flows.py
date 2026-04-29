from pathlib import Path
import sys
import inspect
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import HTTPException
import pytest

import database
import main
import dependencies
from routers import auth, products, sales, purchases, reports
from schemas import schemas


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    db_path = tmp_path / "erp_test.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    database.DB_PATH = str(db_path)
    database.init_db()
    database.init_compras()
    database.init_inventory()
    database.init_proveedores()
    yield


def fake_request(headers=None, cookies=None):
    return SimpleNamespace(headers=headers or {}, cookies=cookies or {}, client=SimpleNamespace(host="127.0.0.1"))


def crear_producto(nombre, precio=1000, stock=0, tiene_variantes=False, stock_minimo=5):
    return products.crear_producto(
        schemas.ProductoCrear(
            nombre=nombre,
            precio=precio,
            costo=400,
            costo_envio=10,
            stock=stock,
            stock_minimo=stock_minimo,
            categoria="Test",
            codigo_proveedor="",
            tiene_variantes=tiene_variantes,
        )
    )


def crear_variante(producto_id, attr1_valor, stock, stock_minimo=2):
    return products.crear_variante(
        producto_id,
        schemas.VarianteCrear(
            attr1_nombre="Color",
            attr1_valor=attr1_valor,
            attr2_nombre=None,
            attr2_valor=None,
            stock=stock,
            stock_minimo=stock_minimo,
            codigo_barras="",
        ),
    )


def test_crear_variante_resincroniza_stock_producto():
    p = crear_producto("Polera", stock=0, tiene_variantes=True)
    crear_variante(p["id"], "Rojo", stock=7)

    inventario = products.listar_productos()
    producto = next(x for x in inventario if x["id"] == p["id"])
    assert producto["stock"] == 7


def test_compra_con_variantes_exige_variante_id():
    p = crear_producto("Zapato", stock=0, tiene_variantes=True)
    crear_variante(p["id"], "42", stock=3)

    with pytest.raises(HTTPException) as err:
        purchases.registrar_compra(
            schemas.CompraCrear(
                proveedor="Proveedor X",
                notas="",
                costo_envio=0,
                actualizar_costo=True,
                items=[
                    schemas.ItemCompra(
                        producto_id=p["id"],
                        variante_id=None,
                        cantidad=2,
                        costo_unitario=500,
                    )
                ],
            )
        )
    assert err.value.status_code == 400
    assert "tiene variantes" in err.value.detail


def test_compra_con_variante_resincroniza_producto():
    p = crear_producto("Pantalon", stock=0, tiene_variantes=True)
    v = crear_variante(p["id"], "Negro", stock=2)

    compra = purchases.registrar_compra(
        schemas.CompraCrear(
            proveedor="Proveedor Y",
            notas="",
            costo_envio=0,
            actualizar_costo=True,
            items=[
                schemas.ItemCompra(
                    producto_id=p["id"],
                    variante_id=v["id"],
                    cantidad=3,
                    costo_unitario=700,
                )
            ],
        )
    )
    assert compra["compra_id"] > 0

    variantes = products.listar_variantes(p["id"])["variantes"]
    variante = next(x for x in variantes if x["id"] == v["id"])
    assert variante["stock"] == 5

    inventario = products.listar_productos()
    producto = next(x for x in inventario if x["id"] == p["id"])
    assert producto["stock"] == 5


def test_compra_producto_sin_variantes_funciona():
    p = crear_producto("Cuaderno base", stock=1, tiene_variantes=False)
    compra = purchases.registrar_compra(
        schemas.CompraCrear(
            proveedor="Proveedor base",
            notas="",
            costo_envio=0,
            actualizar_costo=True,
            items=[
                schemas.ItemCompra(
                    producto_id=p["id"],
                    variante_id=None,
                    cantidad=4,
                    costo_unitario=150,
                )
            ],
        )
    )
    assert compra["compra_id"] > 0
    inventario = products.listar_productos()
    producto = next(x for x in inventario if x["id"] == p["id"])
    assert producto["stock"] == 5


def test_endpoint_alias_variantes_en_ingles():
    p = crear_producto("Poleron alias", stock=0, tiene_variantes=True)
    v = crear_variante(p["id"], "M", stock=2)
    out = products.listar_variantes(p["id"])
    assert out["producto"] == "Poleron alias"
    assert any(item["id"] == v["id"] for item in out["variantes"])


def test_desactivar_ultima_variante_desactiva_modo_variantes():
    p = crear_producto("Gorro", stock=0, tiene_variantes=True)
    v = crear_variante(p["id"], "Azul", stock=4)

    res = products.desactivar_variante(v["id"])
    assert res["variantes_activas"] == 0

    inventario = products.listar_productos()
    producto = next(x for x in inventario if x["id"] == p["id"])
    assert producto["tiene_variantes"] == 0
    assert producto["stock"] == 0


def test_mas_vendidos_respeta_periodo():
    p = crear_producto("Botella", stock=20, tiene_variantes=False)

    venta_vieja = sales.registrar_venta(
        schemas.VentaCrear(
            metodo_pago="efectivo",
            items=[schemas.ItemVenta(producto_id=p["id"], cantidad=1, variante_id=None)],
        )
    )
    with database.get_db() as conn:
        conn.execute(
            "UPDATE ventas SET created_at='2000-01-01 10:00:00' WHERE id=?",
            (venta_vieja["venta_id"],),
        )

    sales.registrar_venta(
        schemas.VentaCrear(
            metodo_pago="efectivo",
            items=[schemas.ItemVenta(producto_id=p["id"], cantidad=2, variante_id=None)],
        )
    )

    top = reports.mas_vendidos(limite=5, periodo="mes")
    assert top[0]["total_vendido"] == 2


def test_stock_bajo_incluye_variantes_criticas():
    p = crear_producto("Poleron", stock=0, tiene_variantes=True, stock_minimo=5)
    crear_variante(p["id"], "S", stock=1, stock_minimo=2)
    crear_variante(p["id"], "M", stock=10, stock_minimo=2)

    alertas = reports.stock_bajo()
    producto = next(x for x in alertas if x["id"] == p["id"])
    assert producto["stock"] == 11
    assert len(producto["variantes_bajas"]) == 1


def test_historiales_devuelven_created_at_iso():
    p = crear_producto("Taza", stock=10, tiene_variantes=False)

    purchases.registrar_compra(
        schemas.CompraCrear(
            proveedor="Proveedor Z",
            notas="",
            costo_envio=0,
            actualizar_costo=True,
            items=[
                schemas.ItemCompra(
                    producto_id=p["id"],
                    variante_id=None,
                    cantidad=1,
                    costo_unitario=300,
                )
            ],
        )
    )
    compras = purchases.historial_compras()
    assert "T" in compras[0]["created_at"]

    sales.registrar_venta(
        schemas.VentaCrear(
            metodo_pago="efectivo",
            items=[schemas.ItemVenta(producto_id=p["id"], cantidad=1, variante_id=None)],
        )
    )
    ventas = sales.historial_ventas()
    assert "T" in ventas[0]["created_at"]


def test_api_sesion_sin_cookie_devuelve_autenticado_false():
    respuesta = auth.verificar_sesion(fake_request())
    assert respuesta == {"autenticado": False}


def test_backup_acepta_header_x_backup_key(monkeypatch):
    monkeypatch.setattr(main, "BACKUP_KEY", "clave-segura")
    ok = main.descargar_backup(fake_request(headers={"X-Backup-Key": "clave-segura"}))
    assert "backup_erp_" in ok.filename

    with pytest.raises(HTTPException) as err:
        main.descargar_backup(fake_request(headers={"X-Backup-Key": "incorrecta"}))
    assert err.value.status_code == 403


def test_backup_query_param_sigue_funcionando_si_endpoint_lo_mantiene(monkeypatch):
    firma = inspect.signature(main.descargar_backup)
    if "clave" not in firma.parameters:
        pytest.skip("El endpoint ya no expone compatibilidad por query param 'clave'.")

    monkeypatch.setattr(main, "BACKUP_KEY", "clave-segura")
    respuesta = main.descargar_backup(fake_request(), clave="clave-segura")
    assert "backup_erp_" in respuesta.filename


@pytest.mark.parametrize(
    "ruta",
    ["/api/ventas", "/api/compras", "/api/reportes/mas-vendidos"],
)
def test_limite_positivo_restringe_resultados(ruta):
    p = crear_producto("Producto limite", stock=20, tiene_variantes=False)
    sales.registrar_venta(
        schemas.VentaCrear(
            metodo_pago="efectivo",
            items=[schemas.ItemVenta(producto_id=p["id"], cantidad=1, variante_id=None)],
        )
    )
    purchases.registrar_compra(
        schemas.CompraCrear(
            proveedor="Proveedor limite",
            notas="",
            costo_envio=0,
            actualizar_costo=True,
            items=[
                schemas.ItemCompra(
                    producto_id=p["id"],
                    variante_id=None,
                    cantidad=1,
                    costo_unitario=100,
                )
            ],
        )
    )
    if ruta == "/api/ventas":
        respuesta = sales.historial_ventas(limite=1)
    elif ruta == "/api/compras":
        respuesta = purchases.historial_compras(limite=1)
    else:
        respuesta = reports.mas_vendidos(limite=1)
    assert len(respuesta) <= 1


@pytest.mark.parametrize(
    "ruta",
    [
        "/api/ventas",
        "/api/compras",
        "/api/reportes/mas-vendidos",
    ],
)
def test_limite_invalido_se_normaliza_sin_romper(ruta):
    p = crear_producto("Producto limite invalido", stock=20, tiene_variantes=False)
    sales.registrar_venta(
        schemas.VentaCrear(
            metodo_pago="efectivo",
            items=[schemas.ItemVenta(producto_id=p["id"], cantidad=1, variante_id=None)],
        )
    )
    purchases.registrar_compra(
        schemas.CompraCrear(
            proveedor="Proveedor limite invalido",
            notas="",
            costo_envio=0,
            actualizar_costo=True,
            items=[
                schemas.ItemCompra(
                    producto_id=p["id"],
                    variante_id=None,
                    cantidad=1,
                    costo_unitario=100,
                )
            ],
        )
    )
    if ruta == "/api/ventas":
        respuesta = sales.historial_ventas(limite=-1)
        assert len(respuesta) >= 1
    elif ruta == "/api/compras":
        respuesta = purchases.historial_compras(limite=-1)
        assert len(respuesta) >= 1
    else:
        respuesta = reports.mas_vendidos(limite=-1)
        assert len(respuesta) >= 1


def test_cookie_secure_condicionada_por_flag_si_es_viable(monkeypatch):
    monkeypatch.setattr(auth, "APP_PIN", "1234")
    monkeypatch.setattr(auth, "COOKIE_HTTPONLY", True)
    monkeypatch.setattr(auth, "COOKIE_SAMESITE", "lax")
    monkeypatch.setattr(auth, "COOKIE_SECURE", True)

    class ResponseDummy:
        def __init__(self):
            self.cookies = None

        def set_cookie(self, **kwargs):
            self.cookies = kwargs

    response = ResponseDummy()
    out = auth.login(schemas.LoginRequest(pin="1234"), response, fake_request())
    assert out["mensaje"] == "Acceso concedido"
    assert response.cookies is not None
    assert response.cookies["secure"] is True
    assert response.cookies["httponly"] is True


def _logs(entity_type=None, entity_id=None):
    return main.historial_logs(entity_type=entity_type, entity_id=entity_id, limite=50)


def test_log_creacion_compra():
    p = crear_producto("Cuaderno", stock=5, tiene_variantes=False)
    compra = purchases.registrar_compra(
        schemas.CompraCrear(
            proveedor="Prov log",
            notas="entrada",
            costo_envio=20,
            actualizar_costo=True,
            items=[schemas.ItemCompra(producto_id=p["id"], cantidad=3, costo_unitario=200, variante_id=None)],
        )
    )
    logs = _logs("purchase", compra["compra_id"])
    assert len(logs) == 1
    assert logs[0]["action"] == "create"
    assert logs[0]["previous_data"] is None
    assert logs[0]["new_data"]["id"] == compra["compra_id"]


def test_log_creacion_venta():
    p = crear_producto("Lapiz", stock=12, tiene_variantes=False)
    venta = sales.registrar_venta(
        schemas.VentaCrear(
            metodo_pago="efectivo",
            items=[schemas.ItemVenta(producto_id=p["id"], cantidad=2, variante_id=None)],
        )
    )
    logs = _logs("sale", venta["venta_id"])
    assert len(logs) == 1
    assert logs[0]["action"] == "create"
    assert logs[0]["new_data"]["id"] == venta["venta_id"]


def test_correccion_compra_ajusta_stock_y_log():
    p = crear_producto("Resma", stock=2, tiene_variantes=False)
    compra = purchases.registrar_compra(
        schemas.CompraCrear(
            proveedor="Prov A",
            notas="n1",
            costo_envio=0,
            actualizar_costo=True,
            items=[schemas.ItemCompra(producto_id=p["id"], cantidad=5, costo_unitario=100, variante_id=None)],
        )
    )
    salida = purchases.corregir_compra(
        compra["compra_id"],
        schemas.CompraCorreccion(
            proveedor="Prov A",
            notas="corregida",
            costo_envio=0,
            actualizar_costo=True,
            items=[schemas.ItemCompra(producto_id=p["id"], cantidad=3, costo_unitario=90, variante_id=None)],
        ),
    )
    assert salida["original_purchase_id"] == compra["compra_id"]
    assert salida["corrected_purchase_id"] > compra["compra_id"]
    inventario = products.listar_productos()
    producto = next(x for x in inventario if x["id"] == p["id"])
    assert producto["stock"] == 5
    with database.get_db() as conn:
        original = conn.execute("SELECT estado, corrected_by_id FROM compras WHERE id=?", (compra["compra_id"],)).fetchone()
        corrected = conn.execute(
            "SELECT estado, corrected_from_id, total FROM compras WHERE id=?",
            (salida["corrected_purchase_id"],),
        ).fetchone()
    assert original["estado"] == "cancelled"
    assert original["corrected_by_id"] == salida["corrected_purchase_id"]
    assert corrected["estado"] == "active"
    assert corrected["corrected_from_id"] == compra["compra_id"]
    assert corrected["total"] == 270
    logs = _logs("purchase", compra["compra_id"])
    assert [x["action"] for x in logs] == ["link_correction", "cancel", "create"]


def test_correccion_venta_no_duplica_y_bloquea_reintento():
    p = crear_producto("Resaltador", stock=10, tiene_variantes=False)
    venta = sales.registrar_venta(
        schemas.VentaCrear(
            metodo_pago="efectivo",
            items=[schemas.ItemVenta(producto_id=p["id"], cantidad=2, variante_id=None)],
        )
    )
    out = sales.corregir_venta(
        venta["venta_id"],
        schemas.VentaCorreccion(
            metodo_pago="tarjeta",
            items=[schemas.ItemVenta(producto_id=p["id"], cantidad=3, variante_id=None)],
        ),
    )
    with pytest.raises(HTTPException) as err:
        sales.corregir_venta(
            venta["venta_id"],
            schemas.VentaCorreccion(
                metodo_pago="efectivo",
                items=[schemas.ItemVenta(producto_id=p["id"], cantidad=1, variante_id=None)],
            ),
        )
    assert err.value.status_code in {400, 409}
    inventario = products.listar_productos()
    producto = next(x for x in inventario if x["id"] == p["id"])
    assert producto["stock"] == 7
    with database.get_db() as conn:
        original = conn.execute("SELECT estado, corrected_by_id FROM ventas WHERE id=?", (venta["venta_id"],)).fetchone()
        corrected = conn.execute("SELECT corrected_from_id, estado FROM ventas WHERE id=?", (out["corrected_sale_id"],)).fetchone()
    assert original["estado"] == "cancelled"
    assert original["corrected_by_id"] == out["corrected_sale_id"]
    assert corrected["corrected_from_id"] == venta["venta_id"]
    assert corrected["estado"] == "active"


def test_cancelar_venta_recupera_stock_y_registra_log():
    p = crear_producto("Borrador", stock=10, tiene_variantes=False)
    venta = sales.registrar_venta(
        schemas.VentaCrear(
            metodo_pago="efectivo",
            items=[schemas.ItemVenta(producto_id=p["id"], cantidad=4, variante_id=None)],
        )
    )
    out = sales.cancelar_venta(venta["venta_id"])
    assert out["estado"] == "cancelled"
    inventario = products.listar_productos()
    producto = next(x for x in inventario if x["id"] == p["id"])
    assert producto["stock"] == 10
    logs = _logs("sale", venta["venta_id"])
    assert [x["action"] for x in logs] == ["cancel", "create"]


def test_cancelar_compra_falla_si_ya_no_hay_stock_suficiente():
    p = crear_producto("Tinta", stock=0, tiene_variantes=False)
    compra = purchases.registrar_compra(
        schemas.CompraCrear(
            proveedor="Prov B",
            notas="",
            costo_envio=0,
            actualizar_costo=True,
            items=[schemas.ItemCompra(producto_id=p["id"], cantidad=5, costo_unitario=30, variante_id=None)],
        )
    )
    sales.registrar_venta(
        schemas.VentaCrear(
            metodo_pago="efectivo",
            items=[schemas.ItemVenta(producto_id=p["id"], cantidad=4, variante_id=None)],
        )
    )
    with pytest.raises(HTTPException) as err:
        purchases.cancelar_compra(compra["compra_id"])
    assert err.value.status_code == 409


def test_doble_cancelacion_devuelve_error_controlado():
    p = crear_producto("Marcador", stock=8, tiene_variantes=False)
    venta = sales.registrar_venta(
        schemas.VentaCrear(
            metodo_pago="efectivo",
            items=[schemas.ItemVenta(producto_id=p["id"], cantidad=1, variante_id=None)],
        )
    )
    sales.cancelar_venta(venta["venta_id"])
    with pytest.raises(HTTPException) as err:
        sales.cancelar_venta(venta["venta_id"])
    assert err.value.status_code == 400


def test_correccion_sobre_transaccion_cancelada_falla():
    p = crear_producto("Regla", stock=15, tiene_variantes=False)
    venta = sales.registrar_venta(
        schemas.VentaCrear(
            metodo_pago="efectivo",
            items=[schemas.ItemVenta(producto_id=p["id"], cantidad=2, variante_id=None)],
        )
    )
    sales.cancelar_venta(venta["venta_id"])
    with pytest.raises(HTTPException) as err:
        sales.corregir_venta(
            venta["venta_id"],
            schemas.VentaCorreccion(
                metodo_pago="tarjeta",
                items=[schemas.ItemVenta(producto_id=p["id"], cantidad=1, variante_id=None)],
            ),
        )
    assert err.value.status_code in {400, 409}


def test_consistencia_stock_final_multiples_operaciones():
    p = crear_producto("Cuadro", stock=20, tiene_variantes=False)
    compra = purchases.registrar_compra(
        schemas.CompraCrear(
            proveedor="Prov X",
            notas="",
            costo_envio=0,
            actualizar_costo=True,
            items=[schemas.ItemCompra(producto_id=p["id"], cantidad=5, costo_unitario=50, variante_id=None)],
        )
    )
    venta_1 = sales.registrar_venta(
        schemas.VentaCrear(
            metodo_pago="efectivo",
            items=[schemas.ItemVenta(producto_id=p["id"], cantidad=8, variante_id=None)],
        )
    )
    purchases.corregir_compra(
        compra["compra_id"],
        schemas.CompraCorreccion(
            proveedor="Prov X",
            notas="corr",
            costo_envio=0,
            actualizar_costo=True,
            items=[schemas.ItemCompra(producto_id=p["id"], cantidad=3, costo_unitario=50, variante_id=None)],
        ),
    )
    sales.cancelar_venta(venta_1["venta_id"])
    sales.registrar_venta(
        schemas.VentaCrear(
            metodo_pago="tarjeta",
            items=[schemas.ItemVenta(producto_id=p["id"], cantidad=4, variante_id=None)],
        )
    )

    inventario = products.listar_productos()
    producto = next(x for x in inventario if x["id"] == p["id"])
    # Stock esperado: 20 + 3 - 4 = 19
    assert producto["stock"] == 19
