# API de Solicitudes Académicas

API REST en **FastAPI** que registra solicitudes de estudiantes, las guarda en **Excel Online** (Microsoft 365 / OneDrive, vía Microsoft Graph) y avisa por **Telegram** cada vez que llega una nueva. Incluye una página web, un script de pruebas de carga y una versión mejorada para comparar resultados.

```
Usuario → Página web / API FastAPI → Procesamiento → Excel Online
                                                   → Bot de Telegram
```

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/solicitudes` | Registra una solicitud, la guarda en Excel y notifica por Telegram |
| GET | `/solicitudes` | Lista todas las solicitudes |
| GET | `/solicitudes/{id}` | Consulta una solicitud |
| PUT | `/solicitudes/{id}` | Cambia el estado (`Pendiente`, `En proceso`, `Resuelta`, `Rechazada`) |
| GET | `/stats` | Contadores de éxitos y errores de Excel y Telegram (evidencia para las pruebas) |
| GET | `/health` | Estado y modo de la API |
| GET | `/docs` | Documentación interactiva (Swagger) |
| GET | `/` | Página web con formulario y lista |

Ejemplo:
```bash
curl -X POST http://localhost:8000/solicitudes -H "Content-Type: application/json" \
  -d '{"estudiante":"Ana Pérez","correo":"ana@correo.edu.co","tipo":"Certificación","descripcion":"Certificado de notas"}'
```

## 1. Instalación

```bash
python -m venv venv
venv\Scripts\activate          # Windows   (Linux/Mac: source venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env         # Linux/Mac: cp .env.example .env
```

## 2. Preparar Excel Online

1. En OneDrive crea un libro **Solicitudes.xlsx**.
2. En la fila 1 escribe estos encabezados, **exactamente**: `ID | Fecha | Estudiante | Correo | Tipo | Descripcion | Estado`.
3. Selecciona los encabezados → **Insertar → Tabla** (marca «La tabla tiene encabezados») → en *Diseño de tabla* ponle el nombre **Solicitudes**.
4. Rellena en `.env`: `EXCEL_USER` (correo del dueño del OneDrive), `EXCEL_FILE_PATH` y `EXCEL_TABLE`.

## 3. Registrar la aplicación en Microsoft Entra ID

1. Entra a <https://entra.microsoft.com> → **Aplicaciones → Registros de aplicaciones → Nuevo registro**.
2. Copia el **Id. de directorio (inquilino)** → `AZURE_TENANT_ID` y el **Id. de aplicación (cliente)** → `AZURE_CLIENT_ID`.
3. **Certificados y secretos → Nuevo secreto de cliente** → copia el *Valor* → `AZURE_CLIENT_SECRET`.
4. **Permisos de API → Agregar → Microsoft Graph → Permisos de aplicación → `Files.ReadWrite.All`** y pulsa **Conceder consentimiento de administrador**.

> Requiere una cuenta **institucional (trabajo o escuela)** de Microsoft 365. Las cuentas personales de OneDrive no admiten este tipo de acceso. Si tu cuenta no puede conceder el consentimiento, pide al administrador del inquilino que lo haga.

## 4. Crear el Bot de Telegram

1. En Telegram habla con **@BotFather** → `/newbot` → copia el token → `TELEGRAM_BOT_TOKEN`.
2. Abre tu bot y envíale cualquier mensaje (o agrégalo a un grupo y escribe allí).
3. Visita `https://api.telegram.org/bot<TOKEN>/getUpdates` y copia `chat.id` → `TELEGRAM_CHAT_ID`.

## 5. Ejecutar

La integración actual de Telegram **solo envía avisos** al chat configurado; no lee mensajes ni responde como chatbot. Para conversar con el bot hace falta implementar una entrada (webhook o lectura de `getUpdates`).

```bash
uvicorn app.main:app --reload
```
Abre <http://localhost:8000> (web) o <http://localhost:8000/docs> (Swagger).

**Sin credenciales** puedes practicar con `SIMULAR=true`: Excel y Telegram se simulan en memoria. Sirve para desarrollar, **no** como evidencia: el informe debe usar los servicios reales.

Si configuras `TELEGRAM_REAL=true`, Telegram envía mensajes reales incluso con `SIMULAR=true`. `EXCEL_FLOW_URL` sirve para agregar filas mediante Power Automate, pero las consultas y cambios de estado siguen usando Microsoft Graph y requieren las credenciales de Azure de la sección 3. Si quieres guardar también directamente con Graph, deja `EXCEL_FLOW_URL` vacío; para usar ambos servicios reales configura además las credenciales y `SIMULAR=false`.

## 6. Pruebas de carga

Con la API corriendo (idealmente ya publicada):

```bash
python scripts/prueba_carga.py --url https://TU-APP.onrender.com --n 10 25 50 100 --etiqueta base
```
El script lanza N solicitudes simultáneas y muestra tiempo medio, p95 y máximo, exitosas, errores, códigos HTTP y los contadores de Excel y Telegram. Guarda todo en `resultados_carga.csv`.

Después de cada prueba revisa en Excel cuántas filas llegaron y en Telegram cuántos mensajes recibiste; compáralos con los contadores.

## 7. Versión mejorada (antes / después)

Cambia en `.env` (o en las variables del servicio publicado) `MODO=mejorado` y repite la prueba con `--etiqueta mejorada`.

| | `MODO=simple` | `MODO=mejorado` |
|---|---|---|
| Respuesta al usuario | Espera a Excel y a Telegram (201) | Inmediata, procesa en segundo plano (202) |
| Escritura en Excel | Una llamada por solicitud | Lotes de hasta 25 filas por llamada |
| Errores 429 / 5xx | Se pierden | Reintentos con espera creciente y respeto de `Retry-After` |
| Telegram | Un mensaje por solicitud | Mensajes agrupados con pausa entre envíos |
| Lecturas | Siempre consulta Excel | Caché de 5 s |

En modo mejorado `t_hasta_procesar_todo_s` indica cuánto tardó realmente en terminar Excel y Telegram, más allá de la respuesta rápida al usuario.

## 8. Publicar

Ejemplo con **Render** (gratuito): crea un *Web Service* desde tu repositorio de GitHub.
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- En *Environment* agrega las variables de `.env.example` con sus valores reales.

El plan gratuito se duerme tras un rato sin uso; haz una petición a `/health` antes de la sustentación.

## Seguridad

- `.env` está en `.gitignore`: **nunca** subas tokens, secretos ni contraseñas.
- Si un secreto se filtra, revócalo y crea uno nuevo (BotFather: `/revoke`; Entra ID: nuevo secreto).
- La API no tiene autenticación de usuarios, es suficiente para esta actividad pero no para producción.
- Las celdas que empiezan con `=`, `+`, `-` o `@` se neutralizan para evitar inyección de fórmulas en Excel.

## Estructura

```
app/main.py        endpoints, colas y trabajadores del modo mejorado
app/services.py    conectores de Microsoft Graph y Telegram, reintentos y contadores
app/models.py      validación de datos
app/config.py      variables de entorno
app/static/        página web
scripts/prueba_carga.py
```
