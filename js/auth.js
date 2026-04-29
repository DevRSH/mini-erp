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
