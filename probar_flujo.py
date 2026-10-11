import httpx

vals = {}
for linea in open(".env", encoding="utf-8"):
    linea = linea.strip()
    if linea and not linea.startswith("#") and "=" in linea:
        k, v = linea.split("=", 1)
        vals[k.strip()] = v.strip().strip('"')

r = httpx.post(
    vals["EXCEL_FLOW_URL"],
    json={"id": "PRUEBA1", "fecha": "2026-10-10", "estudiante": "Jose Perez",
          "correo": "jose.perez@example.com", "tipo": "Certificación",
          "descripcion": "Prueba directa al flujo", "estado": "Pendiente"},
    timeout=30,
)
print(r.status_code, r.text[:300])