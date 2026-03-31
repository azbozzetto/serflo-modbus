# HP550 Hydramotion — Sistema de Captura

Aplicación Python para captura continua de datos del viscosímetro HP550 Hydramotion vía broadcasting mode sobre RS-232, con dashboard web integrado para visualización en tiempo real, gestión de partidas de producción y persistencia de datos.

## Características

- Captura automática cada X segundos (configurable)
- Dashboard web con gráficos en tiempo real (Chart.js)
- Gestión de partidas de producción con eventos y muestras/lecturas
- Anotaciones en el gráfico: flags de eventos y marcadores de muestras
- Zoom interactivo con rueda del mouse; botón "Restablecer Zoom"
- Almacenamiento en SQLite y/o CSV
- Reconexión automática si se pierde la conexión serial
- Rotación automática de archivos CSV por día
- Logging completo de operaciones y errores
- Servicio systemd para ejecución continua en Linux

---

## Requisitos

### Hardware
- HP550 Hydramotion Viscometer
- Puerto serial RS-232 o adaptador USB-Serial (FTDI compatible)
- PC (Windows) o Raspberry Pi con Linux

### Software
- Python 3.7 o superior
- pip (gestor de paquetes Python)

---

## Instalación Rápida

1. **Instalar dependencias**
   ```bash
   pip install -r requirements.txt
   ```

   Dependencias:
   - pymodbus >= 3.0.0
   - pyserial >= 3.5
   - pyyaml >= 6.0
   - flask >= 3.0.0

2. **Configurar el HP550**

   En el dispositivo HP550, configurar:
   ```
   baud: 9600
   Par:  EVEN
   Addr: 01
   rS:   RS232
   bE:   ON    ← CRITICO (habilita transmision)
   Oph:  01    ← Recomendado (transmite VL + VC + Temp)
   ```

3. **Editar configuración**

   Editar `config/config.yaml` y ajustar:
   ```yaml
   serial:
     port: "COM9"              # Puerto serial (Linux: /dev/ttyUSB0)

   data_capture:
     enabled: true
     interval: 10              # Segundos entre capturas
     storage_type: "sqlite"    # "sqlite", "csv", o "both"

   web:
     port: 5000
   ```

---

## Uso

### Captura + Dashboard (modo normal)

```bash
python hp550_capture.py
```

Inicia simultáneamente:
- **Captura de datos** del HP550 via serial (hilo principal)
- **Dashboard web** en `http://<ip>:5000` (hilo secundario)

### Solo Dashboard (sin HP550 conectado)

```bash
python hp550_capture.py --web-only
```

Útil para revisar datos históricos sin necesidad del viscosímetro.

### Puerto personalizado

```bash
python hp550_capture.py --port 8080
```

### Exportar datos

```bash
python export_data.py --stats                                 # estadísticas
python export_data.py --recent 20                             # últimas 20 lecturas
python export_data.py --export datos.csv                      # exportar todo
python export_data.py --export ultimos_7_dias.csv --days 7   # últimos 7 días
```

---

## Dashboard Web

### Modos de vista

| Modo | Descripción |
|------|-------------|
| **Auto** | Vista en tiempo real, se actualiza automáticamente |
| **Partidas** | Selector de día/partida histórica; carga el día completo |
| **← →** | Navegar al día anterior / siguiente |

Por defecto, el dashboard carga en modo **Partidas** mostrando el día de hoy completo.

### Controles de tiempo (modo Auto)

Rangos rápidos: 30 min · 1 h · 6 h · 24 h · 7 d

### Zoom

- **Rueda del mouse** sobre el gráfico: zoom in/out centrado en el cursor
- **Botón "Restablecer Zoom"**: vuelve a la escala automática (siempre visible, a la derecha)

### Métricas en tiempo real

- Tarjetas: VL (cP), Temperatura (°C), VC (cP)
- Card de partida: número, artículo y fecha de la partida activa
- Estadísticas del período: promedio, mínimo, máximo
- Auto-refresh cada 10 segundos en modo Auto

### Anotaciones en el gráfico

| Tipo | Visual | Posición |
|------|--------|----------|
| **Eventos** | Línea vertical amarilla discontinua con etiqueta | Parte superior de la escala |
| **Muestras / Lecturas** | Globo de texto con callout hacia abajo | Parte inferior del área del gráfico |

Los botones **Eventos** y **Muestras & Lecturas** en la barra de controles permiten mostrar u ocultar cada tipo. Las anotaciones solo se muestran si el evento/muestra está dentro del rango de tiempo visible.

---

## Gestión de Partidas

Desde el panel lateral (botón `☰`):

### Nueva Partida
- Fecha, N° de partida, artículo
- Se crea en la base de datos; el selector de partidas se actualiza automáticamente

### Nuevo Evento
- Seleccionar partida, hora, temperatura, descripción del evento
- Aparece como flag en el gráfico

### Nueva Muestra / Lectura
- Seleccionar partida, hora, tipo (lectura / laboratorio), instrumento (pipeta / pico 5 / pico 7)
- Viscosidad y temperatura
- Aparece como globo en la parte inferior del gráfico

---

