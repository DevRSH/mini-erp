"""
database.py — Inicialización y conexión a SQLite
Mini ERP | Sprint 4 — Variantes + Costo envío + Código proveedor
"""

import sqlite3
import os
from contextlib import contextmanager


def _default_db_path():
    env_path = os.environ.get("DB_PATH")
    if env_path:
        return env_path

    data_dir = "/data"
    if os.path.isdir(data_dir) and os.access(data_dir, os.W_OK):
        return os.path.join(data_dir, "erp.db")
    return os.path.join(os.path.dirname(__file__), "data", "erp.db")


DB_PATH = _default_db_path()
SQLITE_BUSY_TIMEOUT_MS = int(os.environ.get("SQLITE_BUSY_TIMEOUT_MS", "5000"))


def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(
        DB_PATH,
        timeout=max(SQLITE_BUSY_TIMEOUT_MS / 1000, 1),
    )
    conn.row_factory = sqlite3.Row
    conn.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS}")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def get_db():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _columnas_existentes(conn, tabla):
    rows = conn.execute(f"PRAGMA table_info({tabla})").fetchall()
    return {r["name"] for r in rows}


def _tabla_existe(conn, tabla):
    r = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (tabla,)
    ).fetchone()
    return r is not None


def _obtener_sql_tabla(conn, tabla):
    r = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
        (tabla,),
    ).fetchone()
    return (r["sql"] or "") if r else ""


