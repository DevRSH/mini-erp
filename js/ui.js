function renderVentas(ventas) {
    const contenedor = document.getElementById("ventas");
  
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
  
  // cargar al inicio
  window.onload = cargarVentas;