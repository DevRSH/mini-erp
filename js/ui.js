// =========================
// INICIO APP
// =========================
window.onload = async function () {
    console.log("App iniciando...");
  
    try {
      navTo("dashboard");
      await cargarDashboard();
      await cargarProductos();
      await cargarVentas();
    } catch (e) {
      console.error("Error inicial:", e);
    }
  };
  
  
  // =========================
  // NAVEGACIÓN
  // =========================
  function navTo(page) {
    document.querySelectorAll(".page").forEach(p => {
      p.classList.remove("active");
    });
  
    const pageEl = document.getElementById(`page-${page}`);
    if (pageEl) pageEl.classList.add("active");
  
    document.querySelectorAll(".nav-btn").forEach(btn => {
      btn.classList.remove("active");
    });
  
    const btn = document.getElementById(`nav-${page}`);
    if (btn) btn.classList.add("active");
  }
  
  
  // =========================
  // DASHBOARD
  // =========================
  async function cargarDashboard() {
    document.getElementById("header-sub").innerText = "Sistema activo";
  
    document.getElementById("dash-ventas").innerText = "0";
    document.getElementById("dash-ingresos").innerText = "$0";
    document.getElementById("dash-ganancia").innerText = "$0";
    document.getElementById("dash-alertas").innerText = "0";
  }
  
  
  // =========================
  // PRODUCTOS
  // =========================
  async function cargarProductos() {
    const contenedor = document.getElementById("lista-productos");
    if (!contenedor) return;
  
    contenedor.innerHTML = "<p>Productos cargados (demo)</p>";
  }
  
  
  // =========================
  // VENTAS (HISTORIAL)
  // =========================
  async function cargarVentas() {
    const contenedor = document.getElementById("lista-ventas");
    if (!contenedor) return;
  
    try {
      const ventas = await getSales(); // viene de api.js
  
      renderVentas(ventas);
    } catch (e) {
      contenedor.innerHTML = "<p>Error cargando ventas</p>";
    }
  }
  
  
  // =========================
  // RENDER VENTAS
  // =========================
  function renderVentas(ventas) {
    const contenedor = document.getElementById("lista-ventas");
  
    contenedor.innerHTML = "";
  
    if (!ventas || ventas.length === 0) {
      contenedor.innerHTML = "<p>No hay ventas</p>";
      return;
    }
  
    ventas.forEach(v => {
      const fila = document.createElement("div");
  
      fila.className = "card";
      fila.style.marginBottom = "10px";
  
      fila.innerHTML = `
        <p><strong>ID:</strong> ${v.id}</p>
        <p><strong>Total:</strong> $${v.total}</p>
        <button class="btn btn-outline btn-sm" onclick="editarVenta(${v.id})">Editar</button>
        <button class="btn btn-danger btn-sm" onclick="eliminarVenta(${v.id})">Eliminar</button>
      `;
  
      contenedor.appendChild(fila);
    });
  }
  
  
  // =========================
  // FUNCIONES FALTANTES (PLACEHOLDER)
  // =========================
  function editarVenta(id) {
    alert("Editar venta ID: " + id);
  }
  
  function eliminarVenta(id) {
    alert("Eliminar venta ID: " + id);
  }