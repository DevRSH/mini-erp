// ═══════════════════════════════════════════
// DASHBOARD
// ═══════════════════════════════════════════
let chartVentas = null;

async function cargarDashboard() {
  try {
    const [res, top, sb, diarias] = await Promise.all([
      api('GET', '/api/reportes/resumen?periodo=hoy'),
      api('GET', '/api/reportes/mas-vendidos?limite=5'),
      api('GET', '/api/reportes/stock-bajo'),
      api('GET', '/api/reportes/ventas-diarias?dias=7')
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

    // ── Gráfica de ventas ──
    renderChartVentas(diarias);

    // ── Notificaciones emergentes de stock bajo ──
    mostrarNotificacionesStock(sb);

    // ── Top productos ──
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
// GRÁFICA DE VENTAS (Chart.js)
// ═══════════════════════════════════════════
function renderChartVentas(diarias) {
  const canvas = $('chart-ventas-semana');
  if (!canvas) return;

  // Generar los últimos 7 días como labels
  const hoy = new Date();
  const dias = [];
  for (let i = 6; i >= 0; i--) {
    const d = new Date(hoy);
    d.setDate(d.getDate() - i);
    dias.push(d.toISOString().split('T')[0]);
  }

  // Mapear datos de la API a cada día
  const mapaVentas = {};
  const mapaIngresos = {};
  diarias.forEach(d => {
    mapaVentas[d.fecha] = d.total_ventas;
    mapaIngresos[d.fecha] = d.ingresos;
  });

  const labels = dias.map(d => {
    const parts = d.split('-');
    return `${parts[2]}/${parts[1]}`;
  });
  const dataVentas = dias.map(d => mapaVentas[d] || 0);
  const dataIngresos = dias.map(d => mapaIngresos[d] || 0);

  // Destruir chart anterior si existe
  if (chartVentas) {
    chartVentas.destroy();
    chartVentas = null;
  }

  const ctx = canvas.getContext('2d');

  // Gradiente para barras
  const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
  gradient.addColorStop(0, 'rgba(232, 130, 26, 0.8)');
  gradient.addColorStop(1, 'rgba(232, 130, 26, 0.15)');

  // Gradiente para línea
  const gradientLine = ctx.createLinearGradient(0, 0, 0, canvas.height);
  gradientLine.addColorStop(0, 'rgba(27, 58, 107, 0.4)');
  gradientLine.addColorStop(1, 'rgba(27, 58, 107, 0.02)');

  chartVentas = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        {
          label: 'Ingresos ($)',
          data: dataIngresos,
          backgroundColor: gradient,
          borderColor: '#E8821A',
          borderWidth: 2,
          borderRadius: 8,
          borderSkipped: false,
          yAxisID: 'y',
          order: 2,
        },
        {
          label: 'Ventas (#)',
          data: dataVentas,
          type: 'line',
          borderColor: '#1B3A6B',
          backgroundColor: gradientLine,
          fill: true,
          tension: 0.4,
          pointRadius: 5,
          pointBackgroundColor: '#1B3A6B',
          pointBorderColor: '#fff',
          pointBorderWidth: 2,
          pointHoverRadius: 7,
          yAxisID: 'y1',
          order: 1,
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: 'index',
        intersect: false,
      },
      plugins: {
        legend: {
          display: true,
          position: 'top',
          labels: {
            font: { family: "'Outfit', sans-serif", size: 12 },
            usePointStyle: true,
            pointStyle: 'circle',
            padding: 16,
          }
        },
        tooltip: {
          backgroundColor: 'rgba(27, 58, 107, 0.95)',
          titleFont: { family: "'Outfit', sans-serif", size: 13 },
          bodyFont: { family: "'Outfit', sans-serif", size: 12 },
          padding: 12,
          cornerRadius: 10,
          callbacks: {
            label: function(ctx) {
              if (ctx.dataset.yAxisID === 'y') {
                return ` Ingresos: ${fmt(ctx.parsed.y)}`;
              }
              return ` Ventas: ${ctx.parsed.y}`;
            }
          }
        }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: {
            font: { family: "'Outfit', sans-serif", size: 11 },
            color: '#888',
          }
        },
        y: {
          position: 'left',
          beginAtZero: true,
          grid: { color: 'rgba(0,0,0,0.05)' },
          ticks: {
            font: { family: "'Outfit', sans-serif", size: 11 },
            color: '#E8821A',
            callback: v => '$' + v.toLocaleString('es-CL'),
          }
        },
        y1: {
          position: 'right',
          beginAtZero: true,
          grid: { display: false },
          ticks: {
            font: { family: "'Outfit', sans-serif", size: 11 },
            color: '#1B3A6B',
            stepSize: 1,
          }
        }
      }
    }
  });
}

