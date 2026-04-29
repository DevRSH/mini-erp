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
  
  $('subtotal-venta').textContent = fmt(total);
  
  const descPct = parseFloat($('venta-desc-pct').value) || 0;
  const descMonto = parseFloat($('venta-desc-monto').value) || 0;
  
  const totalConDescuento = Math.max(0, total - descMonto - (total * descPct / 100));
  $('total-venta').textContent = fmt(totalConDescuento);
}

async function confirmarVenta() {
  const items = Object.values(carrito).map(i => ({
    producto_id: i.producto_id,
    cantidad: i.cantidad,
    variante_id: i.variante_id || null
  }));
  if (!items.length) { toast('Carrito vacío', 'error'); return; }
  
  const descPct = parseFloat($('venta-desc-pct').value) || 0;
  const descMonto = parseFloat($('venta-desc-monto').value) || 0;
  
  try {
    const res = await api('POST', '/api/ventas', { 
      items, 
      metodo_pago: $('metodo-pago').value,
      descuento_pct: descPct,
      descuento_monto: descMonto
    });
    toast(`Venta #${res.venta_id} — ${fmt(res.total)} 🎉`);
    carrito = {}; 
    $('venta-desc-pct').value = 0;
    $('venta-desc-monto').value = 0;
    renderCarrito(); 
    cargarProductosVenta();
  } catch (e) { toast(e.message, 'error'); }
}
