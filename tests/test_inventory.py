"""
tests/test_inventory.py — Tests de Nivel 1: movimientos, conteo, descuentos, timeline
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
import database
from routers import products, sales, purchases
from schemas import schemas
from services.inventory import registrar_movimiento, comparar_conteo_fisico, confirmar_conteo_fisico


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    db_path = tmp_path / "erp_test.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    database.DB_PATH = str(db_path)
    database.init_db()
    database.init_compras()
    database.init_inventory()
    yield


def crear_producto(nombre, stock=10, precio=100):
    return products.crear_producto(
        schemas.ProductoCrear(nombre=nombre, precio=precio, costo=50, stock=stock, tiene_variantes=False)
    )


# ══════════════════════════════════════════
# MOVIMIENTOS DE INVENTARIO
# ══════════════════════════════════════════

class TestMovimientosInventario:

    def test_venta_genera_movimiento_automatico(self):
        p = crear_producto("Camiseta", stock=10)
        sales.registrar_venta(
            schemas.VentaCrear(
                items=[schemas.ItemVenta(producto_id=p["id"], cantidad=3)],
                metodo_pago="efectivo",
            )
        )
        with database.get_db() as conn:
            movs = conn.execute(
                "SELECT * FROM inventory_movements WHERE tipo='venta'"
            ).fetchall()
            assert len(movs) == 1
            assert movs[0]["referencia"] == "venta:1"

            items = conn.execute(
                "SELECT * FROM inventory_movement_items WHERE movimiento_id=?",
                (movs[0]["id"],),
            ).fetchall()
            assert len(items) == 1
            assert items[0]["stock_antes"] == 10
            assert items[0]["stock_despues"] == 7
            assert items[0]["cantidad"] == -3

    def test_compra_genera_movimiento_automatico(self):
        p = crear_producto("Pantalón", stock=5)
        purchases.registrar_compra(
            schemas.CompraCrear(
                proveedor="ProvTest",
                items=[schemas.ItemCompra(producto_id=p["id"], cantidad=10, costo_unitario=50)],
            )
        )
        with database.get_db() as conn:
            movs = conn.execute(
                "SELECT * FROM inventory_movements WHERE tipo='compra'"
            ).fetchall()
            assert len(movs) == 1
            assert "compra:1" in movs[0]["referencia"]

            items = conn.execute(
                "SELECT * FROM inventory_movement_items WHERE movimiento_id=?",
                (movs[0]["id"],),
            ).fetchall()
            assert items[0]["stock_antes"] == 5
            assert items[0]["stock_despues"] == 15
            assert items[0]["cantidad"] == 10

    def test_movimiento_manual_se_registra(self):
        p = crear_producto("Lápiz", stock=20)
        with database.get_db() as conn:
            mov_id = registrar_movimiento(
                conn, "ajuste", "Conteo manual",
                [{"producto_id": p["id"], "variante_id": None,
                  "cantidad": -5, "stock_antes": 20, "stock_despues": 15}],
            )
            assert mov_id is not None
            mov = conn.execute(
                "SELECT * FROM inventory_movements WHERE id=?", (mov_id,)
            ).fetchone()
            assert mov["tipo"] == "ajuste"
            assert mov["motivo"] == "Conteo manual"


# ══════════════════════════════════════════
# CONTEO FÍSICO
# ══════════════════════════════════════════

class TestConteoFisico:

    def test_comparar_conteo_sin_diferencias(self):
        p = crear_producto("Borrador", stock=10)
        with database.get_db() as conn:
            result = comparar_conteo_fisico(
                conn, [{"producto_id": p["id"], "cantidad_fisica": 10}]
            )
            assert result["total_diferencias"] == 0
            assert result["items"][0]["diferencia"] == 0

    def test_comparar_conteo_con_diferencias(self):
        p = crear_producto("Regla", stock=15)
        with database.get_db() as conn:
            result = comparar_conteo_fisico(
                conn, [{"producto_id": p["id"], "cantidad_fisica": 12}]
            )
            assert result["total_diferencias"] == 1
            assert result["items"][0]["diferencia"] == -3

    def test_confirmar_conteo_ajusta_stock(self):
        p = crear_producto("Cuaderno", stock=20)
        with database.get_db() as conn:
            result = confirmar_conteo_fisico(
                conn, [{"producto_id": p["id"], "cantidad_fisica": 17}],
                motivo="Inventario mensual",
            )
            assert result["items_ajustados"] == 1
            assert result["movimiento_id"] is not None

            # Verificar stock actualizado
            prod = conn.execute(
                "SELECT stock FROM productos WHERE id=?", (p["id"],)
            ).fetchone()
            assert prod["stock"] == 17

    def test_confirmar_conteo_sin_cambios_no_genera_movimiento(self):
        p = crear_producto("Goma", stock=5)
        with database.get_db() as conn:
            result = confirmar_conteo_fisico(
                conn, [{"producto_id": p["id"], "cantidad_fisica": 5}]
            )
            assert result["items_ajustados"] == 0
            assert result["movimiento_id"] is None


# ══════════════════════════════════════════
# DESCUENTOS EN VENTAS
# ══════════════════════════════════════════

class TestDescuentos:

    def test_venta_sin_descuento_retrocompatible(self):
        p = crear_producto("Bolso", stock=10, precio=1000)
        result = sales.registrar_venta(
            schemas.VentaCrear(
                items=[schemas.ItemVenta(producto_id=p["id"], cantidad=2)],
                metodo_pago="efectivo",
            )
        )
        assert result["total"] == 2000
        assert result["subtotal"] == 2000
        assert result["descuento_pct"] == 0
        assert result["descuento_monto"] == 0

    def test_venta_con_descuento_porcentual(self):
        p = crear_producto("Cartera", stock=10, precio=1000)
        result = sales.registrar_venta(
            schemas.VentaCrear(
                items=[schemas.ItemVenta(producto_id=p["id"], cantidad=2)],
                metodo_pago="efectivo",
                descuento_pct=10,
            )
        )
        assert result["subtotal"] == 2000
        assert result["total"] == 1800  # 2000 - 10% = 1800

    def test_venta_con_descuento_monto_fijo(self):
        p = crear_producto("Mochila", stock=10, precio=500)
        result = sales.registrar_venta(
            schemas.VentaCrear(
                items=[schemas.ItemVenta(producto_id=p["id"], cantidad=2)],
                metodo_pago="efectivo",
                descuento_monto=200,
            )
        )
        assert result["subtotal"] == 1000
        assert result["total"] == 800  # 1000 - 200

    def test_venta_con_descuento_por_item(self):
        p = crear_producto("Libro", stock=10, precio=500)
        result = sales.registrar_venta(
            schemas.VentaCrear(
                items=[schemas.ItemVenta(
                    producto_id=p["id"], cantidad=2, descuento_item=100
                )],
                metodo_pago="efectivo",
            )
        )
        # subtotal bruto = 1000, descuento item = 100, total = 900
        assert result["subtotal"] == 1000
        assert result["total"] == 900

    def test_descuento_no_puede_exceder_100_pct(self):
        with pytest.raises(Exception):
            schemas.VentaCrear(
                items=[schemas.ItemVenta(producto_id=1, cantidad=1)],
                descuento_pct=150,
            )


# ══════════════════════════════════════════
# TIMELINE
# ══════════════════════════════════════════

class TestTimeline:

    def test_timeline_incluye_ventas_y_compras(self):
        from routers.timeline import timeline

        p = crear_producto("Zapato", stock=10, precio=500)
        sales.registrar_venta(
            schemas.VentaCrear(
                items=[schemas.ItemVenta(producto_id=p["id"], cantidad=1)],
            )
        )
        purchases.registrar_compra(
            schemas.CompraCrear(
                proveedor="Zapatos SA",
                items=[schemas.ItemCompra(producto_id=p["id"], cantidad=5, costo_unitario=200)],
            )
        )

        result = timeline()
        assert result["total"] >= 2
        tipos = {e["tipo"] for e in result["eventos"]}
        assert "venta" in tipos
        assert "compra" in tipos

    def test_timeline_paginacion(self):
        from routers.timeline import timeline

        p = crear_producto("Vela", stock=50, precio=100)
        for _ in range(5):
            sales.registrar_venta(
                schemas.VentaCrear(
                    items=[schemas.ItemVenta(producto_id=p["id"], cantidad=1)],
                )
            )

        result = timeline(limit=2, page=1)
        assert result["limit"] == 2
        assert len(result["eventos"]) == 2
        assert result["pages"] >= 3

    def test_timeline_filtro_tipo(self):
        from routers.timeline import timeline

        p = crear_producto("Silla", stock=20, precio=5000)
        sales.registrar_venta(
            schemas.VentaCrear(
                items=[schemas.ItemVenta(producto_id=p["id"], cantidad=1)],
            )
        )
        purchases.registrar_compra(
            schemas.CompraCrear(
                proveedor="Muebles",
                items=[schemas.ItemCompra(producto_id=p["id"], cantidad=3, costo_unitario=2000)],
            )
        )

        result = timeline(tipo="venta")
        assert all(e["tipo"] == "venta" for e in result["eventos"])
