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
