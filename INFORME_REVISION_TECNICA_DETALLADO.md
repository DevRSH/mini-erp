# Informe de Revisión Técnica Detallada — Proyecto Fika (Mini ERP)

Este informe detalla la estructura, funcionamiento y arquitectura del sistema Mini ERP "Fika". Se han corregido los problemas detectados en el escáner y se presenta a continuación un desglose completo del proyecto.

---

## 1. Estructura de Carpetas y Archivos

El proyecto sigue una arquitectura de **SPA (Single Page Application)** para el frontend y una **API REST modular** con FastAPI para el backend.

### Backend (Python/FastAPI)
- **`main.py`**: El punto de entrada de la aplicación. Configura el servidor, los middlewares (autenticación, CORS) y monta las rutas.
- **`routers/`**: Contiene la lógica de los endpoints dividida por módulos (productos, ventas, reportes, etc.). Esto mantiene el código organizado y escalable.
- **`schemas/`**: Define modelos de datos usando **Pydantic**. Estos archivos aseguran que los datos que llegan desde el frontend tengan el formato correcto (validación).
- **`services/`**: Contiene la lógica de negocio compleja que no pertenece directamente a una ruta.
- **`database.py`**: Gestiona la conexión con la base de datos **SQLite** (`erp.db`) y la creación de tablas iniciales.
- **`config.py`**: Maneja las configuraciones del sistema (variables de entorno, rutas de base de datos).
- **`logger.py` & `audit_service.py`**: Gestionan el registro de eventos y auditorías para seguimiento de transacciones.
- **`dependencies.py`**: Funciones auxiliares para la inyección de dependencias en FastAPI (como la validación de tokens).

### Frontend (HTML/JS/CSS)
- **`index.html`**: El archivo principal que carga el navegador. Contiene la estructura básica y los contenedores donde se "inyecta" el contenido dinámicamente.
- **`js/`**: Contiene la lógica del lado del cliente.
    - **`globals.js`**: Estado global y funciones de utilidad (toast, llamadas api).
    - **`scanner.js`**: Lógica específica para el escaneo de códigos de barras (corregida recientemente).
    - **`sales.js`**: Gestión del carrito y confirmación de ventas.
    - **`inventory.js`**: Visualización y gestión de productos.
    - **`main.js`**: Orquestador principal y registro del PWA.
- **`css/`**: Contiene los estilos visuales de la aplicación.

### Otros Archivos Importantes
- **`erp.db`**: El archivo de la base de datos SQLite. Aquí reside toda tu información.
- **`Procfile`**: Archivo de configuración para plataformas de despliegue como Heroku o Railway. Indica cómo ejecutar la aplicación (`uvicorn main:app`).
- **`runtime.txt`**: Especifica la versión de Python que debe usar el servidor de despliegue.
- **`manifest.json`**: Configuración para que la app se comporte como una **PWA** (Progressive Web App), permitiendo "instalarla" en el celular con icono y nombre.
- **`service-worker.js`**: Un script que corre en segundo plano en el navegador para permitir que la app funcione (parcialmente) sin conexión y se instale.

---

## 2. Guía de Extensiones y Archivos "Extraños"

Para que comprendas mejor qué son esos archivos con nombres poco comunes:

- **`.py` (Python)**: Código del backend. Se encarga de hablar con la base de datos y procesar la lógica pesada.
- **`.js` (JavaScript)**: Código del frontend. Se encarga de la interactividad (abrir modales, calcular el total del carrito, activar la cámara).
- **`.css` (Cascading Style Sheets)**: Define la apariencia (colores, bordes, tamaños, animaciones).
- **`.db` (Database)**: Archivo binario donde se guardan los datos de forma permanente.
- **`.json` (JavaScript Object Notation)**: Formato de intercambio de datos. Se usa tanto para configuración (`manifest.json`) como para la comunicación entre backend y frontend.
- **`.codex` / `.cursor`**: Carpetas o archivos generados por editores de código (como VS Code o Cursor) para indexación y asistencia de IA. No afectan al funcionamiento de la app.
- **`.venv/`**: Carpeta del "Entorno Virtual". Contiene las librerías de Python instaladas para este proyecto específico.
- **`.gitignore`**: Indica a Git qué archivos **no** debe subir a la nube (como bases de datos locales o entornos virtuales).

---

## 3. Conexiones y Flujo de Datos

### ¿Cómo se conectan?
1. **Frontend → Backend**: Cuando haces clic en "Confirmar venta", el archivo `js/sales.js` envía un **JSON** mediante una petición `fetch` al endpoint correspondiente en el backend (ej: `POST /api/ventas`).
2. **Backend → Base de Datos**: FastAPI recibe la petición, la valida y usa `database.py` para escribir la información en el archivo `erp.db`.
3. **Backend → Frontend**: El servidor responde con un mensaje de éxito. El frontend recibe esta respuesta y limpia el carrito.

### El flujo del Escáner (Fix Aplicado)
1. El usuario presiona "Escanear".
2. `js/scanner.js` llama a la librería **Html5Qrcode** (que ahora se carga correctamente desde `index.html`).
3. Al detectar un código, se envía al backend vía `GET /api/buscar?codigo=...`.
4. El backend busca en la tabla de `productos` o `variantes`.
5. Si lo encuentra, devuelve los datos y el frontend los agrega automáticamente al carrito.

---

## 4. Cambios Realizados en esta Revisión

1. **Reparación del Escáner**: Se detectó que la librería `html5-qrcode` no estaba siendo importada en `index.html`. Se añadió el script CDN necesario.
2. **Optimización de Scripts**: Se verificó que los archivos modulares estuvieran correctamente enlazados.
3. **Persistencia**: Se confirmaron los cambios en el repositorio Git local.

> [!TIP]
> Si planeas usar la aplicación en un lugar sin conexión a internet estable, te recomiendo descargar la librería `html5-qrcode.min.js` y guardarla en la carpeta `js/` en lugar de usar el enlace externo (CDN).
