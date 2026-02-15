# HP550 Hydramotion - Sistema de Captura

Aplicación Python para captura continua de datos del viscosímetro y temperatura - HP550 Hydramotion vía broadcasting mode sobre RS-232, con dashboard web integrado para visualización en tiempo real.

## Características

- Captura automática cada X segundos (configurable)
- Dashboard web integrado con gráficos en tiempo real
- Almacenamiento en SQLite y/o CSV
- Reconexión automática si se pierde la conexión
- Rotación automática de archivos CSV por día
- Logging completo de operaciones y errores

## Requisitos

### Hardware
- HP550 Hydramotion Viscometer
- Puerto serial RS-232 o adaptador USB-Serial (FTDI compatible)
- PC (Windows) o Raspberry Pi (Linux)

### Software
- Python 3.7 o superior
- pip (gestor de paquetes Python)

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
   Par: EVEN
   Addr: 01
   rS: RS232
   bE: ON    <- CRITICO (habilita transmision)
   Oph: 01   <- Recomendado (transmite VL + VC + Temp)
   ```

3. **Editar configuracion**

   Editar `config/config.yaml` y ajustar:
   ```yaml
   serial:
     port: "COM9"              # Tu puerto serial (Linux: /dev/ttyUSB0)

   data_capture:
     enabled: true
     interval: 10              # Segundos entre capturas
     storage_type: "sqlite"    # "sqlite", "csv", o "both"

   # Opcional: puerto del dashboard web
   web:
     port: 5000
   ```

## Uso

### Captura + Dashboard (modo normal)

```bash
python hp550_capture.py
```

Esto inicia simultaneamente:
- **Captura de datos** del HP550 via serial (hilo principal)
- **Dashboard web** en `http://<ip>:5000` (hilo secundario)

Abrir el dashboard desde cualquier navegador en la red local.

### Solo Dashboard (sin HP550 conectado)

```bash
python hp550_capture.py --web-only
```

Util para revisar datos historicos sin necesidad del viscosimetro.

### Puerto personalizado

```bash
python hp550_capture.py --port 8080
```

### Ver Estadisticas de Datos

```bash
python export_data.py --stats
```

### Ver Lecturas Recientes

```bash
python export_data.py --recent 20
```

### Exportar a CSV

```bash
python export_data.py --export datos_completos.csv
python export_data.py --export ultimos_7_dias.csv --days 7
```

## Dashboard Web

El dashboard muestra en tiempo real:

- **Tarjetas**: valores actuales de VL (cP), Temperatura (C), VC (cP)
- **Grafico**: viscosidad y temperatura en el tiempo con doble eje Y
- **Estadisticas**: promedio, minimo y maximo del periodo seleccionado
- **Rangos**: 30 min, 1 hora, 6 horas, 24 horas, 7 dias
- **Auto-refresh**: se actualiza cada 10 segundos

### API REST

El dashboard expone endpoints JSON para integracion con otros sistemas:

| Endpoint | Descripcion |
|----------|-------------|
| `GET /api/readings?hours=1&limit=2000` | Lecturas en rango de tiempo |
| `GET /api/latest` | Ultima lectura valida |
| `GET /api/stats?hours=24` | Estadisticas del periodo |

## Estructura del Proyecto

```
modbus/
├── config/
│   └── config.yaml                 # Configuracion principal
├── src/
│   ├── broadcast_client.py         # Cliente de comunicacion serial
│   ├── broadcast_parser.py         # Parser de datos HP550
│   ├── data_storage.py             # Sistema de almacenamiento
│   ├── data_logger.py              # Sistema de logging
│   └── utils.py                    # Utilidades
├── html/
│   └── dashboard.html              # Dashboard web (Chart.js)
├── hp550_capture.py                # Script principal: captura + dashboard
├── export_data.py                  # Herramienta de exportacion
├── requirements.txt                # Dependencias Python
├── logs/
│   └── hp550.log                   # Logs de operacion
└── data/
    ├── hp550_data.db               # Base de datos SQLite
    └── csv/                        # Archivos CSV por dia
```

## Datos Capturados

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| timestamp_gmt | TEXT | Marca temporal en GMT |
| timestamp_local | TEXT | Marca temporal local |
| vl_cp | REAL | Viscosidad de linea (cP) |
| temperature_c | REAL | Temperatura (C) |
| vc_cp | REAL | Viscosidad corregida (cP) |
| is_valid | INTEGER | Flag de validez (1=valido) |

## Documentacion Completa

Para informacion detallada sobre configuracion avanzada, ejecucion como servicio, troubleshooting y mantenimiento:

**[README_CAPTURE_24X7.md](README_CAPTURE_24X7.md)**

## Notas Tecnicas

**Importante**: El HP550 no implementa Modbus request-response estandar. En su lugar, usa un modo de "triggered broadcasting":
- Se envia una query Modbus ASCII para disparar la respuesta
- El HP550 responde con un formato de display stream propietario
- El parser extrae los valores del formato `<WT...>` tags

Este comportamiento es especifico del HP550 y por eso se usa `broadcast_client.py` en lugar de un cliente Modbus estandar.
