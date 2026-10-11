"""Configuracion leida desde variables de entorno (.env en local)."""
import os
from dotenv import load_dotenv

load_dotenv()


def _bool(nombre, defecto="false"):
    return os.getenv(nombre, defecto).strip().lower() in ("1", "true", "yes", "si")


MODO = os.getenv("MODO", "simple").strip().lower()      # simple | mejorado
SIMULAR = _bool("SIMULAR")

TENANT_ID = os.getenv("AZURE_TENANT_ID", "")
CLIENT_ID = os.getenv("AZURE_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET", "")
EXCEL_USER = os.getenv("EXCEL_USER", "")
EXCEL_FILE_PATH = os.getenv("EXCEL_FILE_PATH", "Solicitudes.xlsx")
EXCEL_TABLE = os.getenv("EXCEL_TABLE", "Solicitudes")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Ajustes de red y de la version mejorada
TIMEOUT = float(os.getenv("TIMEOUT", "20"))
REINTENTOS = int(os.getenv("REINTENTOS", "5"))            # solo en modo mejorado
LOTE_MAX = int(os.getenv("LOTE_MAX", "25"))               # filas por escritura a Excel
LOTE_ESPERA = float(os.getenv("LOTE_ESPERA", "0.5"))      # segundos para juntar un lote
TG_LOTE_MAX = int(os.getenv("TG_LOTE_MAX", "10"))         # solicitudes por mensaje
TG_INTERVALO = float(os.getenv("TG_INTERVALO", "1.2"))    # pausa entre mensajes
CACHE_TTL = float(os.getenv("CACHE_TTL", "5"))            # cache de lecturas (mejorado)
