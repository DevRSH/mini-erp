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
