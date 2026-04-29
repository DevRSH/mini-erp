    // CREAR PRODUCTO
    // ═══════════════════════════════════════════
    function openModalCrearProducto() {
      ['new-nombre', 'new-precio', 'new-costo', 'new-costo-envio', 'new-cod-proveedor'].forEach(id => { const e = $(id); if (e) e.value = ''; });
      $('new-stock').value = '0'; $('new-stock-min').value = '5'; $('new-categoria').value = 'General';
      $('new-tiene-variantes').checked = false; $('new-stock-field').style.display = '';
      $('modal-crear').classList.add('open');
    }

    function toggleNuevoStockField() {
      $('new-stock-field').style.display = $('new-tiene-variantes').checked ? 'none' : '';
    }

    async function crearProducto() {
      const nombre = $('new-nombre').value.trim();
      const precio = parseFloat($('new-precio').value);
      if (!nombre) { toast('Ingresa un nombre', 'error'); return; }
      if (isNaN(precio) || precio < 0) { toast('Precio inválido', 'error'); return; }
      try {
        await api('POST', '/api/products', {
          nombre, precio,
          costo: parseFloat($('new-costo').value) || 0,
          costo_envio: parseFloat($('new-costo-envio').value) || 0,
          stock: parseInt($('new-stock').value) || 0,
          stock_minimo: parseInt($('new-stock-min').value) ?? 5,
          categoria: $('new-categoria').value || 'General',
          codigo_proveedor: $('new-cod-proveedor').value || '',
          tiene_variantes: $('new-tiene-variantes').checked,
        });
        toast('Producto creado ✅');
        cerrarModales();
        cargarInventario();
      } catch (e) { toast(e.message, 'error'); }
    }

    // ═══════════════════════════════════════════
    // EDITAR PRODUCTO
    // ═══════════════════════════════════════════
    function openModalEditar(id) {
      const p = todosProductos.find(x => x.id === id); if (!p) return;
      $('edit-id').value = p.id; $('edit-nombre').value = p.nombre; $('edit-precio').value = p.precio;
      $('edit-costo').value = p.costo; $('edit-costo-envio').value = p.costo_envio || 0;
      $('edit-stock-min').value = p.stock_minimo; $('edit-categoria').value = p.categoria;
      $('edit-cod-proveedor').value = p.codigo_proveedor || '';
      $('modal-editar').classList.add('open');
    }

    async function guardarEdicion() {
      const id = parseInt($('edit-id').value);
      try {
        await api('PUT', `/api/products/${id}`, {
          nombre: $('edit-nombre').value.trim(),
          precio: parseFloat($('edit-precio').value),
          costo: parseFloat($('edit-costo').value),
          costo_envio: parseFloat($('edit-costo-envio').value) || 0,
          stock_minimo: parseInt($('edit-stock-min').value),
          categoria: $('edit-categoria').value,
          codigo_proveedor: $('edit-cod-proveedor').value || '',
        });
        toast('Producto actualizado ✅');
        cerrarModales(); cargarInventario();
      } catch (e) { toast(e.message, 'error'); }
    }

    // ═══════════════════════════════════════════
    // VARIANTES
    // ═══════════════════════════════════════════
    async function openModalVariantes(productoId) {
      $('var-producto-id').value = productoId;
      $('var-attr1-nombre').value = ''; $('var-attr1-valor').value = '';
      $('var-attr2-nombre').value = ''; $('var-attr2-valor').value = '';
      $('var-stock').value = '0'; $('var-stock-min').value = '2'; $('var-codigo-barras').value = '';
      $('var-tiene-attr2').checked = false; $('var-attr2-fields').style.display = 'none';
      await refrescarVariantesLista(productoId);
      $('modal-variantes').classList.add('open');
    }

    async function refrescarVariantesLista(productoId) {
      try {
        const datos = await obtenerVariantesProducto(productoId);
        $('variantes-titulo').textContent = `📦 ${datos.producto} — Variantes`;
        const lista = datos.variantes;
        if (!lista.length) {
          $('variantes-lista').innerHTML = '<div class="empty-state" style="padding:20px 0"><div class="empty-icon">📦</div><p>Sin variantes. Agrega la primera.</p></div>';
          return;
        }
        $('variantes-lista').innerHTML = lista.map(v => {
          const etiq = v.attr2_valor ? `${v.attr1_valor} / ${v.attr2_valor}` : v.attr1_valor;
          const sub = v.attr2_valor ? `${v.attr1_nombre}: ${v.attr1_valor} | ${v.attr2_nombre}: ${v.attr2_valor}` : `${v.attr1_nombre}: ${v.attr1_valor}`;
          const sb = v.stock === 0 ? 'stock-bad' : v.stock_bajo ? 'stock-warn' : 'stock-ok';
          const st = v.stock === 0 ? '⛔ Agotado' : v.stock_bajo ? `⚠️ ${v.stock} uds` : `✅ ${v.stock} uds`;
          const cod = v.codigo_barras ? `<div style="font-size:11px;color:var(--info);">🔲 ${v.codigo_barras}</div>` : '';
          return `
        <div class="variante-row">
          <div>
            <div class="variante-label">${etiq}</div>
            <div class="variante-sub">${sub}</div>
            ${cod}
          </div>
          <div class="variante-stock">
            <span class="stock-badge ${sb}">${st}</span>
            <div class="variante-actions" style="margin-top:6px;">
              <button class="btn-icon" title="Ajustar stock"
                onclick="openModalAjuste('variante',${v.id},'${etiq.replace(/'/g, "\\'")}',${v.stock})">📦</button>
              <button class="btn-icon" title="Eliminar"
                onclick="eliminarVariante(${v.id},${$('var-producto-id').value})">🗑️</button>
            </div>
          </div>
        </div>`;
        }).join('');
      } catch (e) { toast(e.message, 'error'); }
    }

    function toggleAttr2() {
      $('var-attr2-fields').style.display = $('var-tiene-attr2').checked ? '' : 'none';
    }

    async function crearVariante() {
      const pid = parseInt($('var-producto-id').value);
      const a1n = $('var-attr1-nombre').value.trim();
      const a1v = $('var-attr1-valor').value.trim();
      if (!a1n || !a1v) { toast('Completa el atributo 1', 'error'); return; }
      const tieneA2 = $('var-tiene-attr2').checked;
      const a2n = tieneA2 ? $('var-attr2-nombre').value.trim() : null;
      const a2v = tieneA2 ? $('var-attr2-valor').value.trim() : null;
      if (tieneA2 && (!a2n || !a2v)) { toast('Completa el atributo 2 o desactívalo', 'error'); return; }
      try {
        await api('POST', `/api/products/${pid}/variants`, {
          attr1_nombre: a1n, attr1_valor: a1v,
          attr2_nombre: a2n || null, attr2_valor: a2v || null,
          stock: parseInt($('var-stock').value) || 0,
          stock_minimo: parseInt($('var-stock-min').value) || 2,
          codigo_barras: $('var-codigo-barras').value || '',
        });
        toast('Variante agregada ✅');
        $('var-attr1-valor').value = ''; $('var-attr2-valor').value = '';
        $('var-stock').value = '0'; $('var-codigo-barras').value = '';
        await refrescarVariantesLista(pid);
        cargarInventario();
      } catch (e) { toast(e.message, 'error'); }
    }

    async function eliminarVariante(varId, prodId) {
      if (!confirm('¿Desactivar esta variante?')) return;
      try {
        await api('DELETE', `/api/variantes/${varId}`);
        toast('Variante desactivada');
        await refrescarVariantesLista(prodId);
        cargarInventario();
      } catch (e) { toast(e.message, 'error'); }
    }

    // ═══════════════════════════════════════════
    // AJUSTE STOCK
    // ═══════════════════════════════════════════
    function openModalAjuste(tipo, id, nombre, stock) {
      $('ajuste-tipo-entidad').value = tipo;
      $('ajuste-id').value = id;
      $('ajuste-nombre').textContent = nombre;
      $('ajuste-stock-actual').textContent = `Stock actual: ${stock} unidades`;
      $('ajuste-cantidad').value = ''; $('ajuste-motivo').value = ''; $('ajuste-tipo').value = '1';
      $('modal-ajuste').classList.add('open');
    }

    async function ejecutarAjuste() {
      const tipo = $('ajuste-tipo-entidad').value;
      const id = parseInt($('ajuste-id').value);
      const signo = parseInt($('ajuste-tipo').value);
      const cant = parseInt($('ajuste-cantidad').value);
      const motivo = $('ajuste-motivo').value || 'Ajuste manual';
      if (!cant || cant <= 0) { toast('Cantidad inválida', 'error'); return; }
      try {
        const endpoint = tipo === 'variante' ? `/api/variantes/${id}/ajuste` : `/api/products/${id}/adjust`;
        const res = await api('POST', endpoint, { cantidad: signo * cant, motivo });
        toast(`Stock: ${res.stock_anterior} → ${res.stock_nuevo} ✅`);
        cerrarModales(); cargarInventario();
      } catch (e) { toast(e.message, 'error'); }
    }

    // ═══════════════════════════════════════════
    // ELIMINAR PRODUCTO
    // ═══════════════════════════════════════════
    function openModalEliminar(id, nombre) {
      $('eliminar-id').value = id; $('eliminar-nombre').textContent = nombre;
      $('modal-eliminar').classList.add('open');
    }
    async function eliminarProducto() {
      try {
        const res = await api('DELETE', `/api/products/${parseInt($('eliminar-id').value)}`);
        toast(res.mensaje); cerrarModales(); cargarInventario();
      } catch (e) { toast(e.message, 'error'); }
    }

    // ═══════════════════════════════════════════