// ═══════════════════════════════════════════
// NOTIFICACIONES EMERGENTES DE STOCK BAJO
// ═══════════════════════════════════════════
let notificacionesMostradas = false;

function mostrarNotificacionesStock(stockBajo) {
  // Solo mostrar una vez por sesión (al primer login)
  if (notificacionesMostradas || !stockBajo.length) return;
  notificacionesMostradas = true;

  // Crear el contenedor de notificaciones si no existe
  let notifContainer = $('notif-stock-container');
  if (!notifContainer) {
    notifContainer = document.createElement('div');
    notifContainer.id = 'notif-stock-container';
    notifContainer.style.cssText = `
      position:fixed; top:70px; right:12px; z-index:200;
      display:flex; flex-direction:column; gap:8px;
      max-width:320px; max-height:calc(100vh - 160px);
      overflow-y:auto; pointer-events:auto;
    `;
    document.body.appendChild(notifContainer);
  }

  // Agotados primero, luego stock bajo
  const agotados = stockBajo.filter(p => p.stock === 0);
  const bajos = stockBajo.filter(p => p.stock > 0);

  // Mostrar máximo 5 notificaciones
  const items = [...agotados, ...bajos].slice(0, 5);

  items.forEach((p, i) => {
    const esAgotado = p.stock === 0;
    const notif = document.createElement('div');
    notif.className = 'stock-notif';
    notif.style.cssText = `
      background: ${esAgotado ? '#FEF2F2' : '#FFFBEB'};
      border-left: 4px solid ${esAgotado ? '#DC2626' : '#F59E0B'};
      border-radius: 12px; padding: 12px 16px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.12);
      font-family: 'Outfit', sans-serif;
      animation: slideInRight 0.4s ease ${i * 0.12}s both;
      display: flex; align-items: flex-start; gap: 10px;
      cursor: pointer; transition: transform 0.2s, opacity 0.3s;
      pointer-events: auto;
    `;

    const icon = esAgotado ? '⛔' : '⚠️';
    const statusText = esAgotado ? 'Agotado' : `${p.stock} uds (mín. ${p.stock_minimo})`;

    notif.innerHTML = `
      <div style="font-size:20px;line-height:1;">${icon}</div>
      <div style="flex:1;min-width:0;">
        <div style="font-weight:700;font-size:13px;color:#1B3A6B;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${escapeHtml(p.nombre)}</div>
        <div style="font-size:12px;color:${esAgotado ? '#DC2626' : '#92400E'};margin-top:2px;">${statusText}</div>
      </div>
      <button onclick="this.parentElement.remove()" style="background:none;border:none;cursor:pointer;font-size:16px;color:#999;padding:0;line-height:1;">✕</button>
    `;

    // Click en la notificación → ir a inventario
    notif.addEventListener('click', (e) => {
      if (e.target.tagName === 'BUTTON') return;
      notifContainer.innerHTML = '';
      navTo('inventario');
    });

    notifContainer.appendChild(notif);
  });

  // Si hay más de 5, mostrar resumen
  if (stockBajo.length > 5) {
    const resumen = document.createElement('div');
    resumen.style.cssText = `
      background: #F0F4FF; border-radius: 10px; padding: 10px 14px;
      font-family: 'Outfit', sans-serif; font-size: 12px; color: #1B3A6B;
      text-align: center; cursor: pointer; font-weight: 600;
      animation: slideInRight 0.4s ease ${items.length * 0.12}s both;
      box-shadow: 0 2px 10px rgba(0,0,0,0.08);
    `;
    resumen.textContent = `+ ${stockBajo.length - 5} productos más con stock bajo`;
    resumen.addEventListener('click', () => {
      notifContainer.innerHTML = '';
      navTo('reportes');
    });
    notifContainer.appendChild(resumen);
  }

  // Auto-cerrar después de 8 segundos
  setTimeout(() => {
    if (notifContainer) {
      notifContainer.style.transition = 'opacity 0.5s';
      notifContainer.style.opacity = '0';
      setTimeout(() => { if (notifContainer.parentNode) notifContainer.remove(); }, 500);
    }
  }, 8000);
}

// ═══════════════════════════════════════════
// DESCARGAR RESPALDO
// ═══════════════════════════════════════════
function openModalBackup() {
  $('backup-clave').value = '';
  $('modal-backup').classList.add('open');
}

async function descargarBackup() {
  const clave = $('backup-clave').value.trim();
  if (!clave) { toast('Ingresa la clave de respaldo', 'error'); return; }
  try {
    const link = document.createElement('a');
    link.href = `/api/backup?clave=${encodeURIComponent(clave)}`;
    link.download = 'backup_erp.db';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    toast('Descarga iniciada 💾');
    cerrarModales();
  } catch (e) { toast(e.message, 'error'); }
}
