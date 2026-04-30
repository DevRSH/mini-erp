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

  cont.innerHTML = eventos.map(e => {
    const isCancel = e.tipo === 'cancelacion';
    const hasMonto = e.monto !== null && e.monto !== undefined;
    const hasItems = e.items && e.items.length > 0;
    
    return `
    <div class="card timeline-card" onclick="toggleTimelineDetail(this)" style="margin-bottom:12px; border-left: 4px solid ${isCancel ? 'var(--danger)' : 'var(--primary)'}">
      <div class="timeline-header">
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
        <div style="display:flex; flex-direction:column; align-items:flex-end; gap:4px;">
          ${hasMonto ? `<div style="font-weight:700; font-size:16px;">${fmt(e.monto)}</div>` : ''}
          <div class="timeline-arrow">▼</div>
        </div>
      </div>
      
      <div class="timeline-details">
        <ul class="timeline-items-list">
          ${hasItems ? e.items.map(it => `<li class="timeline-item-detail">${escapeHtml(it)}</li>`).join('') : '<li class="timeline-empty-detail">Sin detalles adicionales</li>'}
        </ul>
      </div>
    </div>`;
  }).join('');
}

function toggleTimelineDetail(card) {
  const allCards = document.querySelectorAll('.timeline-card');
  const isExpanded = card.classList.contains('expanded');
  
  // Opcional: Cerrar otros si quieres estilo acordeón, pero mejor dejar que abran varios
  // allCards.forEach(c => c.classList.remove('expanded'));
  
  if (isExpanded) {
    card.classList.remove('expanded');
  } else {
    card.classList.add('expanded');
  }
}