## API REST

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/readings?hours=1&limit=2000` | Lecturas en rango de tiempo |
| GET | `/api/readings?partida_id=<id>` | Todas las lecturas del día de la partida |
| GET | `/api/latest` | Última lectura válida |
| GET | `/api/stats?hours=24` | Estadísticas del período |
| GET | `/api/stats?partida_id=<id>` | Estadísticas del día de la partida |
| GET | `/api/partidas` | Lista todas las partidas (desc) |
| GET | `/api/partidas/current` | Partida de hoy (o última disponible) |
| POST | `/api/partidas` | Crear partida `{fecha, articulo, numero_partida}` |
| GET | `/api/partidas/<id>/eventos` | Eventos de la partida |
| POST | `/api/partidas/<id>/eventos` | Crear evento `{hora_evento, temperatura_c, evento}` |
| GET | `/api/partidas/<id>/muestras` | Muestras de la partida |
| POST | `/api/partidas/<id>/muestras` | Crear muestra `{hora_medicion, tipo_medicion, instrumento, medicion_viscosidad, medicion_temperatura}` |

---

## Estructura del Proyecto

```
modbus/
├── config/
│   └── config.yaml                 # Configuración principal
├── src/
│   ├── broadcast_client.py         # Cliente de comunicación serial
│   ├── broadcast_parser.py         # Parser de datos HP550
│   ├── data_storage.py             # Sistema de almacenamiento (SQLite + CSV)
│   ├── data_logger.py              # Sistema de logging
│   └── utils.py                    # Utilidades
├── html/
│   ├── dashboard.html              # Dashboard web (Chart.js + anotaciones)
│   └── style.css                   # Estilos del dashboard
├── hp550_capture.py                # Script principal: captura + API Flask
├── hp550-capture.service           # Unidad systemd para Raspberry Pi / Ubuntu
├── export_data.py                  # Herramienta de exportación
├── requirements.txt                # Dependencias Python
├── logs/
│   └── hp550.log                   # Logs de operación
└── data/
    ├── hp550_data.db               # Base de datos SQLite
    └── csv/                        # Archivos CSV por día
```

---

## Esquema de Base de Datos

### `readings` — lecturas del viscosímetro

| Campo | Tipo | Descripción |
|-------|------|-------------|
| timestamp_gmt | TEXT | Marca temporal en GMT |
| timestamp_local | TEXT | Marca temporal local |
| vl_cp | REAL | Viscosidad de línea (cP) |
| temperature_c | REAL | Temperatura (°C) |
| vc_cp | REAL | Viscosidad corregida (cP) |
| is_valid | INTEGER | Flag de validez (1 = válido) |

### `partidas` — partidas de producción

| Campo | Tipo | Descripción |
|-------|------|-------------|
| fecha | TEXT | Fecha `YYYY-MM-DD` |
| articulo | TEXT | Nombre del artículo |
| numero_partida | INTEGER | Número de partida |

### `eventos` — eventos dentro de una partida

| Campo | Tipo | Descripción |
|-------|------|-------------|
| partida_id | INTEGER | FK → partidas |
| hora_evento | TEXT | Hora `HH:MM` |
| temperatura_c | REAL | Temperatura en el momento |
| evento | TEXT | Descripción del evento |

### `muestras` — lecturas manuales o de laboratorio

| Campo | Tipo | Descripción |
|-------|------|-------------|
| partida_id | INTEGER | FK → partidas |
| hora_medicion | TEXT | Hora `HH:MM` |
| tipo_medicion | TEXT | `lectura` o `laboratorio` |
| instrumento | TEXT | `pipeta`, `pico 5`, `pico 7` o NULL |
| medicion_viscosidad | REAL | Viscosidad medida |
| medicion_temperatura | REAL | Temperatura medida |

Las lecturas automáticas se asocian a una partida por fecha (`date(timestamp_local) = partida.fecha`), sin FK directa.

---

## Servicio systemd (Raspberry Pi / Ubuntu)

Para ejecutar como servicio 24/7 con inicio automático en boot:

```bash
# 1. Copiar el archivo de servicio
sudo cp hp550-capture.service /etc/systemd/system/

# 2. Agregar usuario al grupo serial
sudo usermod -a -G dialout pi

# 3. Activar e iniciar
sudo systemctl daemon-reload
sudo systemctl enable hp550-capture.service
sudo systemctl start hp550-capture.service
```

El servicio está vinculado a `/dev/ttyUSB0`: se detiene automáticamente si se desconecta el adaptador USB-serial y se reinicia al reconectarlo.

### Gestión del servicio

```bash
sudo systemctl status hp550-capture    # estado actual
sudo systemctl stop hp550-capture      # detener
sudo systemctl restart hp550-capture   # reiniciar
journalctl -u hp550-capture -f         # logs en tiempo real
```

---

## Notas Técnicas

**Protocolo HP550**: El HP550 no implementa Modbus request-response estándar. Usa un modo de "triggered broadcasting":
- Se envía una query Modbus ASCII para disparar la respuesta
- El HP550 responde con un formato de display stream propietario
- El parser extrae los valores de los tags `<WT...>`

Por eso se usa `broadcast_client.py` en lugar de un cliente Modbus estándar.

**Backup de base de datos** (recomendado antes de actualizaciones):
```bash
cp data/hp550_data.db data/hp550_data_BACKUP_$(date +%Y%m%d_%H%M).db
```
