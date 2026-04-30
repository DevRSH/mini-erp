// ═══════════════════════════════════════════
// GESTIÓN DE PROVEEDORES (NIVEL 2)
// ═══════════════════════════════════════════

let todosProveedores = [];

async function cargarProveedores() {
  try {
    todosProveedores = await api('GET', '/api/proveedores');
    renderProveedoresSelects();
    renderProveedoresLista();
  } catch (e) { 
    console.error('Error proveedores:', e); 
    const cont = $('lista-proveedores-directorio') || $('lista-proveedores-crud');
    if (cont) cont.innerHTML = `<div class="alert-box danger" style="margin:10px;"><span>Error: ${e.message}</span></div>`;
  }
}

function renderProveedoresSelects() {
  const selects = [$('compra-proveedor-id')];
  const html = '<option value="">Seleccionar proveedor...</option>' + 
    todosProveedores.map(p => `<option value="${p.id}">${p.nombre}</option>`).join('');
  
  selects.forEach(s => { if(s) s.innerHTML = html; });
}

function renderProveedoresLista() {
  const cont = $('lista-proveedores-directorio') || $('lista-proveedores-crud');
  if (!cont) return;
  
  if (!todosProveedores.length) {
    cont.innerHTML = '<div class="empty-state" style="padding:20px 0;">No hay proveedores registrados</div>';
    return;
  }
  
  cont.innerHTML = todosProveedores.map(p => `
    <div style="margin-bottom:12px; padding-bottom:12px; border-bottom:1px solid #eee; display:flex; justify-content:space-between; align-items:center;">
      <div>
        <div style="font-weight:700; color:var(--primary);">${p.nombre}</div>
        <div style="font-size:12px; color:var(--muted);">${p.contacto || 'Sin contacto'}</div>
      </div>
      <div style="display:flex; gap:8px;">
        <button class="btn btn-outline btn-sm" style="padding:4px 8px;" onclick="openModalEditarProveedor(${p.id})">✏️</button>
        <button class="btn btn-outline btn-sm" style="padding:4px 8px; color:var(--danger);" onclick="eliminarProveedor(${p.id})">🗑️</button>
      </div>
    </div>
  `).join('');
}

function openModalListaProveedores() {
  cargarProveedores();
  $('modal-lista-proveedores').classList.add('open');
}

function openModalCrearProveedor() {
  $('proveedor-id').value = '';
  $('proveedor-nombre').value = '';
  $('proveedor-contacto').value = '';
  $('proveedor-modal-title').textContent = '🏢 Nuevo Proveedor';
  $('modal-proveedor').classList.add('open');
}

function openModalEditarProveedor(id) {
  const p = todosProveedores.find(x => x.id === id);
  if (!p) return;
  $('proveedor-id').value = p.id;
  $('proveedor-nombre').value = p.nombre;
  $('proveedor-contacto').value = p.contacto || '';
  $('proveedor-modal-title').textContent = '✏️ Editar Proveedor';
  $('modal-proveedor').classList.add('open');
}

async function guardarProveedor() {
  const id = $('proveedor-id').value;
  const data = {
    nombre: $('proveedor-nombre').value.trim(),
    contacto: $('proveedor-contacto').value.trim()
  };
  
  if (!data.nombre) { toast('Nombre requerido', 'error'); return; }
  
  try {
    if (id) {
      await api('PATCH', `/api/proveedores/${id}`, data);
      toast('Actualizado');
    } else {
      await api('POST', '/api/proveedores/', data);
      toast('Creado');
    }
    cerrarModales();
    cargarProveedores();
  } catch (e) { toast(e.message, 'error'); }
}

async function eliminarProveedor(id) {
  if (!confirm('¿Desactivar este proveedor?')) return;
  try {
    await api('DELETE', `/api/proveedores/${id}`);
    toast('Desactivado');
    cargarProveedores();
  } catch (e) { toast(e.message, 'error'); }
}
