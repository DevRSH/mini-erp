"""
main.py — Mini ERP | FastAPI Backend
Sprint 8: JWT, Pydantic Settings, Logging estructurado
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, Response, Cookie
from fastapi.responses import HTMLResponse, Response as FastResponse, FileResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import Optional, List
from database import init_db, init_compras, init_inventory, get_db
from audit_service import log_transaction, snapshot_sale, snapshot_purchase, list_logs
import os
import secrets
import sqlite3

from config import settings
from logger import log
from dependencies import (
    BACKUP_KEY, _validar_token
)

# Rutas que no requieren autenticación
RUTAS_PUBLICAS = {"/", "/login", "/manifest.json",
                  "/service-worker.js", "/icon-192.png", "/icon-512.png"}

# ────────────────────────────────────────────
# LIFESPAN (reemplaza @app.on_event deprecado)
# ────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    init_compras()
    init_inventory()
    yield

app = FastAPI(title="NESKO", version="4.0.0", lifespan=lifespan)

app.mount("/css", StaticFiles(directory="css"), name="css")
app.mount("/js", StaticFiles(directory="js"), name="js")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(sqlite3.IntegrityError)
async def sqlite_integrity_error_handler(request: Request, exc: sqlite3.IntegrityError):
    log.error("IntegrityError en %s: %s", request.url.path, exc)
    return JSONResponse(
        {"detail": "Conflicto de integridad de datos"},
        status_code=409,
    )


@app.exception_handler(sqlite3.OperationalError)
async def sqlite_operational_error_handler(request: Request, exc: sqlite3.OperationalError):
    detail = "Error operativo de base de datos"
    status = 500
    mensaje = str(exc).lower()
    if "locked" in mensaje or "busy" in mensaje:
        detail = "Base de datos ocupada temporalmente, reintenta"
        status = 503
    log.error("OperationalError en %s [%d]: %s", request.url.path, status, exc)
    return JSONResponse({"detail": detail}, status_code=status)

# ────────────────────────────────────────────
# MIDDLEWARE DE AUTENTICACIÓN
# ────────────────────────────────────────────

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path

    # Rutas públicas pasan sin verificar
    if path in RUTAS_PUBLICAS or path.startswith("/css/") or path.startswith("/js/"):
        return await call_next(request)

    # Endpoints públicos API que no requieren sesión previa
    if path in {"/api/login", "/api/sesion"}:
        return await call_next(request)

    # Verificar cookie de sesión
    token = request.cookies.get("erp_session")
    if not token or not _validar_token(token):
        # Si es llamada API → 401 JSON
        if path.startswith("/api/"):
            return JSONResponse({"detail": "No autenticado"}, status_code=401)
        # Si es página → redirigir al login
        return RedirectResponse(url="/", status_code=302)

    return await call_next(request)



# ────────────────────────────────────────────
# AUTENTICACIÓN — ENDPOINTS
# ────────────────────────────────────────────

from routers.auth import router as auth_router
app.include_router(auth_router)

from routers.products import router as products_router
app.include_router(products_router)

from routers.sales import router as sales_router
app.include_router(sales_router)

# ────────────────────────────────────────────
# SPRINT 3 — REPORTES
# ────────────────────────────────────────────
from routers.reports import router as reports_router
app.include_router(reports_router)

# ────────────────────────────────────────────
# SPRINT 5 — COMPRAS A PROVEEDOR
# ────────────────────────────────────────────
from routers.purchases import router as purchases_router
app.include_router(purchases_router)

# ────────────────────────────────────────────
# NIVEL 1 — INVENTARIO Y TIMELINE
# ────────────────────────────────────────────
from routers.inventory import router as inventory_router
app.include_router(inventory_router)

from routers.timeline import router as timeline_router
app.include_router(timeline_router)


@app.get("/api/transaction-logs")
def historial_logs(entity_type: Optional[str] = None, entity_id: Optional[int] = None, limite: int = 100):
    limite = max(1, min(limite, 300))
    with get_db() as conn:
        if entity_type and entity_type not in {"purchase", "sale"}:
            raise HTTPException(400, "entity_type debe ser purchase o sale")
        return list_logs(conn, entity_type=entity_type, entity_id=entity_id, limit=limite)


# ────────────────────────────────────────────
# SPRINT 5 — EXPORTACIÓN DE REPORTES
# ────────────────────────────────────────────

@app.get("/api/exportar/reporte")
def exportar_reporte(periodo: str = "mes"):
    """
    Genera un archivo HTML autocontenido con el reporte completo.
    Listo para compartir por WhatsApp o guardar en el celular.
    """
    filtros = {
        "hoy":    "date(v.created_at) = date('now','localtime')",
        "semana": "v.created_at >= date('now','-7 days','localtime')",
        "mes":    "strftime('%Y-%m', v.created_at) = strftime('%Y-%m', 'now','localtime')"
    }
    nombres_periodo = {"hoy": "Hoy", "semana": "Últimos 7 días", "mes": "Este mes"}
    if periodo not in filtros:
        raise HTTPException(400, "periodo debe ser: hoy, semana o mes")

    with get_db() as conn:
        # Resumen
        rv = conn.execute(
            f"""SELECT COUNT(*) AS total_ventas,
                       COALESCE(SUM(total),0) AS ingresos,
                       COALESCE(AVG(total),0) AS ticket_promedio
                FROM ventas v WHERE {filtros[periodo]} AND v.estado='active'"""
        ).fetchone()

        # Ganancia estimada
        gan = conn.execute(
            f"""SELECT COALESCE(SUM(
                    d.subtotal - (d.cantidad * (p.costo + COALESCE(p.costo_envio,0)))
                ),0) AS ganancia
                FROM detalle_venta d
                JOIN productos p ON d.producto_id = p.id
                JOIN ventas v ON d.venta_id = v.id
                WHERE {filtros[periodo]}"""
        ).fetchone()

        # Stock bajo
        stock_bajo = conn.execute(
            """SELECT nombre, stock, stock_minimo, categoria
               FROM productos WHERE activo=1 AND stock <= stock_minimo
               ORDER BY stock ASC LIMIT 20"""
        ).fetchall()

        # Más vendidos
        mas_vendidos = conn.execute(
            """SELECT p.nombre, SUM(d.cantidad) AS total_vendido,
                      SUM(d.subtotal) AS ingresos_totales
               FROM detalle_venta d
               JOIN productos p ON d.producto_id = p.id
               GROUP BY p.id ORDER BY total_vendido DESC LIMIT 10"""
        ).fetchall()

        # Últimas ventas
        ultimas = conn.execute(
            f"""SELECT v.id, v.total, v.metodo_pago, v.created_at
                FROM ventas v WHERE {filtros[periodo]} AND v.estado='active'
                ORDER BY v.created_at DESC LIMIT 20"""
        ).fetchall()

    from datetime import datetime
    ahora = datetime.now().strftime("%d/%m/%Y %H:%M")
    nombre_per = nombres_periodo[periodo]

    def fmt_num(n):
        return f"${int(n):,}".replace(",", ".")

    # ── Construir secciones HTML ──────────────────
    filas_stock = "".join(
        f"""<tr>
              <td>{r['nombre']}</td>
              <td style="color:{'#991B1B' if r['stock']==0 else '#92400E'};font-weight:700;">
                {'⛔ Agotado' if r['stock']==0 else f"⚠️ {r['stock']} uds"}
              </td>
              <td>{r['stock_minimo']}</td>
              <td>{r['categoria']}</td>
            </tr>"""
        for r in stock_bajo
    ) or "<tr><td colspan='4' style='text-align:center;color:#065F46;'>✅ Stock en orden</td></tr>"

    filas_vendidos = "".join(
        f"""<tr>
              <td><strong>#{i+1}</strong> {r['nombre']}</td>
              <td style="font-weight:700;">{r['total_vendido']} uds</td>
              <td style="color:#2D9B5E;font-weight:700;">{fmt_num(r['ingresos_totales'])}</td>
            </tr>"""
        for i, r in enumerate(mas_vendidos)
    ) or "<tr><td colspan='3' style='text-align:center;'>Sin datos</td></tr>"

    metodo_ic = {"efectivo": "💵", "transferencia": "📱", "tarjeta": "💳"}
    filas_ventas = "".join(
        f"""<tr>
              <td>#{str(r['id']).zfill(4)}</td>
              <td>{r['created_at'][:16].replace('T',' ')}</td>
              <td style="color:#2D9B5E;font-weight:700;">{fmt_num(r['total'])}</td>
              <td>{metodo_ic.get(r['metodo_pago'],'')}&nbsp;{r['metodo_pago']}</td>
            </tr>"""
        for r in ultimas
    ) or "<tr><td colspan='4' style='text-align:center;'>Sin ventas</td></tr>"

    ganancia = gan["ganancia"]
    margen_color = "#2D9B5E" if ganancia >= 0 else "#D63B3B"

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Reporte ERP — {nombre_per}</title>
<style>
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background:#F7F5F0; color:#1A1612; padding:16px; font-size:14px; }}
  .header {{ background:#1B3A6B; color:white; border-radius:14px;
             padding:20px; margin-bottom:16px; }}
  .header h1 {{ font-size:22px; font-weight:800; margin-bottom:4px; }}
  .header p  {{ font-size:13px; opacity:.8; }}
  .stats {{ display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:16px; }}
  .stat {{ background:white; border-radius:12px; padding:14px; text-align:center;
           border:1px solid #E8E3DA; }}
  .stat-value {{ font-size:24px; font-weight:800; line-height:1; margin-bottom:4px; }}
  .stat-label {{ font-size:11px; color:#7D7168; font-weight:600;
                 text-transform:uppercase; letter-spacing:.4px; }}
  .section {{ background:white; border-radius:12px; padding:16px;
              margin-bottom:14px; border:1px solid #E8E3DA; }}
  .section h2 {{ font-size:15px; font-weight:800; margin-bottom:12px;
                 padding-bottom:8px; border-bottom:1px solid #E8E3DA; }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  th {{ background:#F7F5F0; padding:8px; text-align:left; font-size:11px;
        font-weight:700; color:#7D7168; text-transform:uppercase; }}
  td {{ padding:9px 8px; border-bottom:1px solid #F0EDE6; vertical-align:top; }}
  tr:last-child td {{ border-bottom:none; }}
  .footer {{ text-align:center; font-size:11px; color:#7D7168; padding:12px 0; }}
  @media print {{ body {{ background:white; padding:0; }} }}
</style>
</head>
<body>

<div class="header">
    <h1>🏪 Reporte Fika</h1>
  <p>Período: <strong>{nombre_per}</strong> &nbsp;|&nbsp; Generado: {ahora}</p>
</div>

<div class="stats">
  <div class="stat">
    <div class="stat-value" style="color:#E8821A;">{rv['total_ventas']}</div>
    <div class="stat-label">Ventas</div>
  </div>
  <div class="stat">
    <div class="stat-value" style="color:#2D9B5E;">{fmt_num(rv['ingresos'])}</div>
    <div class="stat-label">Ingresos</div>
  </div>
  <div class="stat">
    <div class="stat-value" style="color:{margen_color};">{fmt_num(ganancia)}</div>
    <div class="stat-label">Ganancia est.</div>
  </div>
  <div class="stat">
    <div class="stat-value" style="color:#2A7DC9;">{fmt_num(rv['ticket_promedio'])}</div>
    <div class="stat-label">Ticket prom.</div>
  </div>
</div>

<div class="section">
  <h2>⚠️ Alertas de stock bajo ({len(stock_bajo)})</h2>
  <table>
    <tr><th>Producto</th><th>Stock</th><th>Mínimo</th><th>Categoría</th></tr>
    {filas_stock}
  </table>
</div>

<div class="section">
  <h2>🏆 Productos más vendidos</h2>
  <table>
    <tr><th>Producto</th><th>Cantidad</th><th>Ingresos</th></tr>
    {filas_vendidos}
  </table>
</div>

<div class="section">
  <h2>📋 Últimas ventas ({len(ultimas)})</h2>
  <table>
    <tr><th>#</th><th>Fecha</th><th>Total</th><th>Pago</th></tr>
    {filas_ventas}
  </table>
</div>

<div class="footer">
    Fika — Generado automáticamente el {ahora}
</div>

</body>
</html>"""

    filename = f"reporte_{periodo}_{datetime.now().strftime('%Y%m%d_%H%M')}.html"
    return Response(
        content=html,
        media_type="text/html",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ────────────────────────────────────────────
# SPRINT 7 — BACKUP PROTEGIDO
# ────────────────────────────────────────────

@app.get("/api/backup")
def descargar_backup(request: Request, clave: str = ""):
    """
    Descarga el archivo erp.db completo.
    Requiere clave secreta configurada en variable de entorno BACKUP_KEY.
    """
    if not BACKUP_KEY:
        raise HTTPException(403, "Backup no configurado. Define BACKUP_KEY en Railway.")
    clave_header = request.headers.get("X-Backup-Key", "")
    clave_efectiva = clave_header or clave
    if not secrets.compare_digest(clave_efectiva, BACKUP_KEY):
        ip = request.client.host if request.client else "unknown"
        log.warning("Backup fallido — clave incorrecta — IP: %s", ip)
        raise HTTPException(403, "Clave incorrecta")
    db_path = settings.db_path
    if not os.path.exists(db_path):
        raise HTTPException(404, "Base de datos no encontrada")

    from datetime import datetime
    fecha = datetime.now().strftime("%Y%m%d_%H%M")
    log.info("Backup descargado")
    return FileResponse(
        db_path,
        media_type="application/octet-stream",
        filename=f"backup_erp_{fecha}.db"
    )


# ────────────────────────────────────────────
# PWA — Archivos estáticos
# ────────────────────────────────────────────

@app.get("/manifest.json")
def manifest():
    path = os.path.join(os.path.dirname(__file__), "manifest.json")
    return FileResponse(path, media_type="application/manifest+json")

@app.get("/service-worker.js")
def service_worker():
    path = os.path.join(os.path.dirname(__file__), "service-worker.js")
    return FileResponse(path, media_type="application/javascript")

@app.get("/icon-192.png")
def icon_192():
    path = os.path.join(os.path.dirname(__file__), "icon-192.png")
    return FileResponse(path, media_type="image/png")

@app.get("/icon-512.png")
def icon_512():
    path = os.path.join(os.path.dirname(__file__), "icon-512.png")
    return FileResponse(path, media_type="image/png")


# ────────────────────────────────────────────
# FRONTEND
# ────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def frontend():
    html_path = os.path.join(os.path.dirname(__file__), "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
