# -*- coding: utf-8 -*-
"""
Constantes globales del complemento Validador LiDAR de huella urbana.
"""

# Versión mostrada en la interfaz (debe coincidir con metadata.txt).
VERSION_COMPLEMENTO = "1.0"

# Optimización: umbrales y tamaños de lote.
UMBRAL_PUNTOS_ADVERTENCIA = 5000000
TAMANO_LOTE_REPROYECCION = 500000
TAMANO_LOTE_LECTURA_LIDAR = 1000000

# Exportación.
NOMBRE_CARPETA_EXPORTACION = "exportacion_resultados"
NOMBRE_PROYECTO_QGIS = "proyecto_validador_lidar.qgz"
NOMBRE_MANIFIESTO_EXPORTACION = "manifiesto_exportacion.txt"

# Extensiones de archivo admitidas.
EXTENSIONES_LIDAR = (".las", ".laz")
EXTENSIONES_CATASTRO = (".shp", ".gpkg", ".geojson")

# Valores por defecto de los parámetros de análisis.
ALTURA_MINIMA_EDIFICACION_DEFECTO = 2.5
RESOLUCION_RASTER_DEFECTO = 1.0
AREA_MINIMA_DETECCION_DEFECTO = 15.0
DISTANCIA_TOLERANCIA_DEFECTO = 2.0
PORCENTAJE_MINIMO_COINCIDENCIA_DEFECTO = 70.0

# Nombres de capas generadas en el proyecto QGIS.
NOMBRE_CAPA_DSM = "DSM_LiDAR"
NOMBRE_CAPA_DTM = "DTM_LiDAR"
NOMBRE_CAPA_NDSM = "nDSM_LiDAR"
NOMBRE_CAPA_HUELLAS = "Huellas_edificaciones_LiDAR"
NOMBRE_CAPA_COINCIDENTES = "Edificaciones_coincidentes"
NOMBRE_CAPA_DISCREPANCIAS = "Discrepancias_geometricas"
NOMBRE_CAPA_NUEVAS = "Nuevas_construcciones"
NOMBRE_CAPA_DEMOLICIONES = "Posibles_demoliciones"

# Etapas del pipeline (porcentaje acumulado para la barra de progreso).
ETAPAS_PROCESAMIENTO = [
    ("Validación de entradas", 5),
    ("Procesamiento LiDAR", 20),
    ("Generación DSM/DTM/nDSM", 40),
    ("Extracción de huellas", 55),
    ("Validaciones iniciales", 70),
    ("Validación catastral", 88),
    ("Finalización", 100),
]
