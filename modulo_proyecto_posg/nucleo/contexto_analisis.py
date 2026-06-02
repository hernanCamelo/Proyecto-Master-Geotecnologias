# -*- coding: utf-8 -*-
"""
Contenedor de estado para una ejecución del análisis LiDAR-catastro.
"""


class ContextoAnalisis(object):
    """
    Almacena entradas, parámetros, rutas de salida y referencias a capas generadas.
    Se rellena progresivamente durante el pipeline de procesamiento.
    """

    def __init__(self):
        """Inicializa un contexto vacío."""
        # Entradas configuradas por el usuario.
        self.ruta_archivo_lidar = ""
        self.capa_catastral = None
        self.directorio_salida = ""
        self.crs = None

        # Parámetros numéricos y flags de filtrado.
        self.altura_minima_edificacion = 0.0
        self.resolucion_raster = 0.0
        self.area_minima_deteccion = 0.0
        self.distancia_tolerancia = 0.0
        self.porcentaje_minimo_coincidencia = 0.0
        self.filtrar_clase_terreno = True
        self.filtrar_clase_edificacion = True
        self.usar_todas_clases_si_falla = False

        # Datos intermedios LiDAR y raster.
        self.datos_puntos = None
        self.malla_ndsm = None
        self.malla_dsm = None
        self.estadisticas_raster = {}
        self.transformacion_raster = None
        self.dimensiones_raster = None
        self.origen_raster = None
        self.extension_analisis = None
        self.cantidad_huellas = 0
        self.ruta_huellas = ""
        self.resumen_validacion_inicial = {}
        self.resumen_validacion_catastral = {}
        self.ruta_coincidentes = ""
        self.ruta_discrepancias = ""
        self.ruta_nuevas = ""
        self.ruta_demoliciones = ""

        # Rutas de productos raster generados.
        self.ruta_dsm = ""
        self.ruta_dtm = ""
        self.ruta_ndsm = ""

        # Referencias a capas QGIS generadas.
        self.capa_dsm = None
        self.capa_dtm = None
        self.capa_ndsm = None
        self.capa_huellas = None
        self.capa_coincidentes = None
        self.capa_discrepancias = None
        self.capa_nuevas = None
        self.capa_demoliciones = None

        # Métricas y reporte CSV.
        self.metricas_validacion = []
        self.ruta_informe_csv = ""
        self.ruta_proyecto_exportado = ""
        self.ultima_ruta_exportacion = ""

        # Control de ejecución.
        self.cancelado = False
        self.completado = False

    def reiniciar_resultados(self):
        """Limpia resultados de una ejecución anterior."""
        self.datos_puntos = None
        self.malla_ndsm = None
        self.malla_dsm = None
        self.estadisticas_raster = {}
        self.transformacion_raster = None
        self.dimensiones_raster = None
        self.origen_raster = None
        self.extension_analisis = None
        self.cantidad_huellas = 0
        self.ruta_huellas = ""
        self.resumen_validacion_inicial = {}
        self.resumen_validacion_catastral = {}
        self.ruta_coincidentes = ""
        self.ruta_discrepancias = ""
        self.ruta_nuevas = ""
        self.ruta_demoliciones = ""
        self.ruta_dsm = ""
        self.ruta_dtm = ""
        self.ruta_ndsm = ""
        self.capa_dsm = None
        self.capa_dtm = None
        self.capa_ndsm = None
        self.capa_huellas = None
        self.capa_coincidentes = None
        self.capa_discrepancias = None
        self.capa_nuevas = None
        self.capa_demoliciones = None
        self.metricas_validacion = []
        self.ruta_informe_csv = ""
        self.ruta_proyecto_exportado = ""
        self.ultima_ruta_exportacion = ""
        self.completado = False
