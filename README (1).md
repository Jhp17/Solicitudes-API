# API de Solicitudes Académicas

API REST en **FastAPI** que registra solicitudes de estudiantes (certificaciones, homologaciones, cancelaciones de materia, reintegros y otras), las guarda en **Excel Online** (Microsoft 365 / OneDrive) y avisa por **Telegram** cada vez que llega una nueva. Incluye una página web, un script de pruebas de carga y una versión mejorada para comparar resultados antes y después.

- **Aplicación publicada:** [COMPLETAR: URL]
- **Documentación interactiva (Swagger):** [COMPLETAR: URL]/docs

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

Tipos válidos: `Certificación`, `Homologación`, `Cancelación de materia`, `Reintegro`, `Otro`.

## Estructura

```
app/main.py        endpoints, colas y trabajadores del modo mejorado
app/services.py    conectores de Excel (Power Automate / Microsoft Graph) y Telegram, reintentos y contadores
app/models.py      validación de datos
app/config.py      variables de entorno
app/static/        página web
scripts/prueba_carga.py   pruebas de carga
```

## 1. Instalación

Requiere Python 3.10 o superior.

```bash
python -m venv venv
venv\Scripts\activate          # Windows   (Linux/Mac: source venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env         # Linux/Mac: cp .env.example .env
```

Luego abre `.env` y completa los valores (secciones 2 a 4). **Nunca subas `.env` a GitHub.**

## 2. Preparar Excel Online

1. En OneDrive crea un libro **Solicitudes.xlsx**.
2. En la fila 1 escribe estos encabezados, exactamente y en este orden: `ID | Fecha | Estudiante | Correo | Tipo | Descripcion | Estado`.
3. Selecciona los encabezados → **Insertar → Tabla** (marca «La tabla tiene encabezados») → en *Diseño de tabla* ponle el nombre **Solicitudes**.
4. En `.env` completa `EXCEL_USER` (correo del dueño del OneDrive), `EXCEL_FILE_PATH` y `EXCEL_TABLE`.

## 3. Conectar la API con Excel

Hay dos formas. Elige una.

### Opción A: flujo de Power Automate (la que usa este proyecto)

Sirve para **agregar filas** (`POST /solicitudes`).

1. En Power Automate crea un flujo **instantáneo** con el desencadenador *Cuando se recibe una solicitud HTTP*.
2. En el esquema JSON del cuerpo define los campos de tipo texto: `id`, `fecha`, `estudiante`, `correo`, `tipo`, `descripcion`, `estado`.
3. Agrega la acción **Excel Online (Empresa) → Agregar una fila a una tabla**, selecciona `Solicitudes.xlsx` y la tabla `Solicitudes`, y asigna cada columna con el campo correspondiente del paso 2.
4. Guarda el flujo, copia la **URL HTTP POST** generada y pégala en `.env` como `EXCEL_FLOW_URL`.

> La URL del flujo es un secreto: quien la tenga puede escribir en tu Excel. No la publiques.

Con este método, `GET /solicitudes` y `PUT /solicitudes/{id}` siguen usando Microsoft Graph, por lo que necesitan las credenciales de la opción B.

### Opción B: Microsoft Graph (registro de aplicación en Entra ID)

1. Entra a <https://entra.microsoft.com> → **Aplicaciones → Registros de aplicaciones → Nuevo registro**.
2. Copia el **Id. de directorio (inquilino)** → `AZURE_TENANT_ID` y el **Id. de aplicación (cliente)** → `AZURE_CLIENT_ID`.
3. **Certificados y secretos → Nuevo secreto de cliente** → copia el *Valor* → `AZURE_CLIENT_SECRET`.
4. **Permisos de API → Agregar → Microsoft Graph → Permisos de aplicación → `Files.ReadWrite.All`** y pulsa **Conceder consentimiento de administrador**.

> Requiere una cuenta **institucional (trabajo o escuela)** de Microsoft 365. Si tu cuenta no puede conceder el consentimiento, pídelo al administrador del inquilino. Si dejas `EXCEL_FLOW_URL` vacío, la API también agrega las filas directamente con Graph.

