// ═══════════════════════════════════════════
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
      const cancelada = v.estado === 'cancelled';
      const estadoBadge = cancelada
        ? '<span style="background:#FEE2E2;color:#991B1B;padding:2px 8px;border-radius:6px;font-size:11px;font-weight:700;">❌ Cancelada</span>'
        : '<span style="background:#DCFCE7;color:#166534;padding:2px 8px;border-radius:6px;font-size:11px;font-weight:700;">✅ Activa</span>';
      const btnCancelar = !cancelada
        ? `<button class="btn-icon" title="Cancelar venta" onclick="openModalCancelar('venta',${v.id},'#${String(v.id).padStart(4,'0')}','${fmt(v.total)}')" style="font-size:14px;">🗑️</button>`
        : '';
      return `
    <div class="sale-card" style="${cancelada ? 'opacity:0.55;' : ''}">
      <div class="sale-header">
        <div><div class="sale-id">#${String(v.id).padStart(4, '0')}</div><div class="sale-date">${fecha}</div></div>
        <div style="text-align:right;">
          <div class="sale-total">${fmt(v.total)}</div>
          <span class="sale-method">${mic[v.metodo_pago] || ''} ${escapeHtml(v.metodo_pago)}</span>
        </div>
      </div>
      <div class="sale-items-list">📦 ${itemsTxt}</div>
      <div style="display:flex;justify-content:space-between;align-items:center;margin-top:8px;">
        ${estadoBadge}
        ${btnCancelar}
      </div>
    </div>`;
    }).join('');
  } catch (e) { $('lista-ventas').innerHTML = `<div class="alert-box danger"><span>${e.message}</span></div>`; }
}

// ═══════════════════════════════════════════
// CANCELAR VENTA
// ═══════════════════════════════════════════
function openModalCancelar(tipo, id, ref, total) {
  $('cancelar-tipo').value = tipo;
  $('cancelar-id').value = id;
  $('cancelar-mensaje').innerHTML = `¿Cancelar ${tipo} <strong>${ref}</strong> por <strong>${total}</strong>? Se revertirá el stock automáticamente.`;
  $('modal-cancelar').classList.add('open');
}

async function ejecutarCancelacion() {
  const tipo = $('cancelar-tipo').value;
  const id = parseInt($('cancelar-id').value);
  const endpoint = tipo === 'venta' ? `/api/ventas/${id}/cancelar` : `/api/compras/${id}/cancelar`;
  try {
    await api('POST', endpoint);
    toast(`${tipo === 'venta' ? 'Venta' : 'Compra'} cancelada. Stock revertido ✅`);
    cerrarModales();
    if (tipo === 'venta') cargarHistorial();
    else cargarCompras();
  } catch (e) { toast(e.message, 'error'); }
}

