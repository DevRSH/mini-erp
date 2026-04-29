import os

path = "js/app.js"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Destination files
files = {
    "auth.js": [],
    "globals.js": [],
    "dashboard.js": [],
    "inventory.js": [],
    "scanner.js": [],
    "sales.js": [],
    "history.js": [],
    "reports.js": [],
    "purchases.js": [],
    "main.js": [], # will hold init/pwa
}

# Routing logic
current_file = "auth.js" # starts with auth since line 2 is AUTH

for line in lines:
    if "AUTENTICACIÓN" in line:
        current_file = "auth.js"
    elif "ESTADO GLOBAL" in line or "UTILIDADES" in line or "NAVEGACIÓN" in line:
        current_file = "globals.js"
    elif "DASHBOARD" in line:
        current_file = "dashboard.js"
    elif "INVENTARIO" in line or "CREAR PRODUCTO" in line or "EDITAR PRODUCTO" in line or "VARIANTES" in line or "AJUSTE STOCK" in line or "ELIMINAR PRODUCTO" in line:
        if "INVENTARIO" in line and current_file == "globals.js": # first INVENTARIO match
            current_file = "inventory.js"
        elif "INVENTARIO" not in line:
            current_file = "inventory.js"
    elif "ESCÁNER" in line:
        current_file = "scanner.js"
    elif "VENTAS —" in line or "Cargar variantes para productos" in line:
        current_file = "sales.js"
    elif "HISTORIAL" in line:
        current_file = "history.js"
    elif "REPORTES" in line or "EXPORTACIÓN" in line:
        current_file = "reports.js"
    elif "COMPRAS" in line:
        current_file = "purchases.js"
    elif "SERVICE WORKER" in line or "INICIO" in line:
        current_file = "main.js"

    files[current_file].append(line)

# Write out the files
for name, content in files.items():
    with open(f"js/{name}", "w", encoding="utf-8") as f:
        f.writelines(content)
    print(f"Created js/{name} with {len(content)} lines")

# Let's rename app.js to app.js.backup so it doesn't conflict
os.rename("js/app.js", "js/app.js.backup")
print("Renamed js/app.js to js/app.js.backup")
