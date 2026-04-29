// ═══════════════════════════════════════════
// REPORTES (NIVEL 3 - INTELIGENCIA)
// ═══════════════════════════════════════════
function cambiarPeriodo(periodo, btn) {
  document.querySelectorAll('.period-tab').forEach(b => b.classList.remove('active'));
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
