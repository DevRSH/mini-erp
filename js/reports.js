// ═══════════════════════════════════════════
// REPORTES (NIVEL 3 - INTELIGENCIA)
// ═══════════════════════════════════════════
let rentabilidadCache = [];
let inventarioCompletoCache = [];
let comprasProvCache = [];
let reporteProductosCache = [];
let rotacionCache = { alta:[], media:[], baja:[], sin_movimiento:[] };
let sortCol = 'ganancia';
let sortDir = -1;
let sortProvCol = 'total_invertido';
let sortProvDir = -1;

function cambiarSeccionReporte(seccion, btn) {
  document.querySelectorAll('#page-reportes > .period-tabs .period-tab').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  
  if (seccion === 'tablero') {
    $('reporte-tablero-content').style.display = 'block';
    $('reporte-rentabilidad-content').style.display = 'none';
    $('filtros-tablero').style.display = 'block';
    $('reporte-detallado-content').style.display = 'none';
    if (!$('tablero-desde').value) setPeriodoTablero('7d');
    else cargarTablero();
  } else if (seccion === 'rentabilidad') {
    $('reporte-tablero-content').style.display = 'none';
    $('reporte-rentabilidad-content').style.display = 'block';
    $('filtros-tablero').style.display = 'block';
    $('reporte-detallado-content').style.display = 'none';
    if (!$('tablero-desde').value) setPeriodoTablero('7d');
    else cargarRentabilidad();
  } else if (seccion === 'categorias') {
    $('reporte-tablero-content').style.display = 'none';
    $('reporte-rentabilidad-content').style.display = 'none';
    $('reporte-categorias-content').style.display = 'block';
    $('filtros-tablero').style.display = 'block';
    $('reporte-detallado-content').style.display = 'none';
    if (!$('tablero-desde').value) setPeriodoTablero('7d');
    else cargarReporteCategorias();
  } else if (seccion === 'inventario') {
    $('reporte-tablero-content').style.display = 'none';
    $('reporte-rentabilidad-content').style.display = 'none';
    $('reporte-categorias-content').style.display = 'none';
    $('reporte-inventario-content').style.display = 'block';
    $('filtros-tablero').style.display = 'none';
    $('reporte-detallado-content').style.display = 'none';
    if (!$('inv-fecha-corte').value) $('inv-fecha-corte').value = new Date().toISOString().split('T')[0];
    cargarReporteInventario();
  } else if (seccion === 'compras') {
    $('reporte-tablero-content').style.display = 'none';
    $('reporte-rentabilidad-content').style.display = 'none';
    $('reporte-categorias-content').style.display = 'none';
    $('reporte-inventario-content').style.display = 'none';
    $('reporte-compras-content').style.display = 'block';
    $('filtros-tablero').style.display = 'block';
    $('reporte-detallado-content').style.display = 'none';
    if (!$('tablero-desde').value) setPeriodoTablero('7d');
    else cargarReporteCompras();
  } else if (seccion === 'productos') {
    $('reporte-tablero-content').style.display = 'none';
    $('reporte-rentabilidad-content').style.display = 'none';
    $('reporte-categorias-content').style.display = 'none';
    $('reporte-inventario-content').style.display = 'none';
    $('reporte-compras-content').style.display = 'none';
    $('reporte-productos-content').style.display = 'block';
    $('filtros-tablero').style.display = 'none';
    $('reporte-detallado-content').style.display = 'none';
    cargarReporteProductos();
  } else {
    $('reporte-tablero-content').style.display = 'none';
    $('reporte-rentabilidad-content').style.display = 'none';
    $('filtros-tablero').style.display = 'none';
    $('reporte-detallado-content').style.display = 'block';
    cargarReportes('hoy');
  }
}

async function cargarRentabilidad() {
  const desde = $('tablero-desde').value;
  const hasta = $('tablero-hasta').value;
  if (!desde || !hasta) return;
  try {
    const data = await api('GET', `/api/reportes/rentabilidad?desde=${desde}&hasta=${hasta}`);
    rentabilidadCache = data.por_producto;
    renderRentabilidad(data);
  } catch (e) { toast('Error rentabilidad: ' + e.message, 'error'); }
}

function renderRentabilidad(data) {
  const res = data.resumen;
  $('rentabilidad-resumen').innerHTML = `
    <div style="text-align:center; padding:10px 0;">
      <div style="font-size:12px; color:var(--muted); text-transform:uppercase; font-weight:700;">Estado de Resultados</div>
      <div style="display:flex; justify-content:space-around; align-items:center; margin-top:15px;">
        <div>
          <div style="font-size:11px; color:var(--muted);">Ingresos</div>
          <div style="font-size:16px; font-weight:700;">${fmt(res.ingresos)}</div>
        </div>
        <div style="color:var(--muted); font-size:20px;">-</div>
        <div>
          <div style="font-size:11px; color:var(--muted);">Costos</div>
          <div style="font-size:16px; font-weight:700; color:var(--danger);">${fmt(res.costo_mercaderia + res.costo_envios)}</div>
        </div>
        <div style="color:var(--muted); font-size:20px;">=</div>
        <div>
          <div style="font-size:11px; color:var(--muted);">Ganancia</div>
          <div style="font-size:20px; font-weight:800; color:var(--success);">${fmt(res.ganancia)}</div>
          <div style="font-size:12px; font-weight:700; color:var(--success);">${res.margen_pct}% margen</div>
        </div>
      </div>
      <div style="margin-top:15px; font-size:11px; color:var(--muted); border-top:1px solid #eee; padding-top:8px;">
        Total invertido en compras: <strong>${fmt(res.total_invertido_compras)}</strong>
      </div>
    </div>
  `;

  renderTablaRentabilidad();
  renderGraficoRentabilidad($('canvas-rentabilidad'), data.evolucion_semanal);
}

function renderTablaRentabilidad() {
  const body = $('rentabilidad-body');
  body.innerHTML = rentabilidadCache.map(p => `
    <tr>
      <td>${p.nombre}</td>
      <td style="font-size:11px; color:var(--muted);">${p.categoria}</td>
      <td style="text-align:center;">${p.unidades_vendidas}</td>
      <td style="text-align:right;">${fmt(p.ingresos)}</td>
      <td style="text-align:right; color:var(--muted);">${fmt(p.costo_total)}</td>
      <td style="text-align:right; font-weight:700; color:var(--success);">${fmt(p.ganancia)}</td>
      <td style="text-align:right; font-weight:700;">${p.margen_pct}%</td>
    </tr>
  `).join('');
}

function ordenarRentabilidad(col) {
  if (sortCol === col) sortDir *= -1;
  else { sortCol = col; sortDir = -1; }
  
  rentabilidadCache.sort((a, b) => {
    let valA = a[col];
    let valB = b[col];
    if (typeof valA === 'string') {
      return sortDir * valA.localeCompare(valB);
    }
    return sortDir * (valA - valB);
  });
  renderTablaRentabilidad();
}

function renderGraficoRentabilidad(canvas, data) {
  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  ctx.scale(dpr, dpr);

  const w = rect.width;
  const h = rect.height;
  ctx.clearRect(0, 0, w, h);

  if (!data.length) {
    ctx.fillStyle = "#999";
    ctx.textAlign = "center";
    ctx.fillText("Sin datos suficientes", w/2, h/2);
    return;
  }

  const maxVal = Math.max(...data.map(d => Math.max(d.ingresos, d.ganancia))) * 1.1 || 100;
  const barW = (w - 40) / data.length;
  const margin = 30;

  data.forEach((d, i) => {
    const x = 20 + i * barW;
    const hIng = (d.ingresos / maxVal) * (h - 40);
    const hGan = (d.ganancia / maxVal) * (h - 40);

    // Barra Ingresos
    ctx.fillStyle = "rgba(232, 130, 26, 0.3)";
    ctx.fillRect(x + 5, h - 20 - hIng, barW - 10, hIng);
    
    // Barra Ganancia
    ctx.fillStyle = "#2D9B5E";
    ctx.fillRect(x + 10, h - 20 - hGan, barW - 20, hGan);

    // Label semana (cada 2 si son muchos)
    if (data.length < 7 || i % 2 === 0) {
      ctx.fillStyle = "#777";
      ctx.font = "10px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(d.semana.split('-')[1], x + barW/2, h - 5);
    }
  });

  // Eje base
  ctx.strokeStyle = "#eee";
  ctx.beginPath();
  ctx.moveTo(10, h - 20);
  ctx.lineTo(w - 10, h - 20);
  ctx.stroke();
}

