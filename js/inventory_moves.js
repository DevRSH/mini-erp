// ═══════════════════════════════════════════
// TOMA FÍSICA DE INVENTARIO
// ═══════════════════════════════════════════
let productosConteo = [];
let itemsConteo = {}; // key: prod_id o var_id

function openModalConteo() {
  $('conteo-motivo').value = '';
  $('search-conteo-productos').value = '';
  itemsConteo = {};
  $('conteo-resumen').style.display = 'none';
  $('btn-confirmar-conteo').disabled = true;
  cargarProductosConteo();
  renderItemsConteo();
  $('modal-conteo').classList.add('open');
}

async function cargarProductosConteo() {
  try {
    productosConteo = await api('GET', '/api/products');
    filtrarProductosConteo();
  } catch (e) { toast('Error cargando productos', 'error'); }
}

function filtrarProductosConteo() {
  const q = $('search-conteo-productos').value.toLowerCase();
  const cont = $('productos-para-conteo');
  
  const filtrados = productosConteo.filter(p =>
    p.nombre.toLowerCase().includes(q) || p.categoria.toLowerCase().includes(q)
  );

  cont.innerHTML = filtrados.map(p => {
    if (p.tiene_variantes) {
      return `
      <div class="product-select-item" onclick="seleccionarVarianteConteo(${p.id}, '${p.nombre.replace(/'/g, "\\'")}')">
        <div style="font-size:22px;margin-bottom:4px;">📦</div>
        <div class="psi-name">${p.nombre}</div>
        <div style="font-size:10px;color:var(--info);">Seleccionar variante</div>
      </div>`;
    } else {
      const key = `prod_${p.id}`;
      const agregado = !!itemsConteo[key];
      return `
      <div class="product-select-item ${agregado ? 'added' : ''}" onclick="agregarAConteo(${p.id}, null, '${p.nombre.replace(/'/g, "\\'")}', ${p.stock})">
        <div style="font-size:22px;margin-bottom:4px;">📦</div>
        <div class="psi-name">${p.nombre}</div>
        <div class="psi-stock">Stock actual: ${p.stock}</div>
        ${agregado ? '<div style="font-size:10px;color:var(--success);">Agregado ✅</div>' : ''}
      </div>`;
    }
  }).join('');
}

async function seleccionarVarianteConteo(prodId, prodNombre) {
  try {
    const datos = await obtenerVariantesProducto(prodId);
    const vars = datos.variantes.filter(v => v.activo);
    if (!vars.length) { toast('Sin variantes activas', 'error'); return; }
    
    // Mostramos las variantes en el mismo contenedor para simplificar
    const cont = $('productos-para-conteo');
    cont.innerHTML = `
      <div style="grid-column: 1 / -1; margin-bottom: 8px;">
        <button class="btn btn-outline btn-sm" onclick="filtrarProductosConteo()">⬅️ Volver</button>
        <span style="font-weight:bold; margin-left:8px;">${prodNombre}</span>
      </div>
    ` + vars.map(v => {
      const etiq = v.attr2_valor ? `${v.attr1_valor} / ${v.attr2_valor}` : v.attr1_valor;
      const key = `var_${v.id}`;
      const agregado = !!itemsConteo[key];
      return `
      <div class="product-select-item ${agregado ? 'added' : ''}" onclick="agregarAConteo(${prodId}, ${v.id}, '${prodNombre} - ${etiq}', ${v.stock})">
        <div style="font-size:22px;margin-bottom:4px;">🏷️</div>
        <div class="psi-name">${etiq}</div>
        <div class="psi-stock">Stock: ${v.stock}</div>
        ${agregado ? '<div style="font-size:10px;color:var(--success);">Agregado ✅</div>' : ''}
      </div>`;
    }).join('');
  } catch (e) { toast(e.message, 'error'); }
}

function agregarAConteo(prodId, varId, nombre, stockSistema) {
  const key = varId ? `var_${varId}` : `prod_${prodId}`;
  if (!itemsConteo[key]) {
    itemsConteo[key] = {
      producto_id: prodId,
      variante_id: varId,
      nombre: nombre,
      stock_sistema: stockSistema,
      cantidad_fisica: stockSistema
    };
  }
  
  $('conteo-resumen').style.display = 'none';
  $('btn-confirmar-conteo').disabled = true;
  
  renderItemsConteo();
  filtrarProductosConteo();
}

