// ═══════════════════════════════════════════
// REPORTES (NIVEL 3 - INTELIGENCIA)
// ═══════════════════════════════════════════
function cambiarSeccionReporte(seccion, btn) {
  document.querySelectorAll('#page-reportes > .period-tabs .period-tab').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  
  if (seccion === 'tablero') {
    $('reporte-tablero-content').style.display = 'block';
    $('filtros-tablero').style.display = 'block';
    $('reporte-detallado-content').style.display = 'none';
    if (!$('tablero-desde').value) setPeriodoTablero('7d');
    else cargarTablero();
  } else {
    $('reporte-tablero-content').style.display = 'none';
    $('filtros-tablero').style.display = 'none';
    $('reporte-detallado-content').style.display = 'block';
    cargarReportes('hoy');
  }
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
