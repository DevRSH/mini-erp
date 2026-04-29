    // HISTORIAL
    // ═══════════════════════════════════════════
    async function cargarHistorial() {
      $('lista-ventas').innerHTML = '<div class="spinner"></div>';
      try {
        const ventas = await api('GET', '/api/ventas?limite=50');
        if (!ventas.length) { $('lista-ventas').innerHTML = '<div class="empty-state"><div class="empty-icon">📋</div><p>Sin ventas aún.</p></div>'; return; }
        const mic = { efectivo: '💵', transferencia: '📱', tarjeta: '💳' };
        $('lista-ventas').innerHTML = ventas.map(v => {
          const fecha = new Date(v.created_at).toLocaleString('es-CL', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
          const itemsTxt = v.items.map(i => {
            const attr1 = escapeHtml(i.attr1_valor);
            const attr2 = escapeHtml(i.attr2_valor);
            const etiq = i.attr2_valor ? ` (${attr1}/${attr2})` : i.attr1_valor ? ` (${attr1})` : '';
            return `${escapeHtml(i.nombre)}${etiq} ×${i.cantidad}`;
          }).join(', ');
          return `
        <div class="sale-card">
          <div class="sale-header">
            <div><div class="sale-id">#${String(v.id).padStart(4, '0')}</div><div class="sale-date">${fecha}</div></div>
            <div style="text-align:right;">
              <div class="sale-total">${fmt(v.total)}</div>
              <span class="sale-method">${mic[v.metodo_pago] || ''} ${escapeHtml(v.metodo_pago)}</span>
            </div>
          </div>
          <div class="sale-items-list">📦 ${itemsTxt}</div>
        </div>`;
        }).join('');
      } catch (e) { $('lista-ventas').innerHTML = `<div class="alert-box danger"><span>${e.message}</span></div>`; }
    }

    // ═══════════════════════════════════════════