function removerDeConteo(key) {
  delete itemsConteo[key];
  $('conteo-resumen').style.display = 'none';
  $('btn-confirmar-conteo').disabled = true;
  renderItemsConteo();
  filtrarProductosConteo();
}

function actualizarCantidadConteo(key, qty) {
  if (itemsConteo[key]) {
    itemsConteo[key].cantidad_fisica = parseInt(qty) || 0;
    $('conteo-resumen').style.display = 'none';
    $('btn-confirmar-conteo').disabled = true;
  }
}

function renderItemsConteo() {
  const items = Object.entries(itemsConteo);
  const vacio = $('conteo-vacio');
  const cItems = $('conteo-items');
  
  if (!items.length) { 
    vacio.style.display = 'block'; 
    cItems.innerHTML = ''; 
    return; 
  }
  
  vacio.style.display = 'none';
  
  cItems.innerHTML = items.map(([key, item]) => `
  <div class="cart-item" style="align-items: center;">
    <div style="flex:1;">
      <div class="cart-name">${item.nombre}</div>
      <div style="font-size:12px; color:var(--muted);">Sistema: ${item.stock_sistema}</div>
    </div>
    <div style="display:flex; align-items:center; gap:8px;">
      <label style="font-size:12px;">Físico:</label>
      <input type="number" class="form-input" style="width:70px; padding:4px;" value="${item.cantidad_fisica}" min="0" onchange="actualizarCantidadConteo('${key}', this.value)">
      <button class="btn btn-outline btn-sm" style="padding:4px; color:var(--danger); border-color:transparent;" onclick="removerDeConteo('${key}')">❌</button>
    </div>
  </div>`).join('');
}

async function compararConteo() {
  const items = Object.values(itemsConteo).map(i => ({
    producto_id: i.producto_id,
    variante_id: i.variante_id,
    cantidad_fisica: i.cantidad_fisica
  }));
  
  if (!items.length) { toast('No hay items para comparar', 'error'); return; }
  
  try {
    const res = await api('POST', '/api/inventario/conteo', { items, motivo: "Comparacion" });
    
    const resumen = $('conteo-resumen');
    const diffTxt = $('conteo-diferencias-txt');
    
    resumen.style.display = 'block';
    
    if (res.total_diferencias === 0) {
      diffTxt.textContent = `✅ Todo cuadra perfecto (${res.total_items} items).`;
      diffTxt.style.color = 'var(--success)';
      // No habilitamos confirmar porque no hay nada que ajustar
      $('btn-confirmar-conteo').disabled = true;
    } else {
      diffTxt.textContent = `⚠️ Hay diferencias en ${res.total_diferencias} items.`;
      diffTxt.style.color = 'var(--danger)';
      $('btn-confirmar-conteo').disabled = false;
    }
    
  } catch (e) { toast(e.message, 'error'); }
}

async function confirmarConteoFisico() {
  const items = Object.values(itemsConteo).map(i => ({
    producto_id: i.producto_id,
    variante_id: i.variante_id,
    cantidad_fisica: i.cantidad_fisica
  }));
  
  const motivo = $('conteo-motivo').value.trim() || "Toma de inventario físico";
  
  try {
    const res = await api('POST', '/api/inventario/confirmar-conteo', { items, motivo });
    toast(`Inventario ajustado. ${res.items_ajustados} items modificados. ✅`);
    cerrarModales();
    cargarInventario();
  } catch (e) { toast(e.message, 'error'); }
}

// ═══════════════════════════════════════════
// REGISTRO DE MERMA
// ═══════════════════════════════════════════
let itemsMerma = {}; // key: prod_id o var_id

function openModalMerma() {
  $('merma-motivo').value = '';
  $('search-merma-productos').value = '';
  itemsMerma = {};
  cargarProductosMerma();
  renderItemsMerma();
  $('modal-merma').classList.add('open');
}

async function cargarProductosMerma() {
  try {
    productosConteo = await api('GET', '/api/products');
    filtrarProductosMerma();
  } catch (e) { toast('Error cargando productos', 'error'); }
}

