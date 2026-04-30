// ═══════════════════════════════════════════
// ESTADO GLOBAL
// ═══════════════════════════════════════════
let todosProductos = [];
let productosVenta = [];
let carrito = {};          // key: "prod_ID" o "var_ID"
let scannerActivo = false;
let html5QrCode = null;
let pendienteProductoVariante = null; // producto esperando elección de variante

// ═══════════════════════════════════════════
// UTILIDADES
// ═══════════════════════════════════════════
const $ = id => document.getElementById(id);
const fmt = n => (n == null || isNaN(n)) ? '—' : '$' + Number(n).toLocaleString('es-CL');
const ALLOWED_TOAST_TYPES = new Set(['success', 'error', 'info']);
function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function toast(msg, tipo = 'success') {
  const c = $('toast-container');
  const el = document.createElement('div');
  const ic = { success: '✅', error: '❌', info: 'ℹ️' };
  const safeType = ALLOWED_TOAST_TYPES.has(tipo) ? tipo : 'success';
  el.className = `toast ${safeType}`;
  const icon = document.createElement('span');
  icon.textContent = ic[safeType] || '';
  const message = document.createElement('span');
  message.textContent = String(msg ?? '');
  el.append(icon, message);
  c.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

async function api(method, path, body = null) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body) opts.body = JSON.stringify(body);
  opts.credentials = 'same-origin';
  const res = await fetch(path, opts);
  const data = await res.json();
  if (!res.ok) {
    let msg = 'Error del servidor';
    if (data.detail) {
      if (typeof data.detail === 'string') msg = data.detail;
      else if (Array.isArray(data.detail)) msg = data.detail.map(e => `${e.loc.join('.')}: ${e.msg}`).join(' | ');
      else msg = JSON.stringify(data.detail);
    }
    throw new Error(msg);
  }
  return data;
}

async function obtenerVariantesProducto(productId) {
  return await api('GET', `/api/products/${productId}/variants`);
}

function cerrarModales() {
  document.querySelectorAll('.modal-overlay').forEach(m => m.classList.remove('open'));
  detenerScanner();
}
document.querySelectorAll('.modal-overlay').forEach(m => {
  m.addEventListener('click', e => { if (e.target === m) cerrarModales(); });
});

function marginClass(pct) {
  if (pct >= 30) return 'margin-good';
  if (pct >= 15) return 'margin-mid';
  return 'margin-bad';
}

// ═══════════════════════════════════════════
// NAVEGACIÓN
// ═══════════════════════════════════════════
function navTo(pag) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  $(`page-${pag}`).classList.add('active');
  $(`nav-${pag}`).classList.add('active');
  const loaders = {
    dashboard: () => { cargarDashboard(); cargarProveedores(); },
    inventario: cargarInventario,
    ventas: cargarProductosVenta,
    compras: cargarCompras,
    timeline: cargarTimeline,
    reportes: () => cargarReportes('hoy')
  };
  if (loaders[pag]) loaders[pag]();
}
