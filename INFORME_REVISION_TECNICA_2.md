# 2do Informe de Revision Tecnica

Proyecto: `mini-erp`  
Fecha: `2026-04-27`  
Alcance: Frontend (`index.html`, `service-worker.js`) + Backend (`main.py`, `database.py`, `tests/`)

## Hallazgos (ordenados por severidad)

### Criticos

1. `PIN` por defecto debil y cookie de sesion sin `secure`
   Evidencia: [main.py](/home/ics-raulsh/Documents/Estudios/Auto Aprendizaje/Proyectos/mini-erp/main.py:22), [main.py](/home/ics-raulsh/Documents/Estudios/Auto Aprendizaje/Proyectos/mini-erp/main.py:118)  
   Riesgo: acceso no autorizado y robo de sesion en entornos HTTP o mal configurados.

2. Endpoint de backup expone secreto por query string (`/api/backup?clave=...`)
   Evidencia: [main.py](/home/ics-raulsh/Documents/Estudios/Auto Aprendizaje/Proyectos/mini-erp/main.py:1075)  
   Riesgo: filtrado en logs, historial, proxies, capturas o enlaces compartidos.

3. Riesgo alto de XSS DOM por uso de `innerHTML` con datos dinamicos sin sanitizacion
   Evidencia: [index.html](/home/ics-raulsh/Documents/Estudios/Auto Aprendizaje/Proyectos/mini-erp/index.html:1898), [index.html](/home/ics-raulsh/Documents/Estudios/Auto Aprendizaje/Proyectos/mini-erp/index.html:2004), [index.html](/home/ics-raulsh/Documents/Estudios/Auto Aprendizaje/Proyectos/mini-erp/index.html:2481), [index.html](/home/ics-raulsh/Documents/Estudios/Auto Aprendizaje/Proyectos/mini-erp/index.html:2784)  
   Riesgo: ejecucion de scripts maliciosos desde nombres/campos manipulados.

4. Condiciones de carrera en ventas/compras (validar y descontar/sumar en pasos separados)
   Evidencia: [main.py](/home/ics-raulsh/Documents/Estudios/Auto Aprendizaje/Proyectos/mini-erp/main.py:505), [main.py](/home/ics-raulsh/Documents/Estudios/Auto Aprendizaje/Proyectos/mini-erp/main.py:573), [main.py](/home/ics-raulsh/Documents/Estudios/Auto Aprendizaje/Proyectos/mini-erp/main.py:742)  
   Riesgo: sobreventa, inconsistencias de stock y errores bajo concurrencia real.

### Altos

5. Handlers inline (`onclick`) con strings dinamicos aumentan superficie de inyeccion
   Evidencia: [index.html](/home/ics-raulsh/Documents/Estudios/Auto Aprendizaje/Proyectos/mini-erp/index.html:2028), [index.html](/home/ics-raulsh/Documents/Estudios/Auto Aprendizaje/Proyectos/mini-erp/index.html:2364), [index.html](/home/ics-raulsh/Documents/Estudios/Auto Aprendizaje/Proyectos/mini-erp/index.html:2398)

6. Sin CSP efectiva y alta dependencia de JS inline
   Evidencia: [index.html](/home/ics-raulsh/Documents/Estudios/Auto Aprendizaje/Proyectos/mini-erp/index.html:4), [index.html](/home/ics-raulsh/Documents/Estudios/Auto Aprendizaje/Proyectos/mini-erp/index.html:1296)

7. Dependencia externa de `unpkg` sin `integrity` (SRI) ni fallback local
   Evidencia: [index.html](/home/ics-raulsh/Documents/Estudios/Auto Aprendizaje/Proyectos/mini-erp/index.html:136)

8. Integridad referencial incompleta en migracion de `detalle_venta.variante_id`
   Evidencia: [database.py](/home/ics-raulsh/Documents/Estudios/Auto Aprendizaje/Proyectos/mini-erp/database.py:103)  
   Riesgo: filas huerfanas o datos inconsistentes.

9. Contrato inconsistente de `/api/sesion` por middleware
   Evidencia: [main.py](/home/ics-raulsh/Documents/Estudios/Auto Aprendizaje/Proyectos/mini-erp/main.py:75), [main.py](/home/ics-raulsh/Documents/Estudios/Auto Aprendizaje/Proyectos/mini-erp/main.py:127)  
   Nota: hoy puede responder `401` antes de llegar a la logica que devuelve `{"autenticado": false}`.

### Medios

10. Parametro `limite` sin cota en endpoints de historial/listados
    Evidencia: [main.py](/home/ics-raulsh/Documents/Estudios/Auto Aprendizaje/Proyectos/mini-erp/main.py:583), [main.py](/home/ics-raulsh/Documents/Estudios/Auto Aprendizaje/Proyectos/mini-erp/main.py:642), [main.py](/home/ics-raulsh/Documents/Estudios/Auto Aprendizaje/Proyectos/mini-erp/main.py:827)  
    Riesgo: consultas excesivas (incluyendo `LIMIT -1` en SQLite).

11. SQLite en WAL sin `busy_timeout`
    Evidencia: [database.py](/home/ics-raulsh/Documents/Estudios/Auto Aprendizaje/Proyectos/mini-erp/database.py:29)  
    Riesgo: `database is locked` en picos de escritura.

12. Vista de historial existente pero no visible en la navegacion principal
    Evidencia: [index.html](/home/ics-raulsh/Documents/Estudios/Auto Aprendizaje/Proyectos/mini-erp/index.html:1426), [index.html](/home/ics-raulsh/Documents/Estudios/Auto Aprendizaje/Proyectos/mini-erp/index.html:1483), [index.html](/home/ics-raulsh/Documents/Estudios/Auto Aprendizaje/Proyectos/mini-erp/index.html:1939)

