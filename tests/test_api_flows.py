from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import HTTPException
import pytest

import database
import main


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    db_path = tmp_path / "erp_test.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    database.DB_PATH = str(db_path)
    database.init_db()
    database.init_compras()
    yield


def crear_producto(nombre, precio=1000, stock=0, tiene_variantes=False, stock_minimo=5):
    return main.crear_producto(
        main.ProductoCrear(
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
    return main.crear_variante(
        producto_id,
        main.VarianteCrear(
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

    inventario = main.listar_productos()
    producto = next(x for x in inventario if x["id"] == p["id"])
    assert producto["stock"] == 7


def test_compra_con_variantes_exige_variante_id():
    p = crear_producto("Zapato", stock=0, tiene_variantes=True)
    crear_variante(p["id"], "42", stock=3)

    with pytest.raises(HTTPException) as err:
        main.registrar_compra(
            main.CompraCrear(
                proveedor="Proveedor X",
                notas="",
                costo_envio=0,
                actualizar_costo=True,
                items=[
                    main.ItemCompra(
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

    compra = main.registrar_compra(
        main.CompraCrear(
            proveedor="Proveedor Y",
            notas="",
            costo_envio=0,
            actualizar_costo=True,
            items=[
                main.ItemCompra(
                    producto_id=p["id"],
                    variante_id=v["id"],
                    cantidad=3,
                    costo_unitario=700,
                )
            ],
        )
    )
    assert compra["compra_id"] > 0

    variantes = main.listar_variantes(p["id"])["variantes"]
    variante = next(x for x in variantes if x["id"] == v["id"])
    assert variante["stock"] == 5

    inventario = main.listar_productos()
    producto = next(x for x in inventario if x["id"] == p["id"])
    assert producto["stock"] == 5


def test_desactivar_ultima_variante_desactiva_modo_variantes():
    p = crear_producto("Gorro", stock=0, tiene_variantes=True)
    v = crear_variante(p["id"], "Azul", stock=4)

    res = main.desactivar_variante(v["id"])
    assert res["variantes_activas"] == 0

    inventario = main.listar_productos()
    producto = next(x for x in inventario if x["id"] == p["id"])
    assert producto["tiene_variantes"] == 0
    assert producto["stock"] == 0


def test_mas_vendidos_respeta_periodo():
    p = crear_producto("Botella", stock=20, tiene_variantes=False)

    venta_vieja = main.registrar_venta(
        main.VentaCrear(
            metodo_pago="efectivo",
            items=[main.ItemVenta(producto_id=p["id"], cantidad=1, variante_id=None)],
        )
    )
    with database.get_db() as conn:
        conn.execute(
            "UPDATE ventas SET created_at='2000-01-01 10:00:00' WHERE id=?",
            (venta_vieja["venta_id"],),
        )

    main.registrar_venta(
        main.VentaCrear(
            metodo_pago="efectivo",
            items=[main.ItemVenta(producto_id=p["id"], cantidad=2, variante_id=None)],
        )
    )

    top = main.mas_vendidos(limite=5, periodo="mes")
    assert top[0]["total_vendido"] == 2


def test_stock_bajo_incluye_variantes_criticas():
    p = crear_producto("Poleron", stock=0, tiene_variantes=True, stock_minimo=5)
    crear_variante(p["id"], "S", stock=1, stock_minimo=2)
    crear_variante(p["id"], "M", stock=10, stock_minimo=2)

    alertas = main.stock_bajo()
    producto = next(x for x in alertas if x["id"] == p["id"])
    assert producto["stock"] == 11
    assert len(producto["variantes_bajas"]) == 1


def test_historiales_devuelven_created_at_iso():
    p = crear_producto("Taza", stock=10, tiene_variantes=False)

    main.registrar_compra(
        main.CompraCrear(
            proveedor="Proveedor Z",
            notas="",
            costo_envio=0,
            actualizar_costo=True,
            items=[
                main.ItemCompra(
                    producto_id=p["id"],
                    variante_id=None,
                    cantidad=1,
                    costo_unitario=300,
                )
            ],
        )
    )
    compras = main.historial_compras()
    assert "T" in compras[0]["created_at"]

    main.registrar_venta(
        main.VentaCrear(
            metodo_pago="efectivo",
            items=[main.ItemVenta(producto_id=p["id"], cantidad=1, variante_id=None)],
        )
    )
    ventas = main.historial_ventas()
    assert "T" in ventas[0]["created_at"]