## 4. Crear el Bot de Telegram

1. En Telegram habla con **@BotFather** → `/newbot` → copia el token → `TELEGRAM_BOT_TOKEN`.
2. Abre tu bot y envíale cualquier mensaje (o agrégalo a un grupo y escribe allí).
3. Visita `https://api.telegram.org/bot<TOKEN>/getUpdates` y copia `chat.id` → `TELEGRAM_CHAT_ID`.
4. Pon `TELEGRAM_REAL=true` para enviar mensajes reales.

La integración actual **solo envía avisos** al chat configurado; no lee mensajes ni responde como chatbot.

## 5. Ejecutar

```bash
uvicorn app.main:app --reload
```

Abre <http://localhost:8000> (web) o <http://localhost:8000/docs> (Swagger).

**Sin credenciales** puedes practicar con `SIMULAR=true`: Excel y Telegram se simulan en memoria. Sirve para desarrollar, **no** como evidencia: el informe debe usar los servicios reales.

Combinaciones útiles de variables:

| Objetivo | Variables |
|---|---|
| Todo simulado (desarrollo) | `SIMULAR=true`, `TELEGRAM_REAL=false` |
| Telegram real, Excel por flujo | `SIMULAR=true`, `TELEGRAM_REAL=true`, `EXCEL_FLOW_URL=<url>` |
| Todo real con Graph | `SIMULAR=false`, credenciales de Azure completas |

## 6. Pruebas de carga

Con la API corriendo (idealmente ya publicada), desde la carpeta que contiene `app/` y `scripts/`:

```bash
python scripts/prueba_carga.py --url https://TU-APP.onrender.com --n 10 25 50 100 --etiqueta base
```

El script lanza N solicitudes simultáneas y muestra tiempo medio, p95 y máximo, exitosas, errores, códigos HTTP y los contadores de Excel y Telegram. Guarda todo en `resultados_carga.csv`.

Después de cada prueba revisa en Excel cuántas filas llegaron y en Telegram cuántos mensajes recibiste, y compáralos con los contadores de `/stats`.

## 7. Versión mejorada (antes / después)

Cambia en `.env` (o en las variables del servicio publicado) `MODO=mejorado` y repite la prueba con `--etiqueta mejorada`.

| | `MODO=simple` | `MODO=mejorado` |
|---|---|---|
| Respuesta al usuario | Espera a Excel y a Telegram (201) | Inmediata, procesa en segundo plano (202) |
| Escritura en Excel | Una llamada por solicitud | Lotes de hasta 25 filas por llamada |
| Errores 429 / 5xx | Se pierden | Reintentos con espera creciente y respeto de `Retry-After` |
| Telegram | Un mensaje por solicitud | Mensajes agrupados con pausa entre envíos |
| Lecturas | Siempre consulta Excel | Caché de 5 s |

En modo mejorado, `t_hasta_procesar_todo_s` indica cuánto tardó realmente en terminar Excel y Telegram, más allá de la respuesta rápida al usuario.

## 8. Publicar

Ejemplo con **Render** (plan gratuito): crea un *Web Service* desde tu repositorio de GitHub.

- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- En *Environment* agrega las variables de `.env.example` con sus valores reales.

El plan gratuito se duerme tras un rato sin uso; haz una petición a `/health` antes de la sustentación.

## Seguridad

- `.env` está en `.gitignore`: **nunca** subas tokens, secretos, contraseñas ni la URL del flujo.
- Si un secreto se filtra, revócalo y crea uno nuevo (BotFather: `/revoke`; Entra ID: nuevo secreto; Power Automate: regenera la URL del flujo).
- La API no tiene autenticación de usuarios. Es suficiente para esta actividad, pero no para producción.
- Las celdas que empiezan con `=`, `+`, `-` o `@` se neutralizan para evitar inyección de fórmulas en Excel.
- Limitación conocida: en modo mejorado la cola vive en memoria; si el servicio se reinicia, las solicitudes en cola se pierden.
