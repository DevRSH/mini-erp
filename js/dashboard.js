// ═══════════════════════════════════════════
// DASHBOARD
// ═══════════════════════════════════════════
async function cargarDashboard() {
  try {
    const [res, top, sb] = await Promise.all([
      api('GET', '/api/reportes/resumen?periodo=hoy'),
      api('GET', '/api/reportes/mas-vendidos?limite=5'),
      api('GET', '/api/reportes/stock-bajo')
    ]);
    $('dash-ventas').textContent = res.ventas.total_ventas;
    $('dash-ingresos').textContent = fmt(res.ventas.ingresos);
    $('dash-ganancia').textContent = fmt(res.ganancia_estimada);
    $('dash-alertas').textContent = res.alertas_stock;
    const badge = $('alert-badge');
    if (res.alertas_stock > 0) { badge.textContent = `⚠️ ${res.alertas_stock}`; badge.classList.add('visible'); }
    else badge.classList.remove('visible');
    const hora = new Date().toLocaleTimeString('es-CL', { hour: '2-digit', minute: '2-digit' });
    $('header-sub').textContent = `Actualizado ${hora}`;
    $('dash-alert-list').innerHTML = sb.length > 0
      ? `<div class="alert-box warn"><span class="alert-icon">⚠️</span><span><strong>${sb.length} producto${sb.length > 1 ? 's' : ''}</strong> con stock bajo. Revisa Reportes.</span></div>`
      : `<div class="alert-box success"><span class="alert-icon">✅</span><span>Stock en buen estado.</span></div>`;
    const topDiv = $('dash-top-productos');
    if (!top.length) { topDiv.innerHTML = '<p style="color:var(--muted);text-align:center;padding:16px">Sin ventas aún.</p>'; return; }
    const max = top[0].total_vendido;
    topDiv.innerHTML = top.map((p, i) => `
  <div class="report-item">
    <div class="report-rank ${i === 0 ? 'gold' : i === 1 ? 'silver' : i === 2 ? 'bronze' : ''}">${i + 1}</div>
    <div class="report-info">
      <div class="report-name">${p.nombre}</div>
      <div class="report-bar-wrap"><div class="report-bar" style="width:${(p.total_vendido / max * 100).toFixed(0)}%"></div></div>
    </div>
    <div class="report-vals">
      <div class="report-qty">${p.total_vendido} uds</div>
      <div class="report-income">${fmt(p.ingresos_totales)}</div>
    </div>
  </div>`).join('');
    topDiv.className = 'card';
  } catch (e) { toast('Error dashboard: ' + e.message, 'error'); }
}