function filtrarProductosMerma() {
  const q = $('search-merma-productos').value.toLowerCase();
  const cont = $('productos-para-merma');
  
  const filtrados = productosConteo.filter(p =>
    p.nombre.toLowerCase().includes(q) || p.categoria.toLowerCase().includes(q)
  );

  cont.innerHTML = filtrados.map(p => {
    if (p.tiene_variantes) {
      return `
      <div class="product-select-item" onclick="seleccionarVarianteMerma(${p.id}, '${p.nombre.replace(/'/g, "\\'")}')">
        <div style="font-size:22px;margin-bottom:4px;">📦</div>
        <div class="psi-name">${p.nombre}</div>
        <div style="font-size:10px;color:var(--info);">Seleccionar variante</div>
      </div>`;
    } else {
      const key = `prod_${p.id}`;
      const agregado = !!itemsMerma[key];
      return `
      <div class="product-select-item ${agregado ? 'added' : ''}" onclick="agregarAMerma(${p.id}, null, '${p.nombre.replace(/'/g, "\\'")}', ${p.stock})">
        <div style="font-size:22px;margin-bottom:4px;">📦</div>
        <div class="psi-name">${p.nombre}</div>
        <div class="psi-stock">Stock: ${p.stock}</div>
        ${agregado ? '<div style="font-size:10px;color:var(--success);">Agregado ✅</div>' : ''}
      </div>`;
    }
  }).join('');
}

async function seleccionarVarianteMerma(prodId, prodNombre) {
  try {
    const datos = await obtenerVariantesProducto(prodId);
    const vars = datos.variantes.filter(v => v.activo);
    const cont = $('productos-para-merma');
    cont.innerHTML = `
      <div style="grid-column: 1 / -1; margin-bottom: 8px;">
        <button class="btn btn-outline btn-sm" onclick="filtrarProductosMerma()">⬅️ Volver</button>
      </div>
    ` + vars.map(v => {
      const etiq = v.attr2_valor ? `${v.attr1_valor} / ${v.attr2_valor}` : v.attr1_valor;
      const key = `var_${v.id}`;
      const agregado = !!itemsMerma[key];
      return `
      <div class="product-select-item ${agregado ? 'added' : ''}" onclick="agregarAMerma(${prodId}, ${v.id}, '${prodNombre} - ${etiq}', ${v.stock})">
        <div style="font-size:22px;margin-bottom:4px;">🏷️</div>
        <div class="psi-name">${etiq}</div>
        <div class="psi-stock">Stock: ${v.stock}</div>
      </div>`;
    }).join('');
  } catch (e) { toast(e.message, 'error'); }
}

function agregarAMerma(prodId, varId, nombre, stock) {
  const key = varId ? `var_${varId}` : `prod_${prodId}`;
  if (!itemsMerma[key]) {
    itemsMerma[key] = { producto_id: prodId, variante_id: varId, nombre: nombre, cantidad: 1, stock_max: stock };
  }
  renderItemsMerma();
  filtrarProductosMerma();
}

function renderItemsMerma() {
  const cont = $('merma-items');
  const items = Object.entries(itemsMerma);
  if (!items.length) { cont.innerHTML = '<p style="text-align:center; padding:10px; font-size:13px; color:#999;">Agrega productos arriba</p>'; return; }
  
  cont.innerHTML = items.map(([key, item]) => `
    <div class="cart-item">
      <div style="flex:1;">
        <div class="cart-name">${item.nombre}</div>
      </div>
      <div style="display:flex; align-items:center; gap:8px;">
        <input type="number" class="form-input" style="width:60px; padding:4px;" value="${item.cantidad}" min="1" max="${item.stock_max}" onchange="itemsMerma['${key}'].cantidad = parseInt(this.value)">
        <button class="btn btn-outline btn-sm" style="color:var(--danger); border:none;" onclick="delete itemsMerma['${key}']; renderItemsMerma(); filtrarProductosMerma();">❌</button>
      </div>
    </div>
  `).join('');
}

async function confirmarMerma() {
  const motivo = $('merma-motivo').value.trim();
  if (!motivo) { toast('Indique el motivo', 'error'); return; }
  const items = Object.values(itemsMerma).map(i => ({
    producto_id: i.producto_id,
    variante_id: i.variante_id,
    cantidad: i.cantidad
  }));
  if (!items.length) { toast('No hay items seleccionados', 'error'); return; }
  
  try {
    await api('POST', '/api/inventario/merma', { items, motivo });
    toast('Merma registrada correctamente');
    cerrarModales();
    cargarInventario();
  } catch (e) { toast(e.message, 'error'); }
}

