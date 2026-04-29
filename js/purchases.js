    // SPRINT 5 — COMPRAS
    // ═══════════════════════════════════════════
    let itemsCompra = [];  // [{producto_id, variante_id, nombre, etiqueta, cantidad, costo_unitario}]

    async function asegurarProductosCargados() {
      if (todosProductos.length) return;
      todosProductos = await api('GET', '/api/products');
    }

    async function openModalCompra() {
      itemsCompra = [];
      $('compra-proveedor').value = '';
      $('compra-envio').value = '0';
      $('compra-notas').value = '';
      $('compra-actualizar-costo').checked = true;

      try {
        await asegurarProductosCargados();
      } catch (e) {
        toast('Error cargando productos: ' + e.message, 'error');
        return;
      }

      renderItemsCompra();
      actualizarTotalCompra();
      actualizarDatalistProveedores();
      $('modal-compra').classList.add('open');

      if (!todosProductos.length) {
        toast('No hay productos activos para seleccionar en compras', 'info');
      }
    }

    async function actualizarDatalistProveedores() {
      try {
        const compras = await api('GET', '/api/compras?limite=100');
        const provs = [...new Set(compras.map(c => c.proveedor).filter(Boolean))];
        $('proveedores-list').innerHTML = provs.map(p => `<option value="${p}">`).join('');
      } catch (e) { }
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

