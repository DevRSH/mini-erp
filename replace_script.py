import sys

path = "tests/test_api_flows.py"
with open(path, "r") as f:
    content = f.read()

replacements = [
    ("main.ProductoCrear", "schemas.ProductoCrear"),
    ("main.VarianteCrear", "schemas.VarianteCrear"),
    ("main.CompraCrear", "schemas.CompraCrear"),
    ("main.ItemCompra", "schemas.ItemCompra"),
    ("main.VentaCrear", "schemas.VentaCrear"),
    ("main.ItemVenta", "schemas.ItemVenta"),
    ("main.VentaCorreccion", "schemas.VentaCorreccion"),
    ("main.CompraCorreccion", "schemas.CompraCorreccion"),
    ("main.AjusteStock", "schemas.AjusteStock"),
    ("main.AjusteVariante", "schemas.AjusteVariante"),
    ("main.VarianteEditar", "schemas.VarianteEditar"),
    ("main.ProductoEditar", "schemas.ProductoEditar"),
]

for old, new in replacements:
    content = content.replace(old, new)

with open(path, "w") as f:
    f.write(content)

print("Replaced all schemas successfully.")
