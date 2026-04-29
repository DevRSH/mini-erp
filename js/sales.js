async function cargarVentas() {
    const ventas = await getSales();
    renderVentas(ventas);
  }
  
  async function crearVenta() {
    const total = document.getElementById("total").value;
  
    await createSale({
      total: parseFloat(total)
    });
  
    cargarVentas();
  }
  
  async function editarVenta(id) {
    const nuevoTotal = prompt("Nuevo total:");
  
    if (!nuevoTotal) return;
  
    await updateSale(id, {
      total: parseFloat(nuevoTotal)
    });
  
    cargarVentas();
  }
  
  async function eliminarVenta(id) {
    if (!confirm("¿Eliminar venta?")) return;
  
    await deleteSale(id);
    cargarVentas();
  }