def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS productos (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre           TEXT    NOT NULL,
                precio           REAL    NOT NULL CHECK(precio >= 0),
                costo            REAL    NOT NULL DEFAULT 0 CHECK(costo >= 0),
                stock            INTEGER NOT NULL DEFAULT 0 CHECK(stock >= 0),
                stock_minimo     INTEGER NOT NULL DEFAULT 5 CHECK(stock_minimo >= 0),
                categoria        TEXT    NOT NULL DEFAULT 'General',
                activo           INTEGER NOT NULL DEFAULT 1,
                created_at       TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            );
            CREATE TABLE IF NOT EXISTS ventas (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                total        REAL    NOT NULL CHECK(total >= 0),
                metodo_pago  TEXT    NOT NULL DEFAULT 'efectivo',
                created_at   TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            );
            CREATE TABLE IF NOT EXISTS detalle_venta (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                venta_id        INTEGER NOT NULL REFERENCES ventas(id),
                producto_id     INTEGER NOT NULL REFERENCES productos(id),
                cantidad        INTEGER NOT NULL CHECK(cantidad > 0),
                precio_unitario REAL    NOT NULL CHECK(precio_unitario >= 0),
                subtotal        REAL    NOT NULL CHECK(subtotal >= 0)
            );
            CREATE INDEX IF NOT EXISTS idx_detalle_venta_id ON detalle_venta(venta_id);
            CREATE INDEX IF NOT EXISTS idx_detalle_producto  ON detalle_venta(producto_id);
            CREATE INDEX IF NOT EXISTS idx_ventas_fecha      ON ventas(created_at);
        """)

        # Migraciones columnas productos
        cols = _columnas_existentes(conn, "productos")
        if "codigo_proveedor" not in cols:
            conn.execute("ALTER TABLE productos ADD COLUMN codigo_proveedor TEXT DEFAULT ''")
        if "costo_envio" not in cols:
            conn.execute("ALTER TABLE productos ADD COLUMN costo_envio REAL NOT NULL DEFAULT 0")
        if "tiene_variantes" not in cols:
            conn.execute("ALTER TABLE productos ADD COLUMN tiene_variantes INTEGER NOT NULL DEFAULT 0")

        # Migración detalle_venta
        dv_cols = _columnas_existentes(conn, "detalle_venta")
        if "variante_id" not in dv_cols:
            conn.execute("ALTER TABLE detalle_venta ADD COLUMN variante_id INTEGER")

        # Tabla variantes
        if not _tabla_existe(conn, "variantes"):
            conn.executescript("""
                CREATE TABLE variantes (
                    id             INTEGER PRIMARY KEY AUTOINCREMENT,
                    producto_id    INTEGER NOT NULL REFERENCES productos(id),
                    attr1_nombre   TEXT    NOT NULL,
                    attr1_valor    TEXT    NOT NULL,
                    attr2_nombre   TEXT,
                    attr2_valor    TEXT,
                    stock          INTEGER NOT NULL DEFAULT 0 CHECK(stock >= 0),
                    stock_minimo   INTEGER NOT NULL DEFAULT 2 CHECK(stock_minimo >= 0),
                    codigo_barras  TEXT    DEFAULT '',
                    activo         INTEGER NOT NULL DEFAULT 1,
                    created_at     TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
                );
                CREATE INDEX IF NOT EXISTS idx_variantes_producto ON variantes(producto_id);
                CREATE INDEX IF NOT EXISTS idx_variantes_codigo   ON variantes(codigo_barras);
            """)


def init_compras():
    """Migración adicional: tablas de compras. Llamar después de init_db()."""
    with get_db() as conn:
        if not _tabla_existe(conn, "compras"):
            conn.executescript("""
                CREATE TABLE compras (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    proveedor   TEXT    NOT NULL DEFAULT 'Sin nombre',
                    notas       TEXT    DEFAULT '',
                    subtotal    REAL    NOT NULL DEFAULT 0,
                    costo_envio REAL    NOT NULL DEFAULT 0,
                    total       REAL    NOT NULL DEFAULT 0,
                    created_at  TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
                );

                CREATE TABLE detalle_compra (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    compra_id       INTEGER NOT NULL REFERENCES compras(id),
                    producto_id     INTEGER NOT NULL REFERENCES productos(id),
                    variante_id     INTEGER REFERENCES variantes(id),
                    cantidad        INTEGER NOT NULL CHECK(cantidad > 0),
                    costo_unitario  REAL    NOT NULL CHECK(costo_unitario >= 0),
                    subtotal        REAL    NOT NULL CHECK(subtotal >= 0)
                );

                CREATE INDEX IF NOT EXISTS idx_detalle_compra_id  ON detalle_compra(compra_id);
                CREATE INDEX IF NOT EXISTS idx_detalle_compra_prod ON detalle_compra(producto_id);
            """)

        compras_cols = _columnas_existentes(conn, "compras")
        if "estado" not in compras_cols:
            conn.execute("ALTER TABLE compras ADD COLUMN estado TEXT NOT NULL DEFAULT 'active'")
        if "corrected_from_id" not in compras_cols:
            conn.execute("ALTER TABLE compras ADD COLUMN corrected_from_id INTEGER")
        if "corrected_by_id" not in compras_cols:
            conn.execute("ALTER TABLE compras ADD COLUMN corrected_by_id INTEGER")

        ventas_cols = _columnas_existentes(conn, "ventas")
        if "estado" not in ventas_cols:
            conn.execute("ALTER TABLE ventas ADD COLUMN estado TEXT NOT NULL DEFAULT 'active'")
        if "corrected_from_id" not in ventas_cols:
            conn.execute("ALTER TABLE ventas ADD COLUMN corrected_from_id INTEGER")
        if "corrected_by_id" not in ventas_cols:
            conn.execute("ALTER TABLE ventas ADD COLUMN corrected_by_id INTEGER")

        if not _tabla_existe(conn, "transaction_logs"):
            conn.executescript("""
                CREATE TABLE transaction_logs (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_type   TEXT    NOT NULL CHECK(entity_type IN ('purchase', 'sale')),
                    entity_id     INTEGER NOT NULL,
                    action        TEXT    NOT NULL CHECK(action IN ('create', 'update', 'cancel', 'link_correction')),
                    previous_data TEXT,
                    new_data      TEXT,
                    timestamp     TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
                );
                CREATE INDEX IF NOT EXISTS idx_transaction_logs_entity
                    ON transaction_logs(entity_type, entity_id, timestamp DESC);
            """)
        else:
            sql_def = _obtener_sql_tabla(conn, "transaction_logs")
            if "link_correction" not in sql_def:
                conn.executescript("""
                    ALTER TABLE transaction_logs RENAME TO transaction_logs_old;
                    CREATE TABLE transaction_logs (
                        id            INTEGER PRIMARY KEY AUTOINCREMENT,
                        entity_type   TEXT    NOT NULL CHECK(entity_type IN ('purchase', 'sale')),
                        entity_id     INTEGER NOT NULL,
                        action        TEXT    NOT NULL CHECK(action IN ('create', 'update', 'cancel', 'link_correction')),
                        previous_data TEXT,
                        new_data      TEXT,
                        timestamp     TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
                    );
                    INSERT INTO transaction_logs (id, entity_type, entity_id, action, previous_data, new_data, timestamp)
                    SELECT id, entity_type, entity_id, action, previous_data, new_data, timestamp
                    FROM transaction_logs_old;
                    DROP TABLE transaction_logs_old;
                    CREATE INDEX IF NOT EXISTS idx_transaction_logs_entity
                        ON transaction_logs(entity_type, entity_id, timestamp DESC);
                """)