13. Service worker cachea de forma muy amplia con estrategia simple
    Evidencia: [service-worker.js](/home/ics-raulsh/Documents/Estudios/Auto Aprendizaje/Proyectos/mini-erp/service-worker.js:44)  
    Riesgo: cache growth, comportamiento impredecible offline/actualizaciones.

14. Accesibilidad: `maximum-scale=1.0` bloquea zoom en mobile
    Evidencia: [index.html](/home/ics-raulsh/Documents/Estudios/Auto Aprendizaje/Proyectos/mini-erp/index.html:6)

15. Frontend monolitico (HTML + CSS + JS) de alto acoplamiento
    Evidencia: [index.html](/home/ics-raulsh/Documents/Estudios/Auto Aprendizaje/Proyectos/mini-erp/index.html:1), [index.html](/home/ics-raulsh/Documents/Estudios/Auto Aprendizaje/Proyectos/mini-erp/index.html:1789)

### Bajos

16. Migraciones de compras poco robustas ante esquemas parciales
    Evidencia: [database.py](/home/ics-raulsh/Documents/Estudios/Auto Aprendizaje/Proyectos/mini-erp/database.py:130)

17. Deprecaciones de Pydantic (`@validator`, `min_items`)
    Evidencia: [main.py](/home/ics-raulsh/Documents/Estudios/Auto Aprendizaje/Proyectos/mini-erp/main.py:149), [main.py](/home/ics-raulsh/Documents/Estudios/Auto Aprendizaje/Proyectos/mini-erp/main.py:727)

18. Dependencias poco controladas para reproducibilidad
    Evidencia: [requirements.txt](/home/ics-raulsh/Documents/Estudios/Auto Aprendizaje/Proyectos/mini-erp/requirements.txt:1)

## Sugerencias de mejora (plan priorizado)

### Fase P0 (0-2 semanas)

1. Seguridad sesion:
   `APP_PIN` obligatorio por entorno, `secure=True` en cookie bajo HTTPS, rotacion de `SECRET_KEY`.
2. Backup seguro:
   mover clave a header (`X-Backup-Key`) o reutilizar sesion con rol admin; remover secreto de query.
3. Mitigacion XSS:
   eliminar `innerHTML` en renders de datos o sanitizar; migrar eventos inline a `addEventListener`.
4. Concurrencia stock:
   `BEGIN IMMEDIATE` + actualizacion condicional (`UPDATE ... WHERE stock >= ?`) y validacion por `rowcount`.

### Fase P1 (2-6 semanas)

5. API robusta:
   acotar `limite` con `Query(..., ge=1, le=500)`, manejo estandar de errores SQLite (`503/409`).
6. Integridad DB:
   revisar FKs reales de `variante_id`, restricciones `UNIQUE` y plan de migracion segura.
7. Hardening frontend:
   CSP real, dependencia scanner local con SRI/fallback.
8. UX operativa:
   boton de `Historial` en nav inferior + atajos de navegacion rapida.

### Fase P2 (6-10 semanas)

9. Modularizacion frontend:
   separar `index.html` en modulos (`api.js`, `inventory.js`, `sales.js`, `reports.js`, `styles.css`).
10. Calidad:
   pruebas E2E (login, venta, compra, variantes, reportes) con Playwright.
11. Observabilidad:
   logs estructurados y metricas basicas de latencia/error por endpoint.

## Nuevas funcionalidades propuestas (alto impacto)

### Quick Wins

1. Reabastecimiento asistido:
   boton "Reponer ahora" desde alertas de stock bajo que abra compra precompletada.
2. Kardex basico:
   historial de movimientos por producto/variante (venta, compra, ajuste, anulacion).
3. Venta rapida:
   productos frecuentes/recientes y busqueda global por codigo/nombre/proveedor.
4. Cierre diario de caja:
   apertura/cierre por metodo de pago, diferencia esperada vs real.

### Mediano plazo

5. Reposicion inteligente:
   sugerencias por rotacion, stock de seguridad y dias de cobertura.
6. Cuentas por pagar a proveedor:
   estado de facturas, vencimientos y abonos parciales.
7. Multi-sucursal:
   stock por ubicacion y transferencias internas.
8. Roles y permisos:
   perfiles `cajero`, `admin`, `dueno` con control granular por modulo.

## Open questions / supuestos

1. Se asumio despliegue principal en Railway + HTTPS, pero parte de la configuracion actual permite correr en HTTP.
2. Se asumio uso mono-tienda; si ya existe necesidad multi-sucursal, conviene adelantar ese diseno.
3. No se evaluo carga real en produccion; los riesgos de concurrencia fueron analizados por patron de codigo y SQLite.
4. Los tests actuales validan flujos de dominio (7 casos), pero no middleware HTTP, seguridad ni E2E de frontend.

## Resumen ejecutivo

El sistema tiene una base funcional buena para una microempresa y mejoro respecto al informe anterior en consistencia de variantes/compras. Sin embargo, hoy el mayor riesgo esta en seguridad frontend/backend (XSS + sesion/backup), seguido de concurrencia de stock y robustez operativa (limites API, cache, modularidad).  

Si se ejecuta la Fase P0 completa, el riesgo global baja de forma importante y deja una base sana para escalar funcionalidades como kardex, reposicion inteligente y cierre de caja.

## Agentes utilizados

Se uso analisis paralelo con 2 agentes especializados:

1. Agente Frontend: seguridad UX/UI, accesibilidad, performance y PWA.
2. Agente Backend: seguridad API, integridad de datos, concurrencia y testing.
