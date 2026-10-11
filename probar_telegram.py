import httpx

vals = {}
for linea in open(".env", encoding="utf-8"):
    linea = linea.strip()
    if linea and not linea.startswith("#") and "=" in linea:
        k, v = linea.split("=", 1)
        vals[k.strip()] = v.strip().strip('"')

r = httpx.post(
    f"https://api.telegram.org/bot{vals['TELEGRAM_BOT_TOKEN']}/sendMessage",
    json={"chat_id": vals["TELEGRAM_CHAT_ID"], "text": "Prueba desde mi script"},
)
print(r.status_code, r.text[:150])