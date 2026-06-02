# -*- coding: utf-8 -*-
"""
Validación de entradas del usuario antes de ejecutar el procesamiento.
"""

import os

from qgis.core import QgsVectorLayer, QgsWkbTypes

from ..utilidades.constantes import EXTENSIONES_CATASTRO, EXTENSIONES_LIDAR


class GestorEntradas(object):
    """Valida rutas, capas y parámetros de configuración."""

    @staticmethod
    def validar_archivo_lidar(ruta):
        """
        Comprueba que la ruta apunte a un archivo LAS o LAZ existente.

        :return: Tupla (es_valido, mensaje_error).
        """
        if not ruta or not str(ruta).strip():
            return False, "Debe seleccionar un archivo LiDAR."
        ruta = str(ruta).strip()
        if not os.path.isfile(ruta):
            return False, "El archivo LiDAR no existe: {}".format(ruta)
        extension = os.path.splitext(ruta)[1].lower()
        if extension not in EXTENSIONES_LIDAR:
            return False, "Formato no admitido. Use archivos .las o .laz."
        return True, ""

    @staticmethod
    def validar_directorio_salida(ruta):
        """
        Comprueba que el directorio de salida exista o pueda crearse.

        :return: Tupla (es_valido, mensaje_error).
        """
        if not ruta or not str(ruta).strip():
            return False, "Debe indicar un directorio de salida."
        ruta = str(ruta).strip()
        if os.path.isdir(ruta):
            return True, ""
        try:
            os.makedirs(ruta)
            return True, ""
        except OSError as error:
            return False, "No se puede crear el directorio de salida: {}".format(error)

    @staticmethod
    def validar_capa_catastral(capa):
        """
        Comprueba que la capa sea vectorial poligonal válida.

        :return: Tupla (es_valido, mensaje_error).
        """
        if capa is None:
            return False, "Debe seleccionar una capa catastral de edificaciones."
        if not isinstance(capa, QgsVectorLayer):
            return False, "La capa catastral debe ser una capa vectorial."
        if not capa.isValid():
            return False, "La capa catastral seleccionada no es válida."
        if not GestorEntradas._es_capa_poligonal(capa):
            return False, "La capa catastral debe contener geometrías de tipo polígono."
        return True, ""

    @staticmethod
    def _es_capa_poligonal(capa):
        """
        Comprueba si la capa es poligonal (compatible con QGIS 3.16 a 3.42+).

        En QGIS 3.42 las constantes ya no están en QgsMapLayer; se usa QgsWkbTypes
        o el enum Qgis.GeometryType según la versión instalada.
        """
        try:
            from qgis.core import Qgis

            if capa.geometryType() == Qgis.GeometryType.Polygon:
                return True
        except (ImportError, AttributeError, TypeError):
            pass

        tipo_geometria = capa.geometryType()
        if tipo_geometria == QgsWkbTypes.PolygonGeometry:
            return True

        # Comprobación adicional por tipo WKB.
        return QgsWkbTypes.geometryType(capa.wkbType()) == QgsWkbTypes.PolygonGeometry

    @staticmethod
    def validar_sistema_referencia(crs):
        """
        Comprueba que se haya definido un CRS.

        :return: Tupla (es_valido, mensaje_error).
        """
        if crs is None or not crs.isValid():
            return False, "Debe seleccionar un sistema de referencia espacial válido."
        return True, ""

    @staticmethod
    def validar_parametros_numericos(altura, resolucion, area_minima, tolerancia, porcentaje):
        """
        Comprueba que los parámetros numéricos sean positivos y coherentes.

        :return: Tupla (es_valido, mensaje_error).
        """
        if altura <= 0:
            return False, "La altura mínima de edificación debe ser mayor que cero."
        if resolucion <= 0:
            return False, "La resolución de rasterización debe ser mayor que cero."
        if area_minima <= 0:
            return False, "El área mínima de detección debe ser mayor que cero."
        if tolerancia < 0:
            return False, "La distancia de tolerancia no puede ser negativa."
        if porcentaje <= 0 or porcentaje > 100:
            return False, "El porcentaje mínimo de coincidencia debe estar entre 0 y 100."
        return True, ""

    @staticmethod
    def validar_archivo_catastro_externo(ruta):
        """Valida extensión de un archivo vectorial catastral a cargar."""
        if not ruta or not os.path.isfile(ruta):
            return False, "Archivo catastral no encontrado."
        extension = os.path.splitext(ruta)[1].lower()
        if extension not in EXTENSIONES_CATASTRO:
            return False, "Formato catastral no admitido. Use .shp, .gpkg o .geojson."
        return True, ""
