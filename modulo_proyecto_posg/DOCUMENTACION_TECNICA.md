# Documentación técnica — Validador LiDAR de huella urbana

**Complemento QGIS:** `modulo_proyecto_posg`  
**Versión:** 1.0  
**Autor:** Hernan Dario Camelo Pinzon  
**Compatibilidad:** QGIS 3.16+ (probado en 3.42), Windows y Linux

---

## 1. Objetivo

Integrar datos **LiDAR** (LAS/LAZ) y **cartografía catastral** vectorial para:

- Generar modelos **DSM**, **DTM** y **nDSM**.
- Extraer **huellas de edificaciones** detectadas por LiDAR.
- Comparar con catastro y clasificar **coincidencias**, **discrepancias**, **nuevas construcciones** y **posibles demoliciones**.
- Visualizar resultados en QGIS con **simbología automática** y **etiquetas**.
- **Exportar** productos raster, vectoriales, CSV y proyecto `.qgz`.

---

## 2. Arquitectura

```
modulo_proyecto_posg/
├── modulo_proyecto_posg.py          # Registro en QGIS (menú, toolbar, dock)
├── modulo_proyecto_posg_dockwidget.py
├── nucleo/                          # Lógica de negocio
│   ├── contexto_analisis.py
│   ├── hilo_controlador_procesamiento.py
│   ├── procesador_lidar.py
│   ├── generador_modelos_derivados.py
│   ├── extractor_huellas_edificaciones.py
│   ├── validador_datos_iniciales.py
│   ├── validador_catastral.py
│   ├── gestor_capas_resultado.py
│   ├── simbologia_resultados.py
│   ├── exportador_resultados.py
│   ├── utilidades_raster.py
│   └── utilidades_geometria.py
├── utilidades/
│   ├── constantes.py
│   ├── mensajes.py
│   ├── verificador_dependencias.py
│   └── optimizacion.py
├── estilos/*.qml
└── test/
```

**Flujo:** interfaz → validación → `QThread` → pipeline núcleo → carga de capas en hilo principal → simbología → exportación opcional.

---

## 3. Pipeline de procesamiento

| Etapa | Módulo | Salida |
|-------|--------|--------|
| LiDAR | `ProcesadorLidar` | `DatosPuntosLidar` en memoria |
| Modelos | `GeneradorModelosDerivados` | GeoTIFF DSM, DTM, nDSM |
| Huellas | `ExtractorHuellasEdificaciones` | GPKG huellas |
| Validación inicial | `ValidadorDatosIniciales` | Comprobaciones de calidad |
| Validación catastral | `ValidadorCatastral` | 4 GPKG + CSV métricas |
| Carga mapa | `GestorCapasResultado` | Capas en proyecto QGIS |

---

## 4. Criterios de validación catastral

| Clase | Criterio |
|-------|----------|
| Coincidente | IoU ≥ umbral %, distancia entre centroides ≤ tolerancia, cambio de área ≤ 15 % |
| Discrepancia | Solapamiento con desplazamiento, cambio de superficie o geometría incompatible |
| Nueva construcción | Huella LiDAR sin solapamiento significativo (IoU ≤ 1 %) |
| Posible demolición | Parcela catastral sin emparejar |

**Optimización:** índice espacial R-tree (`geodataframe.sindex`) para candidatos catastrales.

---

## 5. Dependencias Python

Instalar en el intérprete de QGIS:

```bash
python -m pip install numpy laspy lazrs rasterio shapely geopandas
```

Opcional: `pdal` (procesamiento LiDAR avanzado futuro).

---

## 6. Exportación

La pestaña **Exportación** genera una carpeta:

`exportacion_resultados_YYYYMMDD_HHMMSS/`

| Subcarpeta / archivo | Contenido |
|----------------------|-----------|
| `raster/` | Copia de DSM, DTM, nDSM |
| `vectorial/` | Capas en formato elegido (SHP, GPKG, GeoJSON) |
| `informe_validacion_catastral.csv` | Métricas por edificación |
| `proyecto_validador_lidar.qgz` | Proyecto QGIS con capas cargadas |
| `manifiesto_exportacion.txt` | Listado de archivos y opciones |

---

## 7. Optimizaciones

- Reproyección de coordenadas en **lotes** (`TAMANO_LOTE_REPROYECCION = 500000`).
- **Índice espacial** en validación catastral.
- Advertencia automática si la nube supera **5 millones** de puntos.

---

## 8. Pruebas

Desde la carpeta del complemento (con QGIS en PATH para pruebas con GUI):

```bash
# Pruebas sin QGIS (geometría y exportador)
python -m unittest test.test_utilidades_geometria test.test_gestor_entradas test.test_exportador

# Pruebas con entorno QGIS
python -m unittest test.test_modulo_proyecto_posg_dockwidget
```

---

## 9. Parámetros configurables (interfaz)

| Parámetro | Uso |
|-----------|-----|
| Altura mínima edificación | Umbral en nDSM para vectorizar |
| Resolución ráster | Tamaño de celda DSM/DTM/nDSM |
| Área mínima polígono | Filtra huellas pequeñas |
| Distancia tolerancia | Desplazamiento máximo aceptable |
| % coincidencia mínima | Umbral IoU para “coincidente” |

---

## 10. Limitaciones conocidas

- Nubes muy grandes se cargan completamente en memoria (laspy).
- Shapefile limita nombres de campo y geometrías complejas.
- El proyecto `.qgz` guarda el estado actual del perfil QGIS, no rutas relativas automáticas a datos externos.

---

## 11. Referencia

Documento de especificaciones: `Datos/PropuestaPractica_ComplementoQGIS.pdf`
