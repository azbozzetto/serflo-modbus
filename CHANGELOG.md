# Changelog

Todos los cambios notables de este proyecto están documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/lang/es/).

---

## [1.2.0] - 2026-03-19

### Agregado
- **Partidas de producción**: creación y selección de partidas desde el drawer lateral
- **Eventos**: registro de eventos con hora y temperatura, visualizados como flags verticales en el gráfico (línea discontinua amarilla con etiqueta en la parte superior)
- **Muestras & Lecturas**: registro de mediciones manuales (pipeta, pico 5, pico 7, laboratorio) con callout en la parte inferior del gráfico
- **Zoom interactivo**: zoom con rueda del mouse y arrastre sobre el gráfico; botón "Restablecer Zoom" siempre visible a la derecha
- **Toggles de anotaciones**: botones "Eventos" y "Muestras & Lecturas" para mostrar/ocultar anotaciones del gráfico
- **Modo Partidas** (`btn-day-mode`): carga el día completo seleccionado; navegación ← → entre días
- **API REST** para gestión de partidas, eventos y muestras (6 endpoints nuevos)
- **Card de partida**: número, artículo, fecha y pill "En Vivo" (solo cuando se visualiza el día actual)
- **Popup de selección**: "SELECCIÓN DE PARTIDA" con fila "DATOS EN TIEMPO REAL" separada de la tabla histórica
- **Actualización de card al navegar**: en modo live, el card de partida se actualiza según la fecha visualizada
- **CHANGELOG.md** con historial del proyecto

### Cambiado
- Botón "Live" renombrado a **Auto**; activa el modo día para el día de hoy
- La página carga por defecto en **modo Partidas** (día actual completo)
- Tamaño mínimo de fuente **14 px** en todos los elementos
- Viscosidad en anotaciones de muestras: siempre **2 decimales** para no confundir instrumentos
- Etiqueta de anotación de muestras: formato `VISCO. PIPETA 39.90 / TEMP. 81.4 °C`, sin unidad "cP"
- `refresh-info` movido a la barra de controles de escala, alineado a la derecha
- Ancho mínimo de pantalla: **860 px**

### Corregido
- Eventos y muestras que aparecían en partidas incorrectas al navegar hacia atrás en modo live
- Anotaciones que se mostraban fuera del rango de tiempo visible
- Botón "Restablecer Zoom" que desaparecía al seleccionar una partida histórica
- Etiquetas de eventos truncadas o posicionadas fuera del área del gráfico

---

## [1.1.0] - 2025-12-01

### Agregado
- **Servicio systemd** (`hp550-capture.service`) para ejecución continua 24/7 en Raspberry Pi / Ubuntu
- Vinculación del servicio a `/dev/ttyUSB0`: se detiene al desconectar el adaptador y se reinicia al reconectarlo
- Instrucciones de instalación como servicio en README

---

## [1.0.0] - 2025-11-15

### Agregado
- Captura continua de datos del viscosímetro HP550 Hydramotion vía RS-232 en modo broadcasting
- Parser del protocolo propietario HP550 (tags `<WT...>`)
- Dashboard web con Chart.js: gráfico en tiempo real de viscosidad VL y temperatura
- Almacenamiento en SQLite y/o CSV con rotación diaria automática
- API REST: `/api/readings`, `/api/latest`, `/api/stats`
- Reconexión automática al perder la conexión serial
- Sistema de logging con rotación de archivos
- Herramienta `export_data.py` para exportar datos a CSV
- Soporte de configuración mediante `config/config.yaml`
- Compatibilidad Windows (COM port) y Linux (/dev/ttyUSB0)

---

[1.2.0]: https://github.com/azbozzetto/hp550-hydramotion/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/azbozzetto/hp550-hydramotion/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/azbozzetto/hp550-hydramotion/releases/tag/v1.0.0
