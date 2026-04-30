async function confirmarCompra() {
  if (!itemsCompra.length) { toast('Agrega al menos un producto', 'error'); return; }
  for (const [i, item] of itemsCompra.entries()) {
    if (!item.producto_id) { toast(`Selecciona el producto en ítem ${i + 1}`, 'error'); return; }
    if (!item.cantidad || item.cantidad < 1) { toast(`Cantidad inválida en ítem ${i + 1}`, 'error'); return; }
  }
  
  const provId = parseInt($('compra-proveedor-id').value) || null;
  const provNuevo = $('compra-proveedor-nuevo').value.trim();
  
  if (!provId && !provNuevo) { toast('Seleccione un proveedor o ingrese uno nuevo', 'error'); return; }
  
  try {
    const res = await api('POST', '/api/compras', {
      proveedor_id: provId,
      proveedor: provNuevo || 'Sin nombre',
      notas: $('compra-notas').value || '',
      costo_envio: parseFloat($('compra-envio').value) || 0,
      actualizar_costo: $('compra-actualizar-costo').checked,
      items: itemsCompra.map(i => ({
        producto_id: i.producto_id,
        variante_id: i.variante_id || null,
        cantidad: i.cantidad,
        costo_unitario: i.costo_unitario || 0,
      }))
    });
    toast(`Compra #${res.compra_id} registrada — ${fmt(res.total)} ✅`);
    cerrarModales();
    cargarInventario();
    cargarCompras();
  } catch (e) { toast(e.message, 'error'); }
}

async function cargarCompras() {
  const cont = $('lista-compras');
  if (!cont) return;
  cont.innerHTML = '<div class="spinner"></div>';
  cargarProveedores(); 
  try {
    const compras = await api('GET', '/api/compras?limite=50');
    if (!compras.length) {
      cont.innerHTML = '<div class="empty-state"><div class="empty-icon">🚚</div><p>Sin compras registradas.</p></div>';
      return;
    }
    cont.innerHTML = compras.map(c => {
      const fecha = new Date(c.created_at).toLocaleString('es-CL', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
      const itemsTxt = c.items.map(i => {
        const attr1 = escapeHtml(i.attr1_valor);
        const attr2 = escapeHtml(i.attr2_valor);
        const etiq = i.attr2_valor ? ` (${attr1}/${attr2})` : i.attr1_valor ? ` (${attr1})` : '';
        return `${escapeHtml(i.nombre)}${etiq} ×${i.cantidad}`;
      }).join(', ');
      const provNombre = c.proveedor_nombre || c.proveedor || 'Sin nombre';
      const cancelada = c.estado === 'cancelled';
      const estadoBadge = cancelada
        ? '<span style="background:#FEE2E2;color:#991B1B;padding:2px 8px;border-radius:6px;font-size:11px;font-weight:700;">❌ Cancelada</span>'
        : '<span style="background:#DCFCE7;color:#166534;padding:2px 8px;border-radius:6px;font-size:11px;font-weight:700;">✅ Activa</span>';
      const btnCancelar = !cancelada
        ? `<button class="btn-icon" title="Cancelar compra" onclick="openModalCancelar('compra',${c.id},'#${String(c.id).padStart(4,'0')}','${fmt(c.total)}')" style="font-size:14px;">🗑️</button>`
        : '';
      return `
    <div class="sale-card" style="${cancelada ? 'opacity:0.55;' : ''}">
      <div class="sale-header">
        <div>
          <div class="sale-id">#${String(c.id).padStart(4, '0')} — ${escapeHtml(provNombre)}</div>
          <div class="sale-date">${fecha}</div>
        </div>
        <div style="text-align:right;">
          <div class="sale-total" style="color:var(--primary);">${fmt(c.total)}</div>
          ${c.costo_envio > 0 ? `<span class="sale-method">🚚 envío ${fmt(c.costo_envio)}</span>` : ''}
        </div>
      </div>
      <div class="sale-items-list">📦 ${itemsTxt}</div>
      ${c.notas ? `<div style="font-size:12px;color:var(--muted);margin-top:4px;">📝 ${escapeHtml(c.notas)}</div>` : ''}
      <div style="display:flex;justify-content:space-between;align-items:center;margin-top:8px;">
        ${estadoBadge}
        ${btnCancelar}
      </div>
    </div>`;
    }).join('');
  } catch (e) { 
    cont.innerHTML = `<div class="alert-box danger"><span>Error: ${e.message}</span></div>`; 
  }
}
