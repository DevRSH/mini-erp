import re
import os

path = "js/app.js"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Define boundaries using exact string matching based on the file content.
sections = [
    ("auth.js", "AUTENTICACIÓN — PIN", "ESTADO GLOBAL"),
    ("globals.js", "ESTADO GLOBAL", "NAVEGACIÓN"),
    ("nav.js", "NAVEGACIÓN", "DASHBOARD"),
    ("dashboard.js", "DASHBOARD", "INVENTARIO Y PRODUCTOS"),
    ("inventory.js", "INVENTARIO Y PRODUCTOS", "VARIANTES (SPRINT 4)"),
    ("variants.js", "VARIANTES (SPRINT 4)", "VENTAS (PUNTO DE VENTA)"),
    ("sales.js", "VENTAS (PUNTO DE VENTA)", "COMPRAS (INGRESO DE STOCK)"),
    ("purchases.js", "COMPRAS (INGRESO DE STOCK)", "HISTORIAL (VENTAS Y COMPRAS)"),
    ("history.js", "HISTORIAL (VENTAS Y COMPRAS)", "INICIALIZACIÓN"),
    ("init.js", "INICIALIZACIÓN", None)
]

# We need to find the headers exactly to split.
# Let's search for the headers.
import sys

def find_header_index(header):
    if not header:
        return len(content)
    # The header is inside a comment block like:
    # // ═══════════════════════════════════════════
    # // HEADER
    # // ═══════════════════════════════════════════
    idx = content.find(header)
    if idx == -1:
        print(f"Header not found: {header}")
        sys.exit(1)
    
    # find the preceding // ═══════════════════════════════════════════
    preceding = content.rfind("// ════", 0, idx)
    if preceding != -1:
        return preceding
    return idx

for i in range(len(sections)):
    filename, start_head, end_head = sections[i]
    start_idx = find_header_index(start_head)
    end_idx = find_header_index(end_head)
    
    section_content = content[start_idx:end_idx]
    
    # write to js/filename
    with open(f"js/{filename}", "w", encoding="utf-8") as out:
        out.write(section_content)
    print(f"Created js/{filename} ({len(section_content)} bytes)")

print("Done splitting.")
