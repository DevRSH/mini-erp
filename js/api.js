// ===============================
// INICIO APP
// ===============================
window.addEventListener("load", async () => {
  console.log("App iniciando...");

  try {
    await cargarDashboard();
    await cargarProductos();
    await cargarVentas();
  } catch (e) {
    console.error("Error inicial:", e);
  }
});


// ===============================
// CARGAR VENTAS
// ===============================
async function cargarVentas() {
  try {
    const res = await fetch("/api/ventas");

    if (!res.ok) {
      throw new Error("Error al obtener ventas");
    }

    const data = await res.json();
    renderVentas(data);

  } catch (error) {
    console.error("Error cargando ventas:", error);
  }
}


// ===============================
// RENDER VENTAS
// ===============================
function renderVentas(ventas) {
  const contenedor = document.getElementById("ventas");

  if (!contenedor) {
    console.error("No existe el contenedor #ventas");
    return;
  }

  contenedor.innerHTML = "";

  ventas.forEach(v => {
    const fila = document.createElement("div");

    fila.innerHTML = `
      <p>ID: ${v.id} | Total: ${v.total}</p>
      <button onclick="editarVenta(${v.id})">Editar</button>
      <button onclick="eliminarVenta(${v.id})">Eliminar</button>
    `;

    contenedor.appendChild(fila);
  });
}


// ===============================
// EDITAR VENTA (placeholder)
// ===============================
function editarVenta(id) {
  console.log("Editar venta:", id);
}


// ===============================
// ELIMINAR VENTA
// ===============================
async function eliminarVenta(id) {
  if (!confirm("¿Eliminar venta?")) return;

  try {
    const res = await fetch(`/api/ventas/${id}/cancelar`, {
      method: "POST"
    });

    if (!res.ok) {
      throw new Error("No se pudo eliminar");
    }

    await cargarVentas();

  } catch (error) {
    console.error("Error eliminando:", error);
  }
}