async function cargarReporteCategorias() {
  const desde = $('tablero-desde').value;
  const hasta = $('tablero-hasta').value;
  if (!desde || !hasta) return;
  
  const seleccionadas = Array.from(document.querySelectorAll('.cat-check:checked')).map(cb => cb.value).join(',');
  
  try {
    const data = await api('GET', `/api/reportes/categorias?desde=${desde}&hasta=${hasta}${seleccionadas ? `&categorias=${seleccionadas}` : ''}`);
    renderReporteCategorias(data);
  } catch (e) { toast('Error categorías: ' + e.message, 'error'); }
}

async function renderReporteCategorias(data) {
  // Inyectar checkboxes si están vacíos
  const cbCont = $('categorias-checkboxes');
  if (!cbCont.innerHTML.trim()) {
    try {
      const todas = await api('GET', '/api/categorias');
      cbCont.innerHTML = todas.map(c => `
        <label style="font-size:12px; display:flex; align-items:center; gap:4px; background:#eee; padding:4px 8px; border-radius:12px; cursor:pointer;">
          <input type="checkbox" class="cat-check" value="${c}" checked onchange="cargarReporteCategorias()"> ${escapeHtml(c)}
        </label>
      `).join('');
    } catch (e) {}
  }

  const items = [...data.categorias];
  if (data.sin_categoria.unidades_vendidas > 0) items.push(data.sin_categoria);

  const body = $('categorias-body');
  body.innerHTML = items.map(c => `
    <tr style="cursor:pointer;" onclick="toggleDetalleCategoria('${c.nombre.replace(/'/g, "\\'")}')">
      <td><strong>${c.nombre}</strong> <span style="font-size:10px; color:var(--info);">▼</span></td>
      <td style="text-align:center;">${c.productos_activos}</td>
      <td style="text-align:center;">${c.unidades_vendidas}</td>
      <td style="text-align:right;">${fmt(c.ingresos)}</td>
      <td style="text-align:right;">${fmt(c.ganancia)}</td>
      <td style="text-align:right; font-weight:700;">${c.margen_pct}%</td>
    </tr>
    <tr id="detalle-cat-${c.nombre}" style="display:none; background:#fdfdfd;">
      <td colspan="6" id="content-cat-${c.nombre}" style="padding:0;">
        <div class="spinner" style="margin:10px auto;"></div>
      </td>
    </tr>
  `).join('');

  renderGraficoCategorias($('canvas-categorias-torta'), items);
}

function renderGraficoCategorias(canvas, items) {
  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  const size = 250;
  canvas.width = size * dpr;
  canvas.height = size * dpr;
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, size, size);

  if (!items.length) return;

  const total = items.reduce((acc, curr) => acc + curr.ingresos, 0);
  if (total === 0) return;

  // Agrupar otros si hay más de 8
  let sorted = [...items].sort((a, b) => b.ingresos - a.ingresos);
  let chartData = sorted.slice(0, 7);
  if (sorted.length > 7) {
    const otrosIng = sorted.slice(7).reduce((acc, curr) => acc + curr.ingresos, 0);
    chartData.push({ nombre: 'Otros', ingresos: otrosIng });
  }

  const colors = ['#E8821A', '#2D9B5E', '#2A7DC9', '#F59E0B', '#10B981', '#3B82F6', '#8B5CF6', '#6B7280'];
  let startAngle = 0;
  const centerX = size / 2;
  const centerY = size / 2;
  const radius = size / 2 - 20;

  chartData.forEach((d, i) => {
    const sliceAngle = (d.ingresos / total) * 2 * Math.PI;
    
    ctx.fillStyle = colors[i % colors.length];
    ctx.beginPath();
    ctx.moveTo(centerX, centerY);
    ctx.arc(centerX, centerY, radius, startAngle, startAngle + sliceAngle);
    ctx.closePath();
    ctx.fill();

    // Dibujar porcentaje
    if (sliceAngle > 0.2) {
      const middleAngle = startAngle + sliceAngle / 2;
      const textX = centerX + (radius / 1.5) * Math.cos(middleAngle);
      const textY = centerY + (radius / 1.5) * Math.sin(middleAngle);
      ctx.fillStyle = "white";
      ctx.font = "bold 10px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(`${Math.round((d.ingresos/total)*100)}%`, textX, textY);
    }

    startAngle += sliceAngle;
  });
}

async function toggleDetalleCategoria(nombre) {
  const row = $(`detalle-cat-${nombre}`);
  if (row.style.display === 'table-row') {
    row.style.display = 'none';
    return;
  }
  row.style.display = 'table-row';
  const cont = $(`content-cat-${nombre}`);
  
  const desde = $('tablero-desde').value;
  const hasta = $('tablero-hasta').value;
  
  try {
    // Reutilizamos el endpoint de rentabilidad filtrando por categoría
    // (O podemos hacer una llamada nueva si el backend lo permite)
    const prods = await api('GET', `/api/reportes/rentabilidad?desde=${desde}&hasta=${hasta}`);
    const filtrados = prods.por_producto.filter(p => (p.categoria || 'Sin categoría') === nombre);
    
    cont.innerHTML = `
      <div style="padding:10px 20px;">
        <table style="width:100%; font-size:12px; border-collapse:collapse;">
          <thead>
            <tr style="border-bottom:1px solid #eee; color:var(--muted);">
              <th style="text-align:left; padding:4px;">Producto</th>
              <th style="text-align:center;">Vend.</th>
              <th style="text-align:right;">Ganancia</th>
              <th style="text-align:right;">Margen</th>
            </tr>
          </thead>
          <tbody>
            ${filtrados.map(p => `
              <tr>
                <td style="padding:4px;">${p.nombre}</td>
                <td style="text-align:center;">${p.unidades_vendidas}</td>
                <td style="text-align:right; font-weight:700; color:var(--success);">${fmt(p.ganancia)}</td>
                <td style="text-align:right;">${p.margen_pct}%</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;
  } catch (e) { cont.innerHTML = 'Error cargando detalle'; }
}

