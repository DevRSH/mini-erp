import re

with open("js/app.js", "r", encoding="utf-8") as f:
    content = f.read()

# Remove the trailing </script>
content = content.replace("</script>", "")

# Update the fetch calls to include credentials
content = re.sub(
    r"(const res = await fetch\(path, opts\);)",
    r"opts.credentials = 'same-origin';\n      \1",
    content
)

# Also update the fetch in verificarSesion, enviarPin, cerrarSesion
content = content.replace("fetch('/api/sesion')", "fetch('/api/sesion', { credentials: 'same-origin' })")
content = content.replace("fetch('/api/login', {", "fetch('/api/login', {\n          credentials: 'same-origin',")
content = content.replace("fetch('/api/logout', { method: 'POST' })", "fetch('/api/logout', { method: 'POST', credentials: 'same-origin' })")

# Add window.cargarVentas = cargarHistorial to the end
content += "\n    // Alias para cargarVentas\n    window.cargarVentas = cargarHistorial;\n"

with open("js/app.js", "w", encoding="utf-8") as f:
    f.write(content.strip() + "\n")
