// ═══════════════════════════════════════════
// TIMELINE UNIFICADO
// ═══════════════════════════════════════════
let timelinePage = 1;

async function cargarTimeline() {
  const tipo = $('timeline-tipo').value;
  try {
    const res = await api('GET', `/api/timeline?tipo=${tipo}&page=${timelinePage}&limit=50`);
    renderTimeline(res.eventos);
  } catch (e) {
    $('lista-timeline').innerHTML = `<div class="empty-state">${escapeHtml(e.message)}</div>`;
  }
}

function renderTimeline(eventos) {
  const cont = $('lista-timeline');
  if (!eventos || !eventos.length) {
    cont.innerHTML = `
      <div class="empty-state" style="padding:40px 0;">
        <div class="empty-icon">⏳</div>
        <p>No hay eventos registrados</p>
      </div>`;
    return;
  }

  const html = eventos.map(e => {
    const isCancel = e.tipo === 'cancelacion';
    const hasMonto = e.monto !== null && e.monto !== undefined;
    return `
    <div class="card" style="margin-bottom:12px; border-left: 4px solid ${isCancel ? 'var(--danger)' : 'var(--primary)'}">
      <div style="display:flex; justify-content:space-between; align-items:flex-start;">
        <div style="display:flex; gap:12px;">
          <div style="font-size:24px;">${e.icono}</div>
          <div>
            <div style="font-weight:600; font-size:15px; color:${isCancel ? 'var(--danger)' : 'inherit'};">
              ${e.titulo}
            </div>
            <div style="font-size:13px; color:var(--muted); margin-top:2px;">
              ${e.descripcion}
            </div>
            <div style="font-size:11px; color:#aaa; margin-top:4px;">
              ${new Date(e.created_at).toLocaleString('es-CL')}
            </div>
          </div>
        </div>
        ${hasMonto ? `<div style="font-weight:700; font-size:16px;">${fmt(e.monto)}</div>` : ''}
      </div>
    </div>`;
  }).join('');

  cont.innerHTML = html;
}