async function exportarRentabilidadHTML() {
  const desde = $('tablero-desde').value;
  const hasta = $('tablero-hasta').value;
  try {
    const data = await api('GET', `/api/reportes/rentabilidad?desde=${desde}&hasta=${hasta}`);
    const res = data.resumen;
    
    const html = `
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Reporte de Rentabilidad — ${desde} a ${hasta}</title>
<style>
  body { font-family: sans-serif; padding: 30px; color: #333; }
  .resumen { display: flex; gap: 20px; margin-bottom: 30px; background: #f9f9f9; padding: 20px; border-radius: 8px; }
  .stat { flex: 1; text-align: center; }
  .val { font-size: 20px; font-weight: bold; }
  table { width: 100%; border-collapse: collapse; margin-top: 20px; }
  th { background: #eee; text-align: left; padding: 10px; }
  td { padding: 10px; border-bottom: 1px solid #eee; }
  .pos { color: green; font-weight: bold; }
</style>
</head>
<body>
  <h1>📈 Informe de Rentabilidad — Fika</h1>
  <p>Periodo: <strong>${desde}</strong> al <strong>${hasta}</strong></p>

  <div class="resumen">
    <div class="stat"><div>Ingresos</div><div class="val">${fmt(res.ingresos)}</div></div>
    <div class="stat"><div>Costo Mercadería</div><div class="val">${fmt(res.costo_mercaderia)}</div></div>
    <div class="stat"><div>Costo Envíos</div><div class="val">${fmt(res.costo_envios)}</div></div>
    <div class="stat"><div>Ganancia Neta</div><div class="val pos">${fmt(res.ganancia)}</div></div>
    <div class="stat"><div>Margen</div><div class="val pos">${res.margen_pct}%</div></div>
  </div>

  <h2>Detalle por Producto</h2>
  <table>
    <thead>
      <tr><th>Producto</th><th>Categoría</th><th>Vendido</th><th>Ingresos</th><th>Costo Total</th><th>Ganancia</th><th>Margen</th></tr>
    </thead>
    <tbody>
      ${data.por_producto.map(p => `
        <tr>
          <td>${p.nombre}</td>
          <td>${p.categoria}</td>
          <td>${p.unidades_vendidas}</td>
          <td>${fmt(p.ingresos)}</td>
          <td>${fmt(p.costo_total)}</td>
          <td class="pos">${fmt(p.ganancia)}</td>
          <td>${p.margen_pct}%</td>
        </tr>
      `).join('')}
    </tbody>
  </table>
  <p style="margin-top:20px; font-size:12px; color:#777;">Total invertido en compras en el período: ${fmt(res.total_invertido_compras)}</p>
</body>
</html>`;

    const blob = new Blob([html], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `rentabilidad_fika_${desde}_${hasta}.html`;
    a.click();
    toast('Informe de rentabilidad exportado 📤');
  } catch (e) { toast('Error exportando: ' + e.message, 'error'); }
}

async function exportarCategoriasHTML() {
  const desde = $('tablero-desde').value;
  const hasta = $('tablero-hasta').value;
  const seleccionadas = Array.from(document.querySelectorAll('.cat-check:checked')).map(cb => cb.value).join(',');
  
  try {
    const data = await api('GET', `/api/reportes/categorias?desde=${desde}&hasta=${hasta}${seleccionadas ? `&categorias=${seleccionadas}` : ''}`);
    
    const html = `
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Rentabilidad por Categoría — ${desde} a ${hasta}</title>
<style>
  body { font-family: sans-serif; padding: 30px; color: #333; }
  table { width: 100%; border-collapse: collapse; margin-top: 20px; }
  th { background: #f4f4f4; text-align: left; padding: 12px; border-bottom: 2px solid #ddd; }
  td { padding: 12px; border-bottom: 1px solid #eee; }
  .total-row { font-weight: bold; background: #fafafa; }
</style>
</head>
<body>
  <h1>📊 Rentabilidad por Categoría — Fika</h1>
  <p>Periodo: <strong>${desde}</strong> al <strong>${hasta}</strong></p>

  <table>
    <thead>
      <tr>
        <th>Categoría</th>
        <th>Productos</th>
        <th>Vendido</th>
        <th>Ingresos</th>
        <th>Ganancia</th>
        <th>Margen</th>
        <th>Top Producto</th>
      </tr>
    </thead>
    <tbody>
      ${data.categorias.map(c => `
        <tr>
          <td><strong>${c.nombre}</strong></td>
          <td>${c.productos_activos}</td>
          <td>${c.unidades_vendidas}</td>
          <td>${fmt(c.ingresos)}</td>
          <td>${fmt(c.ganancia)}</td>
          <td>${c.margen_pct}%</td>
          <td>${c.top_producto}</td>
        </tr>
      `).join('')}
      <tr class="total-row">
        <td>${data.sin_categoria.nombre}</td>
        <td>${data.sin_categoria.productos_activos}</td>
        <td>${data.sin_categoria.unidades_vendidas}</td>
        <td>${fmt(data.sin_categoria.ingresos)}</td>
        <td>${fmt(data.sin_categoria.ganancia)}</td>
        <td>${data.sin_categoria.margen_pct}%</td>
        <td>${data.sin_categoria.top_producto}</td>
      </tr>
    </tbody>
  </table>
</body>
</html>`;

    const blob = new Blob([html], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `categorias_fika_${desde}_${hasta}.html`;
    a.click();
    toast('Informe por categoría exportado 📤');
  } catch (e) { toast('Error exportando: ' + e.message, 'error'); }
}

async function cargarReporteInventario() {
  const corte = $('inv-fecha-corte').value || new Date().toISOString().split('T')[0];
  try {
    const data = await api('GET', `/api/reportes/inventario?fecha_corte=${corte}`);
    inventarioCompletoCache = data.listado_completo;
    rotacionCache = data.por_rotacion;
    renderReporteInventario(data);
  } catch (e) { toast('Error inventario: ' + e.message, 'error'); }
}

function renderReporteInventario(data) {
  const res = data.resumen;
  $('inv-valor-bodega').textContent = fmt(res.valor_bodega);
  $('inv-total-prods').textContent = res.total_productos;
  $('inv-agotados').textContent = res.agotados;
  $('inv-bajo-min').textContent = res.bajo_minimo;
  $('inv-sin-mov').textContent = res.sin_movimiento_30d;

  // Críticos
  const cCont = $('inv-criticos-list');
  $('inv-criticos-count').textContent = data.criticos.length;
  if (!data.criticos.length) {
    cCont.innerHTML = '<div class="empty-state" style="padding:10px 0;">✅ Sin alertas críticas</div>';
  } else {
    cCont.innerHTML = data.criticos.map(c => `
      <div style="display:flex; justify-content:space-between; align-items:center; padding:8px 0; border-bottom:1px solid #eee;">
        <div>
          <div style="font-weight:700; font-size:13px;">${c.nombre}</div>
          ${c.variante ? `<div style="font-size:11px; color:var(--info);">${c.variante}</div>` : ''}
        </div>
        <div style="text-align:right;">
          <div class="badge ${c.stock === 0 ? 'danger' : 'warn'}">${c.stock === 0 ? 'AGOTADO' : `${c.stock} uds`}</div>
          <div style="font-size:10px; color:var(--muted);">Mín: ${c.stock_minimo}</div>
        </div>
      </div>
    `).join('');
  }

  // Por defecto mostrar pestaña Alta
  tabRotacion('alta', document.querySelector('.btn-rotacion'));
  
  // Listado completo (primeros 200)
  renderInvCompleto(inventarioCompletoCache.slice(0, 200));
}

function tabRotacion(tipo, btn) {
  document.querySelectorAll('.btn-rotacion').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  
  const lista = rotacionCache[tipo] || [];
  const cont = $('inv-rotacion-list');
  
  if (!lista.length) {
    cont.innerHTML = '<div class="empty-state" style="padding:20px 0;">Sin productos en este rango</div>';
    return;
  }
  
  cont.innerHTML = lista.map(p => `
    <div style="display:flex; justify-content:space-between; padding:10px 12px; border-bottom:1px solid #f0f0f0;">
      <div style="flex:1;">
        <div style="font-weight:700; font-size:13px;">${p.nombre}</div>
        <div style="font-size:11px; color:var(--muted);">${p.categoria}</div>
      </div>
      <div style="text-align:right; min-width:80px;">
        <div style="font-weight:700;">${p.stock} uds</div>
        <div style="font-size:10px; color:${p.dias_sin_vender <= 3 ? 'var(--success)' : '#777'};">
          ${p.dias_sin_vender === null ? 'Sin ventas' : `${p.dias_sin_vender} días`}
        </div>
      </div>
    </div>
  `).join('');
}

function filtrarInvCompleto() {
  const q = $('search-inv-completo').value.toLowerCase();
  const filtered = inventarioCompletoCache.filter(p => 
    p.nombre.toLowerCase().includes(q) || 
    p.categoria.toLowerCase().includes(q)
  );
  renderInvCompleto(filtered.slice(0, 200));
  $('inv-completo-footer').textContent = `Mostrando ${Math.min(filtered.length, 200)} de ${filtered.length} resultados`;
}

function renderInvCompleto(lista) {
  const body = $('inv-completo-body');
  body.innerHTML = lista.map(p => `
    <tr>
      <td>
        <div style="font-weight:700;">${p.nombre}</div>
        <div style="font-size:10px; color:var(--muted);">${p.categoria}</div>
      </td>
      <td style="text-align:center;">
        <span class="badge ${p.stock === 0 ? 'danger' : p.stock <= p.stock_minimo ? 'warn' : ''}" style="font-size:10px;">${p.stock}</span>
      </td>
      <td style="text-align:right; color:var(--muted);">${fmt(p.valor_bodega)}</td>
      <td style="text-align:right;">
        <div style="font-size:11px;">${p.ultima_venta || '—'}</div>
        <div style="font-size:9px; color:#999;">${p.dias_sin_vender !== null ? `${p.dias_sin_vender}d` : ''}</div>
      </td>
    </tr>
  `).join('');
}

function toggleSection(id) {
  const el = $(id);
  el.style.display = el.style.display === 'none' ? 'block' : 'none';
}

async function cargarReporteCompras() {
  const desde = $('tablero-desde').value;
  const hasta = $('tablero-hasta').value;
  if (!desde || !hasta) return;
  try {
    const data = await api('GET', `/api/reportes/compras?desde=${desde}&hasta=${hasta}`);
    comprasProvCache = data.por_proveedor;
    renderReporteCompras(data);
  } catch (e) { toast('Error compras: ' + e.message, 'error'); }
}

function renderReporteCompras(data) {
  const res = data.resumen;
  $('comp-total-invertido').textContent = fmt(res.total_invertido);
  $('comp-num-compras').textContent = res.num_compras;
  $('comp-num-prov').textContent = res.num_proveedores;
  $('comp-total-envios').textContent = fmt(res.total_envios);

  renderTablaComprasProv();

  $('compras-prods-body').innerHTML = data.productos_mas_comprados.map(p => {
    const varC = p.variacion_costo_pct === null ? '—' : `${p.variacion_costo_pct}%`;
    const varS = p.variacion_costo_pct === null ? '' : p.variacion_costo_pct > 0 ? 'color:var(--danger);' : p.variacion_costo_pct < 0 ? 'color:var(--success);' : 'color:#999;';
    return `
      <tr>
        <td>
          <div style="font-weight:700;">${p.nombre}</div>
          <div style="font-size:10px; color:var(--muted);">${p.categoria}</div>
        </td>
        <td style="text-align:center;">${p.unidades_compradas}</td>
        <td style="text-align:right;">${fmt(p.costo_promedio)}</td>
        <td style="text-align:right; font-weight:700; ${varS}">${varC}</td>
      </tr>
    `;
  }).join('');
}

function renderTablaComprasProv() {
  const body = $('compras-prov-body');
  body.innerHTML = comprasProvCache.map(p => `
    <tr style="cursor:pointer;" onclick="toggleDetalleProveedor('${p.nombre.replace(/'/g, "\\'")}')">
      <td><strong>${p.nombre}</strong> <span style="font-size:10px; color:var(--info);">▼</span></td>
      <td style="text-align:center;">${p.num_compras}</td>
      <td style="text-align:right; font-weight:700;">${fmt(p.total_invertido)}</td>
    </tr>
    <tr id="detalle-prov-${p.nombre}" style="display:none; background:#f9f9f9;">
      <td colspan="3" id="content-prov-${p.nombre}" style="padding:0;">
        <div class="spinner" style="margin:10px auto;"></div>
      </td>
    </tr>
  `).join('');
}

function ordenarComprasProv(col) {
  if (sortProvCol === col) sortProvDir *= -1;
  else { sortProvCol = col; sortProvDir = -1; }
  
  comprasProvCache.sort((a, b) => {
    let valA = a[col];
    let valB = b[col];
    if (typeof valA === 'string') return sortProvDir * valA.localeCompare(valB);
    return sortProvDir * (valA - valB);
  });
  renderTablaComprasProv();
}

async function toggleDetalleProveedor(nombre) {
  const row = $(`detalle-prov-${nombre}`);
  if (row.style.display === 'table-row') {
    row.style.display = 'none';
    return;
  }
  row.style.display = 'table-row';
  const cont = $(`content-prov-${nombre}`);
  
  const desde = $('tablero-desde').value;
  const hasta = $('tablero-hasta').value;
  
  try {
    const data = await api('GET', `/api/reportes/compras?desde=${desde}&hasta=${hasta}`);
    const freq = data.frecuencia_por_proveedor.find(f => f.proveedor === nombre);
    
    if (!freq) { cont.innerHTML = '<div style="padding:10px;">Sin compras en este periodo</div>'; return; }
    
    cont.innerHTML = `
      <div style="padding:10px 15px;">
        <table style="width:100%; font-size:11px; border-collapse:collapse;">
          <thead>
            <tr style="border-bottom:1px solid #eee; color:var(--muted);">
              <th style="text-align:left; padding:4px;">ID</th>
              <th style="text-align:center; padding:4px;">Fecha</th>
              <th style="text-align:right; padding:4px;">Total</th>
            </tr>
          </thead>
          <tbody>
            ${freq.compras.map(c => `
              <tr>
                <td style="padding:4px; color:var(--info);">#${c.id.toString().zfill(4)}</td>
                <td style="text-align:center; padding:4px;">${c.fecha}</td>
                <td style="text-align:right; padding:4px; font-weight:700;">${fmt(c.total)}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;
  } catch (e) { cont.innerHTML = 'Error cargando detalle'; }
}

async function exportarComprasHTML() {
  const desde = $('tablero-desde').value;
  const hasta = $('tablero-hasta').value;
  try {
    const data = await api('GET', `/api/reportes/compras?desde=${desde}&hasta=${hasta}`);
    const res = data.resumen;
    
    const html = `
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Reporte de Compras — ${desde} a ${hasta}</title>
<style>
  body { font-family: sans-serif; padding: 30px; color: #333; line-height: 1.5; }
  .resumen { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 30px; }
  .stat { background: #f4f7fa; padding: 15px; border-radius: 8px; text-align: center; border: 1px solid #e1e8ed; }
  .val { font-size: 20px; font-weight: bold; display: block; margin-bottom: 5px; color: #1B3A6B; }
  .lab { font-size: 11px; color: #777; text-transform: uppercase; font-weight: bold; }
  table { width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 13px; }
  th { background: #f8fafc; text-align: left; padding: 12px; border-bottom: 2px solid #e2e8f0; }
  td { padding: 12px; border-bottom: 1px solid #edf2f7; }
  .pos { color: #2D9B5E; }
  .neg { color: #d63b3b; }
</style>
</head>
<body>
  <h1>📊 Informe de Compras y Proveedores — Fika</h1>
  <p>Periodo: <strong>${desde}</strong> al <strong>${hasta}</strong></p>

  <div class="resumen">
    <div class="stat"><span class="val">${fmt(res.total_invertido)}</span><span class="lab">Total Invertido</span></div>
    <div class="stat"><span class="val">${res.num_compras}</span><span class="lab">Compras</span></div>
    <div class="stat"><span class="val">${res.num_proveedores}</span><span class="lab">Proveedores</span></div>
    <div class="stat"><span class="val">${fmt(res.total_envios)}</span><span class="lab">Gasto Envíos</span></div>
  </div>

  <h2>Desglose por Proveedor</h2>
  <table>
    <thead>
      <tr><th>Proveedor</th><th>Compras</th><th>Total Invertido</th><th>Gasto Envíos</th><th>Prods Distintos</th><th>Última Compra</th></tr>
    </thead>
    <tbody>
      ${data.por_provider = data.por_proveedor.map(p => `
        <tr>
          <td><strong>${p.nombre}</strong></td>
          <td>${p.num_compras}</td>
          <td>${fmt(p.total_invertido)}</td>
          <td>${fmt(p.total_envios)}</td>
          <td>${p.productos_distintos}</td>
          <td>${p.ultima_compra || '—'}</td>
        </tr>
      `).join('')}
    </tbody>
  </table>

  <h2>Productos más Comprados</h2>
  <table>
    <thead>
      <tr><th>Producto</th><th>Categoría</th><th>Uds Compradas</th><th>Costo Promedio</th><th>Costo Actual</th><th>Variación</th></tr>
    </thead>
    <tbody>
      ${data.productos_mas_comprados.map(p => `
        <tr>
          <td>${p.nombre}</td>
          <td>${p.categoria}</td>
          <td>${p.unidades_compradas}</td>
          <td>${fmt(p.costo_promedio)}</td>
          <td>${fmt(p.costo_actual)}</td>
          <td class="${p.variacion_costo_pct > 0 ? 'neg' : p.variacion_costo_pct < 0 ? 'pos' : ''}">
            ${p.variacion_costo_pct !== null ? `${p.variacion_costo_pct}%` : '—'}
          </td>
        </tr>
      `).join('')}
    </tbody>
  </table>
</body>
</html>`;

    const blob = new Blob([html], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `compras_fika_${desde}_${hasta}.html`;
    a.click();
    toast('Informe de compras exportado 📤');
  } catch (e) { toast('Error exportando: ' + e.message, 'error'); }
}

function setPeriodoTablero(opc) {
  const hoy = new Date();
  const hasta = hoy.toISOString().split('T')[0];
  let desde = hasta;

  // Evitar fechas futuras
  $('tablero-desde').max = hasta;
  $('tablero-hasta').max = hasta;

  if (opc === '7d') {
    const d = new Date();
    d.setDate(d.getDate() - 6);
    desde = d.toISOString().split('T')[0];
  } else if (opc === '30d') {
    const d = new Date();
    d.setDate(d.getDate() - 29);
    desde = d.toISOString().split('T')[0];
  }

  $('tablero-desde').value = desde;
  $('tablero-hasta').value = hasta;
  cargarTablero();
}

async function cargarTablero() {
  const desde = $('tablero-desde').value;
  const hasta = $('tablero-hasta').value;
  if (!desde || !hasta) return toast('Selecciona rango de fechas', 'error');

  try {
    const data = await api('GET', `/api/reportes/tablero?desde=${desde}&hasta=${hasta}`);
    renderTablero(data);
  } catch (e) { toast('Error tablero: ' + e.message, 'error'); }
}

function renderTablero(data) {
  // KPIs
  $('t-ventas').textContent = data.actual.ventas;
  $('t-ingresos').textContent = fmt(data.actual.ingresos);
  $('t-ganancia').textContent = fmt(data.actual.ganancia_estimada);
  $('t-ticket').textContent = fmt(data.actual.ticket_promedio);

  // Variaciones
  renderVariacion('v-ventas', data.variacion.ventas_pct);
  renderVariacion('v-ingresos', data.variacion.ingresos_pct);
  renderVariacion('v-ganancia', data.variacion.ganancia_pct);

  // Métodos de pago
  const metodosDiv = $('tablero-metodos');
  metodosDiv.innerHTML = Object.entries(data.por_metodo).map(([m, d]) => `
    <div style="margin-bottom:12px;">
      <div style="display:flex; justify-content:space-between; font-size:13px; margin-bottom:4px;">
        <span style="text-transform:capitalize;">${m === 'efectivo' ? '💵' : m === 'transferencia' ? '📱' : '💳'} ${m}</span>
        <span style="font-weight:700;">${d.pct}% (${fmt(d.total)})</span>
      </div>
      <div class="report-bar-wrap"><div class="report-bar" style="width:${d.pct}%; background:var(--primary);"></div></div>
    </div>
  `).join('');

  // Top Productos
  const topDiv = $('tablero-top');
  if (!data.top_productos.length) {
    topDiv.innerHTML = '<div class="empty-state">Sin ventas en este periodo</div>';
  } else {
    const maxV = data.top_productos[0].total_vendido || 1;
    topDiv.innerHTML = data.top_productos.map((p, i) => `
      <div class="report-item" style="padding:8px 0; border-bottom:1px solid #eee;">
        <div style="flex:1;">
          <div style="font-weight:600; font-size:14px;">${p.nombre}</div>
          <div class="report-bar-wrap" style="height:6px; margin-top:4px;">
            <div class="report-bar" style="width:${(p.total_vendido / maxV * 100)}%"></div>
          </div>
        </div>
        <div style="text-align:right; min-width:80px;">
          <div style="font-weight:700;">${p.total_vendido} uds</div>
          <div style="font-size:11px; color:var(--muted);">${fmt(p.ingresos)}</div>
        </div>
      </div>
    `).join('');
  }

  // Alertas
  const alertCont = $('tablero-alertas-container');
  if (data.alertas_stock > 0) {
    alertCont.innerHTML = `
      <div class="stat-card danger" onclick="navTo('inventario')" style="cursor:pointer; display:flex; align-items:center; justify-content:space-between; padding:16px;">
        <div>
          <div class="stat-label" style="color:white; opacity:0.9;">Alertas de Stock</div>
          <div class="stat-value" style="font-size:20px;">${data.alertas_stock} productos bajos</div>
        </div>
        <div style="font-size:24px;">⚠️</div>
      </div>
    `;
  } else {
    alertCont.innerHTML = `
      <div class="stat-card success" style="display:flex; align-items:center; justify-content:space-between; padding:16px;">
        <div class="stat-label" style="color:white;">Stock en orden ✅</div>
        <div style="font-size:20px;">👍</div>
      </div>
    `;
  }
}

function renderVariacion(id, pct) {
  const el = $(id);
  if (pct == null) {
    el.innerHTML = '<span style="color:var(--muted);">—</span>';
    return;
  }
  const color = pct >= 0 ? 'var(--success)' : 'var(--danger)';
  const icon = pct >= 0 ? '▲' : '▼';
  el.innerHTML = `<span style="color:${color}; font-weight:700; font-size:11px;">${icon} ${Math.abs(pct)}%</span> <span style="font-size:10px; opacity:0.6;">vs ant.</span>`;
}

function cambiarPeriodo(periodo, btn) {
  document.querySelectorAll('#reporte-detallado-content .period-tab').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  cargarReportes(periodo);
}

async function cargarReportes(periodo) {
  try {
    const [res, sb, mv, sm, proy, marg] = await Promise.all([
      api('GET', `/api/reportes/resumen?periodo=${periodo}`),
      api('GET', '/api/reportes/stock-bajo'),
      api('GET', '/api/reportes/mas-vendidos?limite=8'),
      api('GET', '/api/reportes/sin-movimiento?dias=30'),
      api('GET', '/api/reportes/proyeccion-compras'),
      api('GET', '/api/reportes/margenes-categoria')
    ]);
    
    $('r-ventas').textContent = res.ventas.total_ventas;
    $('r-ingresos').textContent = fmt(res.ventas.ingresos);
    $('r-ganancia').textContent = fmt(res.ganancia_estimada);
    $('r-ticket').textContent = fmt(Math.round(res.ventas.ticket_promedio));

    renderProyeccion(proy);
    renderMargenes(marg);
    renderStockBajo(sb);
    renderMasVendidos(mv);
    renderSinMovimiento(sm);

  } catch (e) { toast('Error reportes: ' + e.message, 'error'); }
}

function renderProyeccion(data) {
  const cont = $('reporte-proyeccion');
  if (!data.length) {
    cont.innerHTML = '<div class="card" style="padding:15px; text-align:center; color:var(--muted); font-size:13px;">Stock suficiente para las próximas 2 semanas ✅</div>';
    return;
  }
  cont.innerHTML = `
    <div class="card" style="padding:0; overflow:hidden;">
      <table class="report-table">
        <thead>
          <tr><th>Producto</th><th>Cobertura</th><th>Sugerencia</th></tr>
        </thead>
        <tbody>
          ${data.map(p => `
            <tr>
              <td><div style="font-weight:700;">${p.nombre}</div><div style="font-size:10px; color:var(--muted);">VPD: ${p.venta_diaria_promedio}</div></td>
              <td style="color:${p.dias_cobertura_restante < 3 ? 'var(--danger)' : 'var(--info)'}; font-weight:700;">${p.dias_cobertura_restante} días</td>
              <td style="text-align:right;"><span class="badge" style="background:var(--primary); color:white; padding:4px 8px;">+${p.cantidad_sugerida}</span></td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>`;
}

function renderMargenes(data) {
  const cont = $('reporte-margenes');
  if (!data.length) { cont.innerHTML = ''; return; }
  cont.innerHTML = `
    <div class="card" style="padding:12px;">
      ${data.map(c => `
        <div style="margin-bottom:12px;">
          <div style="display:flex; justify-content:space-between; font-size:13px; margin-bottom:4px;">
            <span style="font-weight:700;">${c.categoria || 'Sin categoría'}</span>
            <span style="color:var(--success); font-weight:700;">${c.margen_pct}% margen</span>
          </div>
          <div class="report-bar-wrap"><div class="report-bar" style="width:${c.margen_pct}%; background:var(--success);"></div></div>
          <div style="display:flex; justify-content:space-between; font-size:11px; color:var(--muted); margin-top:2px;">
            <span>Ventas: ${fmt(c.ingresos)}</span>
            <span>Ganancia: ${fmt(c.ganancia)}</span>
          </div>
        </div>
      `).join('')}
    </div>`;
}

function renderStockBajo(sb) {
  const sbDiv = $('reporte-stock-bajo');
  if (!sb.length) {
    sbDiv.innerHTML = '<div class="alert-box success"><span class="alert-icon">✅</span><span>Stock en orden.</span></div>';
  } else {
    sbDiv.innerHTML = sb.map(p => {
      const cls = p.stock === 0 ? 'danger' : 'warn'; const ic = p.stock === 0 ? '⛔' : '⚠️';
      const vars = p.variantes_bajas?.length ? `<div style="font-size:12px;margin-top:4px;">${p.variantes_bajas.map(v => `${v.attr1_valor}${v.attr2_valor ? ' /' + v.attr2_valor : ''}: ${v.stock} uds`).join(' | ')}</div>` : '';
      return `<div class="alert-box ${cls}" style="margin-bottom:8px;"><span class="alert-icon">${ic}</span><div><strong>${p.nombre}</strong> — ${p.stock} / mín. ${p.stock_minimo}${vars}</div></div>`;
    }).join('');
  }
}

function renderMasVendidos(mv) {
  const mvDiv = $('reporte-mas-vendidos');
  if (!mv.length) { mvDiv.innerHTML = '<div class="empty-state" style="padding:24px 0"><div class="empty-icon">📊</div><p>Sin datos aún.</p></div>'; return; }
  const maxV = mv[0].total_vendido;
  mvDiv.innerHTML = '<div class="section-title">🏆 Más vendidos</div>' + mv.map((p, i) => `
    <div class="report-item">
      <div class="report-rank ${i === 0 ? 'gold' : i === 1 ? 'silver' : i === 2 ? 'bronze' : ''}">${i + 1}</div>
      <div class="report-info">
        <div class="report-name">${p.nombre}</div>
        <div class="report-bar-wrap"><div class="report-bar" style="width:${(p.total_vendido / maxV * 100).toFixed(0)}%"></div></div>
      </div>
      <div class="report-vals">
        <div class="report-qty">${p.total_vendido} uds</div>
        <div class="report-income">${fmt(p.ingresos_totales)}</div>
      </div>
    </div>`).join('');
}

function renderSinMovimiento(productos) {
  const cont = $('reporte-sin-movimiento');
  if (!cont) return;
  if (!productos || !productos.length) {
    cont.innerHTML = '<div class="card" style="padding:20px; text-align:center; color:var(--muted);">No hay productos estancados ✅</div>';
    return;
  }
  cont.innerHTML = `
    <div class="card" style="padding:0; overflow:hidden;">
      <table class="report-table">
        <thead>
          <tr><th>Producto</th><th>Stock</th><th>Último mov.</th></tr>
        </thead>
        <tbody>
          ${productos.map(p => `
            <tr>
              <td><div style="font-weight:700;">${p.nombre}</div><div style="font-size:10px; color:var(--muted);">${p.categoria}</div></td>
              <td style="text-align:center;">${p.stock}</td>
              <td style="color:var(--danger); font-weight:700; text-align:right;">${p.ultimo_movimiento}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>`;
}

// ═══════════════════════════════════════════
// EXPORTACIÓN A CSV
// ═══════════════════════════════════════════
async function exportarTodoCSV() {
  try {
    const data = await api('GET', '/api/reportes/exportar-full');
    
    // 1. Exportar Movimientos
    let csvMov = 'ID,Tipo,Motivo,Fecha,Producto,Categoria,Cantidad,Stock_Antes,Stock_Despues\n';
    data.movimientos.forEach(m => {
      csvMov += `${m.id},${m.tipo},"${m.motivo}",${m.created_at},"${m.producto}","${m.categoria}",${m.cantidad},${m.stock_antes},${m.stock_despues}\n`;
    });
    descargarArchivo(csvMov, `NESKO_Movimientos_${new Date().toISOString().split('T')[0]}.csv`);

    // 2. Exportar Inventario
    let csvInv = 'ID,Nombre,Categoria,Stock,Costo,Precio,Stock_Minimo\n';
    data.inventario.forEach(i => {
      csvInv += `${i.id},"${i.nombre}","${i.categoria}",${i.stock},${i.costo},${i.precio},${i.stock_minimo}\n`;
    });
    setTimeout(() => {
      descargarArchivo(csvInv, `NESKO_Inventario_${new Date().toISOString().split('T')[0]}.csv`);
    }, 500);
    
    toast('Archivos CSV generados correctamente 📄');
  } catch (e) { toast('Error exportando: ' + e.message, 'error'); }
}

function descargarArchivo(contenido, nombre) {
  const blob = new Blob([contenido], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement("a");
  const url = URL.createObjectURL(blob);
  link.setAttribute("href", url);
  link.setAttribute("download", nombre);
  link.style.visibility = 'hidden';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}
async function exportarTableroHTML() {
  const desde = $('tablero-desde').value;
  const hasta = $('tablero-hasta').value;
  try {
    const data = await api('GET', `/api/reportes/tablero?desde=${desde}&hasta=${hasta}`);
    
    const html = `
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Tablero Fika — ${desde} a ${hasta}</title>
<style>
  body { font-family: sans-serif; background: #f4f7f6; color: #333; padding: 20px; }
  .card { background: white; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; }
  .kpi { text-align: center; padding: 15px; border-radius: 8px; color: white; }
  .kpi-label { font-size: 12px; opacity: 0.9; text-transform: uppercase; }
  .kpi-value { font-size: 24px; font-weight: bold; margin: 5px 0; }
  .primary { background: #E8821A; }
  .success { background: #2D9B5E; }
  .warn { background: #F59E0B; }
  .info { background: #3B82F6; }
  .bar-wrap { background: #eee; border-radius: 4px; height: 8px; margin-top: 5px; }
  .bar { height: 100%; border-radius: 4px; background: #E8821A; }
  h2 { font-size: 18px; margin-top: 0; border-bottom: 1px solid #eee; padding-bottom: 10px; }
  table { width: 100%; border-collapse: collapse; }
  td { padding: 8px 0; border-bottom: 1px solid #eee; }
</style>
</head>
<body>
  <h1>🏪 Tablero de Control — Fika</h1>
  <p>Periodo: <strong>${desde}</strong> al <strong>${hasta}</strong></p>
  
  <div class="grid">
    <div class="kpi primary"><div class="kpi-label">Ventas</div><div class="kpi-value">${data.actual.ventas}</div></div>
    <div class="kpi success"><div class="kpi-label">Ingresos</div><div class="kpi-value">${fmt(data.actual.ingresos)}</div></div>
    <div class="kpi warn"><div class="kpi-label">Ganancia</div><div class="kpi-value">${fmt(data.actual.ganancia_estimada)}</div></div>
    <div class="kpi info"><div class="kpi-label">Ticket Prom.</div><div class="kpi-value">${fmt(data.actual.ticket_promedio)}</div></div>
  </div>

  <div class="card">
    <h2>💳 Métodos de Pago</h2>
    ${Object.entries(data.por_metodo).map(([m, d]) => `
      <div style="margin-bottom:10px;">
        <div style="display:flex; justify-content:space-between;">
          <span>${m.toUpperCase()}</span><span>${d.pct}% (${fmt(d.total)})</span>
        </div>
        <div class="bar-wrap"><div class="bar" style="width:${d.pct}%"></div></div>
      </div>
    `).join('')}
  </div>

  <div class="card">
    <h2>🏆 Top 5 Productos</h2>
    <table>
      ${data.top_productos.map(p => `
        <tr>
          <td><strong>${p.nombre}</strong></td>
          <td style="text-align:right;">${p.total_vendido} uds<br><small>${fmt(p.ingresos)}</small></td>
        </tr>
      `).join('')}
    </table>
  </div>
  
  <div style="text-align:center; font-size:12px; color:#666;">Generado el ${new Date().toLocaleString()}</div>
</body>
</html>`;

    const blob = new Blob([html], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `tablero_fika_${desde}_${hasta}.html`;
    a.click();
    toast('Tablero exportado 📤');
  } catch (e) { toast('Error exportando: ' + e.message, 'error'); }
}

async function exportarRentabilidadHTML() {
  const desde = $('tablero-desde').value;
  const hasta = $('tablero-hasta').value;
  try {
    const data = await api('GET', `/api/reportes/rentabilidad?desde=${desde}&hasta=${hasta}`);
    const res = data.resumen;
    
    const html = `
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Reporte de Rentabilidad — ${desde} a ${hasta}</title>
<style>
  body { font-family: sans-serif; padding: 30px; color: #333; }
  .resumen { display: flex; gap: 20px; margin-bottom: 30px; background: #f9f9f9; padding: 20px; border-radius: 8px; }
  .stat { flex: 1; text-align: center; }
  .val { font-size: 20px; font-weight: bold; }
  table { width: 100%; border-collapse: collapse; margin-top: 20px; }
  th { background: #eee; text-align: left; padding: 10px; }
  td { padding: 10px; border-bottom: 1px solid #eee; }
  .pos { color: green; font-weight: bold; }
</style>
</head>
<body>
  <h1>📈 Informe de Rentabilidad — Fika</h1>
  <p>Periodo: <strong>${desde}</strong> al <strong>${hasta}</strong></p>

  <div class="resumen">
    <div class="stat"><div>Ingresos</div><div class="val">${fmt(res.ingresos)}</div></div>
    <div class="stat"><div>Costo Mercadería</div><div class="val">${fmt(res.costo_mercaderia)}</div></div>
    <div class="stat"><div>Costo Envíos</div><div class="val">${fmt(res.costo_envios)}</div></div>
    <div class="stat"><div>Ganancia Neta</div><div class="val pos">${fmt(res.ganancia)}</div></div>
    <div class="stat"><div>Margen</div><div class="val pos">${res.margen_pct}%</div></div>
  </div>

  <h2>Detalle por Producto</h2>
  <table>
    <thead>
      <tr><th>Producto</th><th>Categoría</th><th>Vendido</th><th>Ingresos</th><th>Costo Total</th><th>Ganancia</th><th>Margen</th></tr>
    </thead>
    <tbody>
      ${data.por_producto.map(p => `
        <tr>
          <td>${p.nombre}</td>
          <td>${p.categoria}</td>
          <td>${p.unidades_vendidas}</td>
          <td>${fmt(p.ingresos)}</td>
          <td>${fmt(p.costo_total)}</td>
          <td class="pos">${fmt(p.ganancia)}</td>
          <td>${p.margen_pct}%</td>
        </tr>
      `).join('')}
    </tbody>
  </table>
</body>
</html>`;

    const blob = new Blob([html], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `rentabilidad_fika_${desde}_${hasta}.html`;
    a.click();
    toast('Informe de rentabilidad exportado 📤');
  } catch (e) { toast('Error exportando: ' + e.message, 'error'); }
}

async function exportarCategoriasHTML() {
  const desde = $('tablero-desde').value;
  const hasta = $('tablero-hasta').value;
  const seleccionadas = Array.from(document.querySelectorAll('.cat-check:checked')).map(cb => cb.value).join(',');
  
  try {
    const data = await api('GET', `/api/reportes/categorias?desde=${desde}&hasta=${hasta}${seleccionadas ? `&categorias=${seleccionadas}` : ''}`);
    
    const html = `
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Rentabilidad por Categoría — ${desde} a ${hasta}</title>
<style>
  body { font-family: sans-serif; padding: 30px; color: #333; }
  table { width: 100%; border-collapse: collapse; margin-top: 20px; }
  th { background: #f4f4f4; text-align: left; padding: 12px; border-bottom: 2px solid #ddd; }
  td { padding: 12px; border-bottom: 1px solid #eee; }
  .total-row { font-weight: bold; background: #fafafa; }
</style>
</head>
<body>
  <h1>📊 Rentabilidad por Categoría — Fika</h1>
  <p>Periodo: <strong>${desde}</strong> al <strong>${hasta}</strong></p>

  <table>
    <thead>
      <tr><th>Categoría</th><th>Productos</th><th>Vendido</th><th>Ingresos</th><th>Ganancia</th><th>Margen</th><th>Top Producto</th></tr>
    </thead>
    <tbody>
      ${data.categorias.map(c => `
        <tr>
          <td><strong>${c.nombre}</strong></td>
          <td>${c.productos_activos}</td>
          <td>${c.unidades_vendidas}</td>
          <td>${fmt(c.ingresos)}</td>
          <td>${fmt(c.ganancia)}</td>
          <td>${c.margen_pct}%</td>
          <td>${c.top_producto}</td>
        </tr>
      `).join('')}
      <tr class="total-row">
        <td>${data.sin_categoria.nombre}</td>
        <td>${data.sin_categoria.productos_activos}</td>
        <td>${data.sin_categoria.unidades_vendidas}</td>
        <td>${fmt(data.sin_categoria.ingresos)}</td>
        <td>${fmt(data.sin_categoria.ganancia)}</td>
        <td>${data.sin_categoria.margen_pct}%</td>
        <td>${data.sin_categoria.top_producto}</td>
      </tr>
    </tbody>
  </table>
</body>
</html>`;

    const blob = new Blob([html], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `categorias_fika_${desde}_${hasta}.html`;
    a.click();
    toast('Informe por categoría exportado 📤');
  } catch (e) { toast('Error exportando: ' + e.message, 'error'); }
}

async function exportarInventarioHTML() {
  const corte = $('inv-fecha-corte').value;
  try {
    const data = await api('GET', `/api/reportes/inventario?fecha_corte=${corte}`);
    const res = data.resumen;
    
    const html = `
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Inventario y Stock — ${corte}</title>
<style>
  body { font-family: sans-serif; padding: 30px; color: #333; line-height: 1.5; }
  .resumen { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 30px; }
  .stat { background: #f9f9f9; padding: 15px; border-radius: 8px; text-align: center; border: 1px solid #eee; }
  .val { font-size: 20px; font-weight: bold; display: block; margin-bottom: 5px; }
  .lab { font-size: 11px; color: #777; text-transform: uppercase; }
  table { width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 13px; }
  th { background: #eee; text-align: left; padding: 10px; border-bottom: 2px solid #ddd; }
  td { padding: 10px; border-bottom: 1px solid #eee; }
</style>
</head>
<body>
  <h1>📦 Reporte de Inventario y Stock — Fika</h1>
  <p>Fecha de corte: <strong>${corte}</strong></p>

  <div class="resumen">
    <div class="stat"><span class="val">${fmt(res.valor_bodega)}</span><span class="lab">Valor Bodega</span></div>
    <div class="stat"><span class="val">${res.total_productos}</span><span class="lab">Productos</span></div>
    <div class="stat"><span class="val">${res.agotados}</span><span class="lab">Agotados</span></div>
    <div class="stat"><span class="val">${res.bajo_minimo}</span><span class="lab">Bajo Mínimo</span></div>
  </div>

  <h2>Listado de Stock y Rotación</h2>
  <table>
    <thead>
      <tr><th>Producto</th><th>Categoría</th><th>Stock</th><th>Costo</th><th>Valor Bodega</th><th>Última Venta</th></tr>
    </thead>
    <tbody>
      ${data.listado_completo.map(p => `
        <tr>
          <td>${p.nombre}</td>
          <td>${p.categoria}</td>
          <td>${p.stock}</td>
          <td>${fmt(p.costo)}</td>
          <td>${fmt(p.valor_bodega)}</td>
          <td>${p.ultima_venta || '—'}</td>
        </tr>
      `).join('')}
    </tbody>
  </table>
</body>
</html>`;

    const blob = new Blob([html], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `inventario_fika_${corte}.html`;
    a.click();
    toast('Inventario exportado 📤');
  } catch (e) { toast('Error exportando: ' + e.message, 'error'); }
}

async function exportarComprasHTML() {
  const desde = $('tablero-desde').value;
  const hasta = $('tablero-hasta').value;
  try {
    const data = await api('GET', `/api/reportes/compras?desde=${desde}&hasta=${hasta}`);
    const res = data.resumen;
    
    const html = `
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Reporte de Compras — ${desde} a ${hasta}</title>
<style>
  body { font-family: sans-serif; padding: 30px; color: #333; line-height: 1.5; }
  .resumen { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 30px; }
  .stat { background: #f4f7fa; padding: 15px; border-radius: 8px; text-align: center; border: 1px solid #e1e8ed; }
  .val { font-size: 20px; font-weight: bold; display: block; margin-bottom: 5px; color: #1B3A6B; }
  .lab { font-size: 11px; color: #777; text-transform: uppercase; font-weight: bold; }
  table { width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 13px; }
  th { background: #f8fafc; text-align: left; padding: 12px; border-bottom: 2px solid #e2e8f0; }
  td { padding: 12px; border-bottom: 1px solid #edf2f7; }
  .pos { color: #2D9B5E; }
  .neg { color: #d63b3b; }
</style>
</head>
<body>
  <h1>📊 Informe de Compras y Proveedores — Fika</h1>
  <p>Periodo: <strong>${desde}</strong> al <strong>${hasta}</strong></p>

  <div class="resumen">
    <div class="stat"><span class="val">${fmt(res.total_invertido)}</span><span class="lab">Total Invertido</span></div>
    <div class="stat"><span class="val">${res.num_compras}</span><span class="lab">Compras</span></div>
    <div class="stat"><span class="val">${res.num_proveedores}</span><span class="lab">Proveedores</span></div>
    <div class="stat"><span class="val">${fmt(res.total_envios)}</span><span class="lab">Gasto Envíos</span></div>
  </div>

  <h2>Desglose por Proveedor</h2>
  <table>
    <thead>
      <tr><th>Proveedor</th><th>Compras</th><th>Total Invertido</th><th>Gasto Envíos</th><th>Prods Distintos</th><th>Última Compra</th></tr>
    </thead>
    <tbody>
      ${data.por_proveedor.map(p => `
        <tr>
          <td><strong>${p.nombre}</strong></td>
          <td>${p.num_compras}</td>
          <td>${fmt(p.total_invertido)}</td>
          <td>${fmt(p.total_envios)}</td>
          <td>${p.productos_distintos}</td>
          <td>${p.ultima_compra || '—'}</td>
        </tr>
      `).join('')}
    </tbody>
  </table>

  <h2>Productos más Comprados</h2>
  <table>
    <thead>
      <tr><th>Producto</th><th>Categoría</th><th>Uds Compradas</th><th>Costo Promedio</th><th>Costo Actual</th><th>Variación</th></tr>
    </thead>
    <tbody>
      ${data.productos_mas_comprados.map(p => `
        <tr>
          <td>${p.nombre}</td>
          <td>${p.categoria}</td>
          <td>${p.unidades_compradas}</td>
          <td>${fmt(p.costo_promedio)}</td>
          <td>${fmt(p.costo_actual)}</td>
          <td class="${p.variacion_costo_pct > 0 ? 'neg' : p.variacion_costo_pct < 0 ? 'pos' : ''}">
            ${p.variacion_costo_pct !== null ? `${p.variacion_costo_pct}%` : '—'}
          </td>
        </tr>
      `).join('')}
    </tbody>
  </table>
</body>
</html>`;

    const blob = new Blob([html], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `compras_fika_${desde}_${hasta}.html`;
    a.click();
    toast('Informe de compras exportado 📤');
  } catch (e) { toast('Error exportando: ' + e.message, 'error'); }
}

async function cargarReporteProductos() {
  const cat = $('rep-prod-cat').value;
  const estado = $('rep-prod-estado').value;
  const bajo = $('rep-prod-bajo').checked;
  
  try {
    const data = await api('GET', `/api/reportes/productos?estado=${estado}${cat ? `&categoria=${cat}` : ''}${bajo ? '&con_stock_bajo=true' : ''}`);
    reporteProductosCache = data;
    renderReporteProductos(data);
    
    // Poblar dropdown de categorías si está vacío
    const sel = $('rep-prod-cat');
    if (sel.options.length <= 1) {
      const cats = await api('GET', '/api/categorias');
      sel.innerHTML = '<option value="">Todas</option>' + cats.map(c => `<option value="${c}">${c}</option>`).join('');
      sel.value = cat;
    }
  } catch (e) { toast('Error catálogo: ' + e.message, 'error'); }
}

function renderReporteProductos(lista) {
  const body = $('rep-productos-body');
  $('rep-prod-count').textContent = `Mostrando ${lista.length} productos`;
  
  body.innerHTML = lista.map(p => {
    const colorMargen = p.margen_pct >= 30 ? 'var(--success)' : p.margen_pct >= 15 ? '#E8821A' : 'var(--danger)';
    const colorStock = p.stock_estado === 'ok' ? 'var(--success)' : p.stock_estado === 'bajo' ? '#E8821A' : 'var(--danger)';
    const opacity = p.activo ? '1' : '0.5';
    const greyScale = p.activo ? '' : 'filter: grayscale(1);';
    
    return `
      <tr style="opacity: ${opacity}; ${greyScale}">
        <td>
          <div style="font-weight:700;">${p.nombre}</div>
          <div style="font-size:10px; color:var(--muted);">${p.categoria}</div>
        </td>
        <td style="text-align:right;">${fmt(p.precio)}</td>
        <td style="text-align:right;">${fmt(p.costo_real)}</td>
        <td style="text-align:right; font-weight:700; color:${colorMargen};">${p.margen_pct}%</td>
        <td style="text-align:center;">${p.stock}</td>
        <td style="text-align:center;"><span style="color:${colorStock}; font-size:16px;">●</span></td>
        <td style="color:var(--muted);">${p.codigo_proveedor || '—'}</td>
        <td style="text-align:center;">
          ${p.tiene_variantes ? `<button class="btn btn-sm btn-outline" onclick="toggleVariantesRep(${p.id})">Variantes (${p.num_variantes})</button>` : '—'}
        </td>
      </tr>
      <tr id="rep-vars-${p.id}" style="display:none; background:#fafafa;">
        <td colspan="8" id="rep-vars-cont-${p.id}" style="padding:0;">
          <div class="spinner" style="margin:10px auto;"></div>
        </td>
      </tr>
    `;
  }).join('');
}

function filtrarRepProductos() {
  const q = $('search-rep-productos').value.toLowerCase();
  const filtered = reporteProductosCache.filter(p => 
    p.nombre.toLowerCase().includes(q) || 
    (p.codigo_proveedor && p.codigo_proveedor.toLowerCase().includes(q))
  );
  renderReporteProductos(filtered);
}

async function toggleVariantesRep(id) {
  const row = $(`rep-vars-${id}`);
  if (row.style.display === 'table-row') {
    row.style.display = 'none';
    return;
  }
  row.style.display = 'table-row';
  const cont = $(`rep-vars-cont-${id}`);
  
  try {
    const vars = await api('GET', `/api/reportes/productos/${id}/variantes`);
    cont.innerHTML = `
      <div style="padding:10px 20px;">
        <table style="width:100%; font-size:11px; border-collapse:collapse;">
          <thead>
            <tr style="border-bottom:1px solid #ddd; color:var(--muted);">
              <th style="text-align:left;">Atributos</th>
              <th style="text-align:center;">Stock</th>
              <th style="text-align:center;">Mínimo</th>
              <th>Código Barras</th>
            </tr>
          </thead>
          <tbody>
            ${vars.map(v => `
              <tr>
                <td>${v.attr1_valor} ${v.attr2_valor ? '/ '+v.attr2_valor : ''}</td>
                <td style="text-align:center; font-weight:700;">${v.stock}</td>
                <td style="text-align:center; color:#999;">${v.stock_minimo}</td>
                <td style="color:var(--info);">${v.codigo_barras || '—'}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;
  } catch (e) { cont.innerHTML = '<div style="padding:10px;">Error cargando variantes</div>'; }
}

async function exportarProductosHTML() {
  const cat = $('rep-prod-cat').value;
  const estado = $('rep-prod-estado').value;
  const bajo = $('rep-prod-bajo').checked;
  
  try {
    const data = reporteProductosCache;
    
    const html = `
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Catálogo de Productos — Fika</title>
<style>
  body { font-family: sans-serif; padding: 30px; color: #333; line-height: 1.5; }
  table { width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 12px; }
  th { background: #f1f5f9; text-align: left; padding: 10px; border-bottom: 2px solid #cbd5e1; }
  td { padding: 10px; border-bottom: 1px solid #e2e8f0; }
  .bajo { color: #E8821A; font-weight: bold; }
  .agotado { color: #d63b3b; font-weight: bold; }
  .inactive { opacity: 0.5; }
</style>
</head>
<body>
  <h1>📋 Catálogo de Productos — Fika</h1>
  <p>Filtros: Categoría: <strong>${cat || 'Todas'}</strong> | Estado: <strong>${estado}</strong> | Solo stock bajo: <strong>${bajo ? 'Sí' : 'No'}</strong></p>

  <table>
    <thead>
      <tr>
        <th>Producto</th>
        <th>Categoría</th>
        <th>Precio</th>
        <th>Costo Real</th>
        <th>Margen</th>
        <th>Stock</th>
        <th>Estado</th>
        <th>Código Prov.</th>
      </tr>
    </thead>
    <tbody>
      ${data.map(p => `
        <tr class="${p.activo ? '' : 'inactive'}">
          <td><strong>${p.nombre}</strong></td>
          <td>${p.categoria}</td>
          <td>${fmt(p.precio)}</td>
          <td>${fmt(p.costo_real)}</td>
          <td>${p.margen_pct}%</td>
          <td class="${p.stock_estado === 'ok' ? '' : p.stock_estado}">${p.stock}</td>
          <td>${p.stock_estado.toUpperCase()}</td>
          <td>${p.codigo_proveedor || '—'}</td>
        </tr>
      `).join('')}
    </tbody>
  </table>
</body>
</html>`;

    const blob = new Blob([html], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `catalogo_fika_${new Date().toISOString().split('T')[0]}.html`;
    a.click();
    toast('Catálogo exportado 📤');
  } catch (e) { toast('Error exportando: ' + e.message, 'error'); }
}
