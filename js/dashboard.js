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

    // ═══════════════════════════════════════════
    // INVENTARIO
    // ═══════════════════════════════════════════
    const ICONOS = ['🥤', '🎩', '👕', '👟', '🍫', '🍬', '🧴', '📦', '🧃', '☕', '🫙', '🍭', '🧤', '🧣'];

    async function cargarInventario() {
      $('lista-productos').innerHTML = '<div class="spinner"></div>';
      try {
        todosProductos = await api('GET', '/api/products');
        renderInventario(todosProductos);
        actualizarDatalistCategorias();
      } catch (e) { $('lista-productos').innerHTML = `<div class="alert-box danger"><span>${e.message}</span></div>`; }
    }

    function renderInventario(lista) {
      const cont = $('lista-productos');
      $('productos-count').textContent = `${lista.length} producto${lista.length !== 1 ? 's' : ''}`;
      if (!lista.length) { cont.innerHTML = '<div class="empty-state"><div class="empty-icon">📦</div><p>Sin productos.</p></div>'; return; }
      cont.innerHTML = lista.map(p => {
        const sc = p.stock === 0 ? 'no-stock' : p.stock_bajo ? 'low-stock' : '';
        const sb = p.stock === 0 ? 'stock-bad' : p.stock_bajo ? 'stock-warn' : 'stock-ok';
        const st = p.stock === 0 ? '⛔ Agotado' : p.stock_bajo ? `⚠️ ${p.stock} uds` : `✅ ${p.stock} uds`;
        const ic = ICONOS[p.id % ICONOS.length];
        const mc = marginClass(p.margen_pct || 0);
        const mg = p.costo > 0 ? `<div class="product-margin ${mc}">Margen: ${p.margen_pct}%</div>` : '';
        const cv = p.tiene_variantes ? `<span class="variante-badge">Con variantes</span>` : '';
        const cod = p.codigo_proveedor ? `<div class="product-cod">🏷️ ${escapeHtml(p.codigo_proveedor)}</div>` : '';
        return `
      <div class="product-card ${sc}">
        <div class="product-icon">${ic}</div>
        <div class="product-info">
          <div class="product-name">${escapeHtml(p.nombre)}</div>
          <div class="product-cat">${escapeHtml(p.categoria)}</div>
          ${cod}${cv}
        </div>
        <div class="product-meta">
          <div class="product-price">${fmt(p.precio)}</div>
          ${mg}
          <span class="stock-badge ${sb}">${st}</span>
        </div>
        <div class="product-actions">
          <button class="btn-icon" title="Editar" onclick="openModalEditar(${p.id})">✏️</button>
          <button class="btn-icon" title="${p.tiene_variantes ? 'Variantes' : 'Ajustar stock'}" onclick="${p.tiene_variantes ? `openModalVariantes(${p.id})` : `openModalAjuste('producto',${p.id},'${p.nombre.replace(/'/g, "\\'")}',${p.stock})`}">📦</button>
          <button class="btn-icon" title="Desactivar" onclick="openModalEliminar(${p.id},'${p.nombre.replace(/'/g, "\\'")}')">🗑️</button>
        </div>
      </div>`;
      }).join('');
    }

    function filtrarProductos() {
      const q = $('search-productos').value.toLowerCase();
      renderInventario(todosProductos.filter(p =>
        p.nombre.toLowerCase().includes(q) ||
        p.categoria.toLowerCase().includes(q) ||
        (p.codigo_proveedor || '').toLowerCase().includes(q)
      ));
    }

    function actualizarDatalistCategorias() {
      const cats = [...new Set(todosProductos.map(p => p.categoria))];
      $('categorias-list').innerHTML = cats.map(c => `<option value="${c}">`).join('');
    }

    // ═══════════════════════════════════════════
