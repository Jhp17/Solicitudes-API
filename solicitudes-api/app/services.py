"""Conectores con Excel Online (Microsoft Graph) y con el Bot de Telegram.

Cada servicio cuenta sus exitos y errores en `stats`, que se consulta en /stats
y sirve como evidencia durante las pruebas de carga.
"""
import asyncio
import os
import random
import time

import httpx

from . import config as c
FLOW_URL = os.getenv("EXCEL_FLOW_URL", "")
TELEGRAM_REAL = os.getenv("TELEGRAM_REAL", "false").lower() == "true"

COLUMNAS = ["ID", "Fecha", "Estudiante", "Correo", "Tipo", "Descripcion", "Estado"]

stats = {k: 0 for k in (
    "excel_ok", "excel_error", "excel_reintentos",
    "telegram_ok", "telegram_error", "telegram_reintentos")}

_client = httpx.AsyncClient(timeout=c.TIMEOUT, limits=httpx.Limits(max_connections=300))
_token = {"valor": None, "expira": 0.0}
_lock_token = asyncio.Lock()

# Estado interno del modo SIMULAR
_sim_filas: list[list] = []
_sim_activas = {"excel": 0, "telegram": 0}


class ServicioError(Exception):
    def __init__(self, servicio, status, detalle="", retry_after=None):
        super().__init__(f"{servicio} {status}: {detalle}")
        self.servicio, self.status, self.retry_after = servicio, status, retry_after


async def cerrar():
    await _client.aclose()


# ---------------------------------------------------------------- utilidades
async def _req(servicio, metodo, url, **kw):
    try:
        r = await _client.request(metodo, url, **kw)
    except httpx.HTTPError as e:                      # timeout, conexion caida, etc.
        raise ServicioError(servicio, 0, type(e).__name__)
    if r.status_code >= 400:
        espera = r.headers.get("Retry-After")
        try:
            espera = espera or r.json().get("parameters", {}).get("retry_after")
        except Exception:
            pass
        raise ServicioError(servicio, r.status_code, r.text[:200], float(espera) if espera else None)
    return r


async def _con_reintentos(servicio, fn, reintentos):
    """Reintenta con espera creciente (respeta Retry-After). Con reintentos=0 no reintenta."""
    for intento in range(reintentos + 1):
        try:
            return await fn()
        except ServicioError as e:
            transitorio = e.status in (0, 409, 423, 429, 500, 502, 503, 504)
            if not transitorio or intento == reintentos:
                raise
            stats[f"{servicio}_reintentos"] += 1
            await asyncio.sleep(e.retry_after or min(2 ** intento, 30) + random.random())


async def _simular(servicio, limite, base):
    """Simula un servicio externo que se satura al superar `limite` llamadas simultaneas."""
    _sim_activas[servicio] += 1
    try:
        n = _sim_activas[servicio]
        await asyncio.sleep(base + 0.04 * n + random.random() * 0.1)
        if n > limite and random.random() < min(0.9, (n - limite) / limite):
            raise ServicioError(servicio, 429, "simulado", retry_after=1)
    finally:
        _sim_activas[servicio] -= 1


# --------------------------------------------------------------------- Excel
async def _token_graph():
    if _token["valor"] and time.time() < _token["expira"] - 60:
        return _token["valor"]
    async with _lock_token:
        if _token["valor"] and time.time() < _token["expira"] - 60:
            return _token["valor"]
        r = await _req("excel", "POST",
                       f"https://login.microsoftonline.com/{c.TENANT_ID}/oauth2/v2.0/token",
                       data={"client_id": c.CLIENT_ID, "client_secret": c.CLIENT_SECRET,
                             "scope": "https://graph.microsoft.com/.default",
                             "grant_type": "client_credentials"})
        j = r.json()
        _token.update(valor=j["access_token"], expira=time.time() + int(j["expires_in"]))
        return _token["valor"]


def _base_tabla():
    return (f"https://graph.microsoft.com/v1.0/users/{c.EXCEL_USER}/drive/root:/"
            f"{c.EXCEL_FILE_PATH}:/workbook/tables/{c.EXCEL_TABLE}")


async def _graph(metodo, sufijo, **kw):
    token = await _token_graph()
    return await _req("excel", metodo, _base_tabla() + sufijo,
                      headers={"Authorization": f"Bearer {token}"}, **kw)


async def excel_agregar(filas, reintentos=0):
    """Agrega una o varias filas al final de la tabla."""
    async def fn():
        if FLOW_URL:
            for f in filas:
                await _req("excel", "POST", FLOW_URL,
                           json=dict(zip(["id", "fecha", "estudiante", "correo",
                                          "tipo", "descripcion", "estado"], f)))
            _sim_filas.extend(filas)
        elif c.SIMULAR:
            await _simular("excel", 15, 0.35)
            _sim_filas.extend(filas)
        else:
            await _graph("POST", "/rows/add", json={"values": filas})
    try:
        await _con_reintentos("excel", fn, reintentos)
        stats["excel_ok"] += len(filas)
    except ServicioError:
        stats["excel_error"] += len(filas)
        raise


async def _filas_con_indice(reintentos=0):
    async def fn():
        if c.SIMULAR and not TELEGRAM_REAL:
            await _simular("excel", 15, 0.2)
            return [{"index": i, "values": [f]} for i, f in enumerate(_sim_filas)]
        r = await _graph("GET", "/rows")
        return r.json().get("value", [])
    return await _con_reintentos("excel", fn, reintentos)


def _a_dict(valores):
    return {k.lower(): v for k, v in zip(COLUMNAS, valores)}


async def excel_listar(reintentos=0):
    filas = await _filas_con_indice(reintentos)
    return [_a_dict(f["values"][0]) for f in filas if f["values"][0][0]]


async def excel_actualizar_estado(id_, estado, reintentos=0):
    """Devuelve la solicitud actualizada o None si el ID no existe."""
    for f in await _filas_con_indice(reintentos):
        valores = list(f["values"][0])
        if valores[0] == id_:
            valores[COLUMNAS.index("Estado")] = estado
            async def fn():
                if c.SIMULAR and not TELEGRAM_REAL:
                    await _simular("excel", 15, 0.2)
                    _sim_filas[f["index"]] = valores
                else:
                    await _graph("PATCH", f"/rows/itemAt(index={f['index']})", json={"values": [valores]})
            await _con_reintentos("excel", fn, reintentos)
            return _a_dict(valores)
    return None


# ------------------------------------------------------------------ Telegram
async def telegram_enviar(texto, cantidad=1, reintentos=0):
    """Envia un mensaje. `cantidad` = solicitudes que resume (para las estadisticas)."""
    async def fn():
        if c.SIMULAR and not TELEGRAM_REAL:
            await _simular("telegram", 5, 0.15)
        else:
            await _req("telegram", "POST",
                       f"https://api.telegram.org/bot{c.TELEGRAM_BOT_TOKEN}/sendMessage",
                       json={"chat_id": c.TELEGRAM_CHAT_ID, "text": texto, "parse_mode": "HTML"})
    try:
        await _con_reintentos("telegram", fn, reintentos)
        stats["telegram_ok"] += cantidad
    except ServicioError:
        stats["telegram_error"] += cantidad
        raise
