    // VENTAS — SELECTOR DE PRODUCTOS
    // ═══════════════════════════════════════════
    async function cargarProductosVenta() {
      try {
        productosVenta = await api('GET', '/api/products');
        renderProductosVenta(productosVenta);
      } catch (e) { toast('Error cargando productos', 'error'); }
    }

    function filtrarProductosVenta() {
      const q = $('search-venta-productos').value.toLowerCase();
      renderProductosVenta(productosVenta.filter(p =>
        p.nombre.toLowerCase().includes(q) || p.categoria.toLowerCase().includes(q)
      ));
    }

    function renderProductosVenta(lista) {
      const cont = $('productos-para-venta');
      cont.innerHTML = lista.map(p => {
        const enCarrito = p.tiene_variantes
          ? Object.keys(carrito).some(k => k.startsWith('var_') && carrito[k].producto_id === p.id)
          : !!carrito[`prod_${p.id}`];
        const noStock = p.stock === 0;
        const ic = ICONOS[p.id % ICONOS.length];
        return `
      <div class="product-select-item ${noStock ? 'nostock' : ''} ${enCarrito ? 'added' : ''}"
           onclick="${noStock ? '' : p.tiene_variantes ? `elegirVariante(${p.id},'${p.nombre.replace(/'/g, "\\'")}')` : `agregarAlCarrito(${p.id})`}">
        <div style="font-size:22px;margin-bottom:4px;">${ic}</div>
        <div class="psi-name">${p.nombre}</div>
        <div class="psi-price">${fmt(p.precio)}</div>
        <div class="psi-stock">${noStock ? 'Sin stock' : `${p.stock} uds`}${enCarrito ? ' ✅' : ''}</div>
        ${p.tiene_variantes ? '<div style="font-size:10px;color:var(--info);">Con variantes</div>' : ''}
      </div>`;
      }).join('');
    }

    function agregarAlCarrito(prodId) {
      const p = productosVenta.find(x => x.id === prodId);
      if (!p || p.stock === 0) return;
      const key = `prod_${prodId}`;
      if (carrito[key]) {
        if (carrito[key].cantidad >= p.stock) { toast(`Solo ${p.stock} disponibles`, 'error'); return; }
        carrito[key].cantidad++;
      } else {
        carrito[key] = { producto_id: prodId, variante_id: null, nombre: p.nombre, etiqueta_variante: null, precio: p.precio, stock: p.stock, cantidad: 1 };
      }
      renderCarrito(); filtrarProductosVenta();
    }

    async function elegirVariante(prodId, prodNombre) {
      try {
        const datos = await obtenerVariantesProducto(prodId);
        const vars = datos.variantes.filter(v => v.activo);
        if (!vars.length) { toast('Sin variantes activas', 'error'); return; }
        $('elegir-variante-titulo').textContent = `📦 ${prodNombre}`;
        $('elegir-variante-grid').innerHTML = vars.map(v => {
          const etiq = v.attr2_valor ? `${v.attr1_valor} / ${v.attr2_valor}` : v.attr1_valor;
          const noStock = v.stock === 0;
          return `
        <div class="variante-picker-item ${noStock ? 'nostock' : ''}"
             onclick="${noStock ? '' :
              `agregarVarianteAlCarrito(${prodId},'${prodNombre.replace(/'/g, "\\'")}',${v.id},'${etiq.replace(/'/g, "\\'")}',${v.precio || 'null'},${v.stock})`}">
          <div class="vpi-nombre">${etiq}</div>
          <div class="vpi-stock">${noStock ? 'Sin stock' : `${v.stock} uds`}</div>
        </div>`;
        }).join('');
        $('modal-elegir-variante').classList.add('open');
      } catch (e) { toast(e.message, 'error'); }
    }

    function agregarVarianteAlCarrito(prodId, prodNombre, varId, etiqueta, precioVar, stock) {
      const p = productosVenta.find(x => x.id === prodId);
      const precio = precioVar || (p ? p.precio : 0);
      const key = `var_${varId}`;
      if (carrito[key]) {
        if (carrito[key].cantidad >= stock) { toast(`Solo ${stock} disponibles`, 'error'); return; }
        carrito[key].cantidad++;
      } else {
        carrito[key] = { producto_id: prodId, variante_id: varId, nombre: prodNombre, etiqueta_variante: etiqueta, precio, stock, cantidad: 1 };
      }
      cerrarModales(); renderCarrito(); filtrarProductosVenta();
    }

    function cambiarCantidadCarrito(key, delta) {
      if (!carrito[key]) return;
      const nueva = carrito[key].cantidad + delta;
      if (nueva <= 0) { delete carrito[key]; }
      else if (nueva > carrito[key].stock) { toast(`Máximo ${carrito[key].stock} disponibles`, 'error'); return; }
      else { carrito[key].cantidad = nueva; }
      renderCarrito(); filtrarProductosVenta();
    }

    function renderCarrito() {
      const items = Object.entries(carrito);
      const vacio = $('carrito-vacio');
      const cItems = $('carrito-items');
      const cTotal = $('carrito-total');
      if (!items.length) { vacio.style.display = 'block'; cItems.innerHTML = ''; cTotal.style.display = 'none'; return; }
      vacio.style.display = 'none'; cTotal.style.display = 'block';
      let total = 0;
      cItems.innerHTML = items.map(([key, item]) => {
        const sub = item.precio * item.cantidad;
        total += sub;
        return `
      <div class="cart-item">
        <div style="flex:1;">
          <div class="cart-name">${item.nombre}</div>
          ${item.etiqueta_variante ? `<div class="cart-variant">📌 ${item.etiqueta_variante}</div>` : ''}
        </div>
        <div class="cart-qty">
          <button class="qty-btn" onclick="cambiarCantidadCarrito('${key}',-1)">−</button>
          <span class="qty-num">${item.cantidad}</span>
          <button class="qty-btn" onclick="cambiarCantidadCarrito('${key}',+1)">+</button>
        </div>
        <div class="cart-subtotal">${fmt(sub)}</div>
      </div>`;
      }).join('');
      $('total-venta').textContent = fmt(total);
    }

    async function confirmarVenta() {
      const items = Object.values(carrito).map(i => ({
        producto_id: i.producto_id,
        cantidad: i.cantidad,
        variante_id: i.variante_id || null
      }));
      if (!items.length) { toast('Carrito vacío', 'error'); return; }
      try {
        const res = await api('POST', '/api/ventas', { items, metodo_pago: $('metodo-pago').value });
        toast(`Venta #${res.venta_id} — ${fmt(res.total)} 🎉`);
        carrito = {}; renderCarrito(); cargarProductosVenta();
      } catch (e) { toast(e.message, 'error'); }
    }

    // ═══════════════════════════════════════════
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
      try {
        const res = await api('POST', '/api/compras', {
          proveedor: $('compra-proveedor').value || 'Sin nombre',
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
          return `
        <div class="sale-card">
          <div class="sale-header">
            <div>
              <div class="sale-id">#${String(c.id).padStart(4, '0')} — ${escapeHtml(c.proveedor)}</div>
              <div class="sale-date">${fecha}</div>
            </div>
            <div style="text-align:right;">
              <div class="sale-total" style="color:var(--primary);">${fmt(c.total)}</div>
              ${c.costo_envio > 0 ? `<span class="sale-method">🚚 envío ${fmt(c.costo_envio)}</span>` : ''}
            </div>
          </div>
          <div class="sale-items-list">📦 ${itemsTxt}</div>
          ${c.notas ? `<div style="font-size:12px;color:var(--muted);margin-top:4px;">📝 ${escapeHtml(c.notas)}</div>` : ''}
        </div>`;
        }).join('');
      } catch (e) { $('lista-compras').innerHTML = `<div class="alert-box danger"><span>${e.message}</span></div>`; }
    }

    // ═══════════════════════════════════════════
