const API_URL = "http://localhost:8000"; // ajusta si es necesario

async function getSales() {
  const res = await fetch(`${API_URL}/sales`);
  return await res.json();
}

async function createSale(data) {
  await fetch(`${API_URL}/sales`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(data)
  });
}

async function updateSale(id, data) {
  await fetch(`${API_URL}/sales/${id}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(data)
  });
}

async function deleteSale(id) {
  await fetch(`${API_URL}/sales/${id}`, {
    method: "DELETE"
  });
}