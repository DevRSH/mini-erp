// ═══════════════════════════════════════════
// SPRINT 5 — COMPRAS
// ═══════════════════════════════════════════
let itemsCompra = [];  // [{producto_id, variante_id, nombre, etiqueta, cantidad, costo_unitario}]

async function asegurarProductosCargados() {
  if (todosProductos.length) return;
  todosProductos = await api('GET', '/api/products');
}

async function openModalCompra() {
  itemsCompra = [];
  if ($('compra-proveedor-id')) $('compra-proveedor-id').value = '';
  if ($('compra-proveedor-nuevo')) $('compra-proveedor-nuevo').value = '';
  $('compra-envio').value = '0';
  $('compra-notas').value = '';
  $('compra-actualizar-costo').checked = true;

  try {
    await Promise.all([asegurarProductosCargados(), cargarProveedores()]);
  } catch (e) {
    toast('Error cargando datos: ' + e.message, 'error');
    return;
  }

  renderItemsCompra();
  actualizarTotalCompra();
  $('modal-compra').classList.add('open');

  if (!todosProductos.length) {
    toast('No hay productos activos para seleccionar en compras', 'info');
  }
}

function agregarItemCompra() {
  if (!todosProductos.length) {
    toast('No hay productos disponibles. Crea o activa productos primero.', 'error');
    return;
  }
  itemsCompra.push({ producto_id: null, variante_id: null, nombre: '', etiqueta: '', cantidad: 1, costo_unitario: 0 });
  renderItemsCompra();
}

function renderItemsCompra() {
  const cont = $('compra-items-lista');
  if (!itemsCompra.length) {
    cont.innerHTML = '<p style="color:var(--muted);font-size:13px;text-align:center;padding:8px 0;">Sin productos. Agrega uno arriba.</p>';
    return;
  }
  cont.innerHTML = itemsCompra.map((item, idx) => `
<div class="card" style="padding:12px;margin-bottom:8px;position:relative;">
  <button onclick="eliminarItemCompra(${idx})" style="position:absolute;top:8px;right:8px;background:none;border:none;cursor:pointer;font-size:16px;color:var(--muted);">✕</button>
  <div class="form-group" style="margin-bottom:8px;">
    <label class="form-label">Producto</label>
    <select class="form-select" id="ci-prod-${idx}" onchange="onSelectProductoCompra(${idx})" style="font-size:14px;">
      <option value="">— Seleccionar —</option>
      ${todosProductos.map(p => `<option value="${p.id}" ${item.producto_id === p.id ? 'selected' : ''}>${p.nombre}${p.tiene_variantes ? ' (con variantes)' : ''}</option>`).join('')}
    </select>
  </div>
  <div id="ci-variante-wrap-${idx}" style="display:${item.producto_id && todosProductos.find(p => p.id === item.producto_id)?.tiene_variantes ? '' : 'none'}">
    <div class="form-group" style="margin-bottom:8px;">
      <label class="form-label">Variante</label>
      <select class="form-select" id="ci-var-${idx}" onchange="onSelectVarianteCompra(${idx})" style="font-size:14px;">
        <option value="">— Seleccionar variante —</option>
      </select>
    </div>
  </div>
  <div class="form-row">
    <div class="form-group" style="margin-bottom:0;">
      <label class="form-label">Cantidad</label>
      <input type="number" class="form-input" id="ci-cant-${idx}" value="${item.cantidad}" min="1"
             onchange="itemsCompra[${idx}].cantidad=parseInt(this.value)||1; actualizarTotalCompra();" style="font-size:14px;">
    </div>
    <div class="form-group" style="margin-bottom:0;">
      <label class="form-label">Costo unitario</label>
      <input type="number" class="form-input" id="ci-costo-${idx}" value="${item.costo_unitario}" min="0"
             onchange="itemsCompra[${idx}].costo_unitario=parseFloat(this.value)||0; actualizarTotalCompra();" style="font-size:14px;">
    </div>
  </div>
</div>`).join('');

  // Cargar variantes para productos que ya las tienen
  itemsCompra.forEach((item, idx) => {
    if (item.producto_id && todosProductos.find(p => p.id === item.producto_id)?.tiene_variantes) {
      cargarVariantesSelectCompra(idx, item.producto_id, item.variante_id);
    }
  });
}

async function onSelectProductoCompra(idx) {
  const sel = $(`ci-prod-${idx}`);
  const pid = parseInt(sel.value) || null;
  itemsCompra[idx].producto_id = pid;
  itemsCompra[idx].variante_id = null;
  const p = pid ? todosProductos.find(x => x.id === pid) : null;
  itemsCompra[idx].nombre = p ? p.nombre : '';
  if (p?.costo) { itemsCompra[idx].costo_unitario = p.costo; $(`ci-costo-${idx}`).value = p.costo; }
  const wrap = $(`ci-variante-wrap-${idx}`);
  if (p?.tiene_variantes) { wrap.style.display = ''; await cargarVariantesSelectCompra(idx, pid, null); }
  else wrap.style.display = 'none';
  actualizarTotalCompra();
}

async function cargarVariantesSelectCompra(idx, prodId, varSeleccionada) {
  try {
    const datos = await obtenerVariantesProducto(prodId);
    const sel = $(`ci-var-${idx}`);
    if (!sel) return;
    sel.innerHTML = '<option value="">— Seleccionar variante —</option>' +
      datos.variantes.map(v => {
        const etiq = v.attr2_valor ? `${v.attr1_valor} / ${v.attr2_valor}` : v.attr1_valor;
        return `<option value="${v.id}" ${varSeleccionada === v.id ? 'selected' : ''}>${etiq} (stock: ${v.stock})</option>`;
      }).join('');
  } catch (e) { }
}

function onSelectVarianteCompra(idx) {
  const vid = parseInt($(`ci-var-${idx}`).value) || null;
  itemsCompra[idx].variante_id = vid;
}

function eliminarItemCompra(idx) {
  itemsCompra.splice(idx, 1);
  renderItemsCompra();
  actualizarTotalCompra();
}

function actualizarTotalCompra() {
  const envio = parseFloat($('compra-envio')?.value) || 0;
  const sub = itemsCompra.reduce((s, i) => s + (i.cantidad * (i.costo_unitario || 0)), 0);
  const total = sub + envio;
  const fmt2 = n => '$' + Math.round(n).toLocaleString('es-CL');
  if ($('compra-subtotal-txt')) $('compra-subtotal-txt').textContent = fmt2(sub);
  if ($('compra-envio-txt')) $('compra-envio-txt').textContent = fmt2(envio);
  if ($('compra-total-txt')) $('compra-total-txt').textContent = fmt2(total);
}

$('compra-envio')?.addEventListener('input', actualizarTotalCompra);

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
  $('lista-compras').innerHTML = '<div class="spinner"></div>';
  cargarProveedores(); // Cargar directorio de proveedores también
  try {
    const compras = await api('GET', '/api/compras?limite=50');
    if (!compras.length) {
      $('lista-compras').innerHTML = '<div class="empty-state"><div class="empty-icon">🚚</div><p>Sin compras registradas.</p></div>';
      return;
    }
    $('lista-compras').innerHTML = compras.map(c => {
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
  } catch (e) { $('lista-compras').innerHTML = `<div class="alert-box danger"><span>${e.message}</span></div>`; }
}


