// ═══════════════════════════════════════════
    // AUTENTICACIÓN — PIN
    // ═══════════════════════════════════════════
    let pinActual = '';

    async function verificarSesion() {
      try {
        const r = await fetch('/api/sesion', { credentials: 'same-origin' });
        const d = await r.json();
        if (d.autenticado) {
          mostrarApp();
        } else {
          mostrarPin();
        }
      } catch (e) {
        mostrarPin();
      }
    }

    function mostrarPin() {
      document.getElementById('pin-screen').classList.remove('hidden');
      pinActual = '';
      actualizarDots();
    }

    function mostrarApp() {
      document.getElementById('pin-screen').classList.add('hidden');
      cargarDashboard();
    }

    function pinKey(digito) {
      if (pinActual.length >= 4) return;
      pinActual += digito;
      actualizarDots();
      if (pinActual.length === 4) {
        setTimeout(enviarPin, 120);
      }
    }

    function pinBorrar() {
      pinActual = pinActual.slice(0, -1);
      actualizarDots();
      document.getElementById('pin-error').textContent = '';
    }

    function actualizarDots() {
      for (let i = 0; i < 4; i++) {
        const dot = document.getElementById(`d${i}`);
        dot.classList.remove('filled', 'error');
        if (i < pinActual.length) dot.classList.add('filled');
      }
    }

    async function enviarPin() {
      try {
        const r = await fetch('/api/login', {
          credentials: 'same-origin',
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ pin: pinActual })
        });
        if (r.ok) {
          mostrarApp();
        } else {
          // PIN incorrecto — animar error
          for (let i = 0; i < 4; i++) {
            document.getElementById(`d${i}`).classList.add('error');
          }
          document.getElementById('pin-error').textContent = 'PIN incorrecto. Intenta de nuevo.';
          setTimeout(() => {
            pinActual = '';
            actualizarDots();
            document.getElementById('pin-error').textContent = '';
          }, 1200);
        }
      } catch (e) {
        document.getElementById('pin-error').textContent = 'Error de conexión.';
        pinActual = '';
        actualizarDots();
      }
    }

    async function cerrarSesion() {
      if (!confirm('¿Cerrar sesión?')) return;
      await fetch('/api/logout', { method: 'POST', credentials: 'same-origin' });
      mostrarPin();
    }

    // ═══════════════════════════════════════════
    // ESTADO GLOBAL
    // ═══════════════════════════════════════════
    let todosProductos = [];
    let productosVenta = [];
    let carrito = {};          // key: "prod_ID" o "var_ID"
    let scannerActivo = false;
    let html5QrCode = null;
    let pendienteProductoVariante = null; // producto esperando elección de variante

    // ═══════════════════════════════════════════
    // UTILIDADES
    // ═══════════════════════════════════════════
    const $ = id => document.getElementById(id);
    const fmt = n => (n == null || isNaN(n)) ? '—' : '$' + Number(n).toLocaleString('es-CL');
    const ALLOWED_TOAST_TYPES = new Set(['success', 'error', 'info']);
    function escapeHtml(value) {
      return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
    }

    function toast(msg, tipo = 'success') {
      const c = $('toast-container');
      const el = document.createElement('div');
      const ic = { success: '✅', error: '❌', info: 'ℹ️' };
      const safeType = ALLOWED_TOAST_TYPES.has(tipo) ? tipo : 'success';
      el.className = `toast ${safeType}`;
      const icon = document.createElement('span');
      icon.textContent = ic[safeType] || '';
      const message = document.createElement('span');
      message.textContent = String(msg ?? '');
      el.append(icon, message);
      c.appendChild(el);
      setTimeout(() => el.remove(), 3500);
    }

    async function api(method, path, body = null) {
      const opts = { method, headers: { 'Content-Type': 'application/json' } };
      if (body) opts.body = JSON.stringify(body);
      opts.credentials = 'same-origin';
      const res = await fetch(path, opts);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Error del servidor');
      return data;
    }

    async function obtenerVariantesProducto(productId) {
      return await api('GET', `/api/products/${productId}/variants`);
    }

    function cerrarModales() {
      document.querySelectorAll('.modal-overlay').forEach(m => m.classList.remove('open'));
      detenerScanner();
    }
    document.querySelectorAll('.modal-overlay').forEach(m => {
      m.addEventListener('click', e => { if (e.target === m) cerrarModales(); });
    });

    function marginClass(pct) {
      if (pct >= 30) return 'margin-good';
      if (pct >= 15) return 'margin-mid';
      return 'margin-bad';
    }

    // ═══════════════════════════════════════════
    // NAVEGACIÓN
    // ═══════════════════════════════════════════
    function navTo(pag) {
      document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
      document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
      $(`page-${pag}`).classList.add('active');
      $(`nav-${pag}`).classList.add('active');
      const loaders = {
        dashboard: cargarDashboard,
        inventario: cargarInventario,
        ventas: cargarProductosVenta,
        compras: cargarCompras,
        historial: cargarHistorial,
        reportes: () => cargarReportes('hoy')
      };
      if (loaders[pag]) loaders[pag]();
    }

    // ═══════════════════════════════════════════
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
    // ESCÁNER DE CÓDIGO DE BARRAS
    // ═══════════════════════════════════════════
    function toggleScanner() {
      if (scannerActivo) detenerScanner();
      else iniciarScanner('scanner-container', onCodigoEscaneadoVenta);
    }

    function iniciarScanner(containerId, callback) {
      if (scannerActivo) return;
      html5QrCode = new Html5Qrcode(containerId);
      html5QrCode.start(
        { facingMode: "environment" },
        { fps: 10, qrbox: { width: 250, height: 120 } },
        (decodedText) => { callback(decodedText); detenerScanner(); }
      ).then(() => {
        scannerActivo = true;
        $('btn-escanear').textContent = '⏹️ Detener escáner';
      }).catch(err => {
        toast('No se pudo acceder a la cámara: ' + err, 'error');
      });
    }

    function detenerScanner() {
      if (html5QrCode && scannerActivo) {
        html5QrCode.stop().catch(() => { });
        html5QrCode = null;
      }
      scannerActivo = false;
      const btn = $('btn-escanear');
      if (btn) btn.textContent = '📷 Escanear código';
      const cont = $('scanner-container');
      if (cont) cont.innerHTML = '';
    }

    async function onCodigoEscaneadoVenta(codigo) {
      const resultDiv = $('scanner-result');
      try {
        const res = await api('GET', `/api/buscar?codigo=${encodeURIComponent(codigo)}`);
        if (res.tipo === 'variante') {
          const v = res.datos;
          const carritoKey = `var_${v.id}`;
          if (!carrito[carritoKey]) {
            carrito[carritoKey] = {
              producto_id: v.producto_id, variante_id: v.id,
              nombre: v.producto_nombre,
              etiqueta_variante: v.attr2_valor ? `${v.attr1_valor} / ${v.attr2_valor}` : v.attr1_valor,
              precio: v.precio, stock: v.stock, cantidad: 1
            };
          } else { carrito[carritoKey].cantidad++; }
          resultDiv.textContent = `✅ Agregado: ${v.producto_nombre} — ${carrito[carritoKey].etiqueta_variante}`;
        } else {
          const p = res.datos;
          if (p.tiene_variantes) { toast('Este producto tiene variantes. Selecciónalo manualmente.', 'info'); return; }
          const carritoKey = `prod_${p.id}`;
          if (!carrito[carritoKey]) {
            carrito[carritoKey] = { producto_id: p.id, variante_id: null, nombre: p.nombre, etiqueta_variante: null, precio: p.precio, stock: p.stock, cantidad: 1 };
          } else { carrito[carritoKey].cantidad++; }
          resultDiv.textContent = `✅ Agregado: ${p.nombre}`;
        }
        resultDiv.style.display = 'block';
        setTimeout(() => resultDiv.style.display = 'none', 2500);
        renderCarrito();
      } catch (e) {
        resultDiv.style.background = '#FEE2E2'; resultDiv.style.color = '#991B1B';
        resultDiv.textContent = `❌ Código no encontrado: ${codigo}`;
        resultDiv.style.display = 'block';
        setTimeout(() => { resultDiv.style.display = 'none'; resultDiv.style.background = ''; resultDiv.style.color = ''; }, 3000);
      }
    }

    async function buscarPorCodigo() {
      const codigo = $('input-codigo').value.trim();
      if (!codigo) return;
      await onCodigoEscaneadoVenta(codigo);
      $('input-codigo').value = '';
    }

    function escanearVariante() {
      const cont = document.createElement('div');
      cont.id = 'scanner-variante-tmp';
      $('var-codigo-barras').parentElement.appendChild(cont);
      const tmpScanner = new Html5Qrcode('scanner-variante-tmp');
      tmpScanner.start(
        { facingMode: "environment" },
        { fps: 10, qrbox: { width: 200, height: 100 } },
        (decoded) => {
          $('var-codigo-barras').value = decoded;
          tmpScanner.stop().then(() => cont.remove()).catch(() => { });
          toast('Código capturado ✅');
        }
      ).catch(e => { toast('Cámara no disponible', 'error'); cont.remove(); });
    }

    // ═══════════════════════════════════════════
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

    // REGISTRO DEL SERVICE WORKER (PWA)
    if ('serviceWorker' in navigator) {
      window.addEventListener('load', () => {
        navigator.serviceWorker.register('/service-worker.js')
          .then(() => console.log('✅ Service Worker registrado'))
          .catch(e => console.warn('SW error:', e));
      });
    }

    // PROMPT DE INSTALACIÓN
    let installPrompt = null;
    window.addEventListener('beforeinstallprompt', e => {
      e.preventDefault();
      installPrompt = e;
      // Mostrar banner de instalación
      const banner = document.createElement('div');
      banner.id = 'install-banner';
      banner.style.cssText = `
    position:fixed; bottom:calc(var(--nav-h) + 12px); left:16px; right:16px;
    background:#1B3A6B; color:white; padding:12px 16px; border-radius:12px;
    display:flex; align-items:center; justify-content:space-between;
    z-index:150; box-shadow:0 4px 20px rgba(0,0,0,.25);
    font-family:'Outfit',sans-serif; font-size:14px; font-weight:600;
    animation:fadeInDown .3s ease;
  `;
      banner.innerHTML = `
    <span>📲 Instalar Fika como app</span>
    <div style="display:flex;gap:8px;">
      <button onclick="instalarPWA()" style="background:#E8821A;color:white;border:none;
        padding:7px 14px;border-radius:8px;cursor:pointer;font-family:'Outfit',sans-serif;
        font-size:13px;font-weight:700;">Instalar</button>
      <button onclick="document.getElementById('install-banner').remove()"
        style="background:rgba(255,255,255,.15);color:white;border:none;
        padding:7px 10px;border-radius:8px;cursor:pointer;font-size:13px;">✕</button>
    </div>`;
      document.body.appendChild(banner);
    });

    async function instalarPWA() {
      if (!installPrompt) return;
      installPrompt.prompt();
      const result = await installPrompt.userChoice;
      if (result.outcome === 'accepted') toast('¡App instalada! Búscala en tu pantalla de inicio 🎉');
      installPrompt = null;
      const b = document.getElementById('install-banner');
      if (b) b.remove();
    }

    // INICIO — verificar sesión antes de mostrar la app
    document.addEventListener('DOMContentLoaded', verificarSesion);

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
