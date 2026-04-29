    // REPORTES
    // ═══════════════════════════════════════════
    function cambiarPeriodo(periodo, btn) {
      document.querySelectorAll('.period-tab').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      cargarReportes(periodo);
    }

    async function cargarReportes(periodo) {
      try {
        const [res, sb, mv] = await Promise.all([
          api('GET', `/api/reportes/resumen?periodo=${periodo}`),
          api('GET', '/api/reportes/stock-bajo'),
          api('GET', '/api/reportes/mas-vendidos?limite=8'),
        ]);
        $('r-ventas').textContent = res.ventas.total_ventas;
        $('r-ingresos').textContent = fmt(res.ventas.ingresos);
        $('r-ganancia').textContent = fmt(res.ganancia_estimada);
        $('r-ticket').textContent = fmt(Math.round(res.ventas.ticket_promedio));

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

        const mvDiv = $('reporte-mas-vendidos');
        if (!mv.length) { mvDiv.innerHTML = '<div class="empty-state" style="padding:24px 0"><div class="empty-icon">📊</div><p>Sin datos aún.</p></div>'; return; }
        const maxV = mv[0].total_vendido;
        mvDiv.innerHTML = mv.map((p, i) => `
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
      } catch (e) { toast('Error reportes: ' + e.message, 'error'); }
    }

    // SPRINT 5 — EXPORTACIÓN
    // ═══════════════════════════════════════════
    function exportarReporte() {
      const periodo = document.querySelector('.period-tab.active')?.textContent?.trim();
      const mapa = { 'Hoy': 'hoy', '7 días': 'semana', 'Este mes': 'mes' };
      const p = mapa[periodo] || 'mes';
      const btn = $('btn-exportar');
      btn.disabled = true;
      btn.textContent = '⏳ Generando...';
      const link = document.createElement('a');
      link.href = `/api/exportar/reporte?periodo=${p}`;
      link.download = `reporte_${p}.html`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      setTimeout(() => {
        btn.disabled = false;
        btn.textContent = '📤 Exportar reporte para compartir';
        toast('Reporte descargado. ¡Comparte el archivo por WhatsApp! 📱');
      }, 1200);
    }

  

    // Alias para cargarVentas
    window.cargarVentas = cargarHistorial;
