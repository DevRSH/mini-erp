# 🏪 Mini ERP

Sistema de gestión para microempresas — control de inventario, ventas, compras y reportes.

Construido con FastAPI + SQLite + HTML/JS vanilla. Desplegable como PWA instalable en cualquier celular.

---

## ✨ Funcionalidades

- **Inventario** — productos con variantes (color, talla), código de proveedor, costo de envío y margen de ganancia automático
- **Ventas** — registro rápido con carrito, descuento automático de stock, soporte para variantes
- **Compras** — registro de compras a proveedor con actualización automática de stock y costos
- **Reportes** — resumen por período (hoy / 7 días / mes), alertas de stock bajo, productos más vendidos, exportación HTML compartible por WhatsApp
- **Escáner** — lectura de códigos de barras con la cámara del celular (requiere HTTPS)
- **PWA** — instalable en Android e iOS desde el navegador, sin pasar por tiendas de apps

---

## 🛠️ Stack

| Capa | Tecnología |
|------|-----------|
| Backend | Python 3.13 + FastAPI |
| Base de datos | SQLite |
| Frontend | HTML + CSS + JavaScript vanilla |
| Deploy | Railway |
| PWA | Web App Manifest + Service Worker |

---

## 🚀 Instalación local

### Requisitos

- Python 3.10+
- pip

### Pasos

```bash
# 1. Clonar el repositorio
git clone https://github.com/DevRSH/mini-erp.git
cd mini-erp

# 2. Instalar dependencias
pip install fastapi uvicorn

# 3. Generar íconos PWA (solo primera vez)
python3 -c "
from PIL import Image, ImageDraw
def icono(size, path):
    img = Image.new('RGB', (size, size), '#E8821A')
    draw = ImageDraw.Draw(img)
    m = size//8
    draw.ellipse([m, m, size-m, size-m], fill='#C96A0D')
    img.save(path)
icono(192, 'icon-192.png')
icono(512, 'icon-512.png')
"

# 4. Lanzar el servidor
python main.py
```

Abrir en el navegador: **http://localhost:8000**

### Acceso desde celular (misma red WiFi)

```bash
ip a | grep "inet " | grep -v 127
```

Usar la IP del resultado (ej: `http://192.168.1.18:8000`) desde Chrome Android.

> ⚠️ El escáner de cámara solo funciona con HTTPS. En local usar entrada manual de código.

---

## ☁️ Deploy en Railway

```bash
# El repositorio ya incluye Procfile y requirements.txt
# Solo conectar el repo en railway.app y hacer deploy
```

**Variables de entorno en Railway:**

| Variable | Descripción |
|----------|-------------|
| `DB_PATH` | Ruta de la base de datos (por defecto `/data/erp.db`) |
| `BACKUP_KEY` | Clave para el endpoint de backup (próximamente) |

**Volumen persistente:**
- Mount path: `/data`
- La base de datos se guarda en `/data/erp.db`

---

## 📁 Estructura del proyecto

```
mini-erp/
├── main.py            # API FastAPI completa (endpoints de todos los sprints)
├── database.py        # Inicialización SQLite y migraciones
├── index.html         # Frontend completo (CSS + JS inline)
├── manifest.json      # Configuración PWA
├── service-worker.js  # Cache y soporte offline PWA
├── icon-192.png       # Ícono app 192x192
├── icon-512.png       # Ícono app 512x512
├── requirements.txt   # Dependencias Python
├── Procfile           # Comando de inicio para Railway
└── .gitignore
```

---

## 📋 Sprints completados

| Sprint | Módulo | Estado |
|--------|--------|--------|
| 1 | Inventario (CRUD + ajuste de stock) | ✅ |
| 2 | Ventas con descuento atómico de stock | ✅ |
| 3 | Reportes y alertas de stock bajo | ✅ |
| 4 | Variantes, código proveedor, escáner, margen | ✅ |
| 5 | Compras a proveedor, exportación de reportes | ✅ |
| 6 | Deploy Railway + volumen persistente + PWA | ✅ |

---

## 🔒 Pendiente para producción

- Autenticación (usuario y contraseña)
- Endpoint de backup protegido
- Tests automatizados con pytest
- Migración a PostgreSQL para multi-usuario

---

## 👤 Autor

**Raúl Salas Henríquez** — [@DevRSH](https://github.com/DevRSH)

Proyecto desarrollado como parte del aprendizaje en Ingeniería en Ciberseguridad — INACAP.
