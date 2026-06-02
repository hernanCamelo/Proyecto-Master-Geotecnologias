# -*- coding: utf-8 -*-
"""
Lectura y filtrado de nubes de puntos LiDAR en formato LAS/LAZ.
"""

import numpy as np
from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProject

from ..utilidades.constantes import UMBRAL_PUNTOS_ADVERTENCIA
from ..utilidades.entorno_geoespacial import configurar_entorno_geoespacial_qgis
from ..utilidades.optimizacion import advertir_archivo_muy_grande, transformar_coordenadas_en_lotes
from .datos_puntos_lidar import DatosPuntosLidar
from .utilidades_raster import CLASE_EDIFICACION_ASPRS, CLASE_TERRENO_ASPRS, CLASES_RUIDO_ASPRS


class ProcesadorLidar(object):
    """Procesa archivos LAS/LAZ y aplica filtros de clasificación."""

    def __init__(self, contexto):
        """
        :param contexto: Instancia de ContextoAnalisis.
        """
        self.contexto = contexto

    def ejecutar(self):
        """
        Lee y filtra la nube de puntos según el contexto.

        :return: Tupla (exito, mensaje).
        """
        if self.contexto.cancelado:
            return False, "Procesamiento cancelado por el usuario."

        try:
            import laspy
        except ImportError:
            return False, (
                "No está instalado el módulo 'laspy'. "
                "Instálelo en el Python de QGIS: python -m pip install laspy lazrs"
            )

        try:
            configurar_entorno_geoespacial_qgis()
            datos = self._leer_archivo_lidar(laspy)
            self._aplicar_filtros_clasificacion(datos)
            datos = self._reprojectar_si_necesario(datos)
            self._calcular_extension(datos)

            self.contexto.datos_puntos = datos
            mensaje = (
                "LiDAR cargado: {0} puntos ({1} terreno, {2} edificación). "
                "Clasificación ASPRS: {3}."
            ).format(
                datos.cantidad_puntos,
                datos.cantidad_terreno,
                datos.cantidad_edificacion,
                "sí" if datos.tiene_clasificacion else "no",
            )
            advertencia = advertir_archivo_muy_grande(
                datos.cantidad_puntos, UMBRAL_PUNTOS_ADVERTENCIA
            )
            if advertencia:
                mensaje = mensaje + " " + advertencia
            return True, mensaje
        except Exception as error:
            return False, "Error al procesar LiDAR: {}".format(error)

    def _leer_archivo_lidar(self, laspy):
        """Lee coordenadas y clasificación desde el archivo."""
        archivo = laspy.read(self.contexto.ruta_archivo_lidar)
        datos = DatosPuntosLidar()

        datos.x = np.asarray(archivo.x, dtype=np.float64)
        datos.y = np.asarray(archivo.y, dtype=np.float64)
        datos.z = np.asarray(archivo.z, dtype=np.float64)
        datos.cantidad_puntos = len(datos.x)

        if datos.cantidad_puntos == 0:
            raise ValueError("El archivo LiDAR no contiene puntos.")

        # Detección de clasificación ASPRS.
        if hasattr(archivo, "classification"):
            clasificacion = np.asarray(archivo.classification, dtype=np.int32)
            datos.tiene_clasificacion = True
            mascara_terreno = clasificacion == CLASE_TERRENO_ASPRS
            mascara_edificacion = clasificacion == CLASE_EDIFICACION_ASPRS
            mascara_ruido = np.isin(clasificacion, CLASES_RUIDO_ASPRS)

            datos.x_terreno = datos.x[mascara_terreno]
            datos.y_terreno = datos.y[mascara_terreno]
            datos.z_terreno = datos.z[mascara_terreno]

            datos.x_edificacion = datos.x[mascara_edificacion]
            datos.y_edificacion = datos.y[mascara_edificacion]
            datos.z_edificacion = datos.z[mascara_edificacion]

            # Puntos de superficie para DSM: todos salvo ruido explícito.
            mascara_superficie = ~mascara_ruido
            datos.x = datos.x[mascara_superficie]
            datos.y = datos.y[mascara_superficie]
            datos.z = datos.z[mascara_superficie]

            datos.cantidad_terreno = len(datos.x_terreno)
            datos.cantidad_edificacion = len(datos.x_edificacion)
            datos.cantidad_puntos = len(datos.x)

        datos.crs_origen = self._obtener_crs_desde_las(archivo)
        datos.crs_trabajo = self.contexto.crs
        return datos

    def _obtener_crs_desde_las(self, archivo):
        """Intenta obtener el CRS embebido en el archivo LAS."""
        try:
            if hasattr(archivo, "header") and hasattr(archivo.header, "parse_crs"):
                crs_parsed = archivo.header.parse_crs()
                if crs_parsed is not None:
                    return QgsCoordinateReferenceSystem(crs_parsed.to_wkt())
        except Exception:
            pass
        return None

    def _aplicar_filtros_clasificacion(self, datos):
        """Ajusta subconjuntos según las opciones del usuario."""
        if not datos.tiene_clasificacion:
            if not self.contexto.usar_todas_clases_si_falla:
                raise ValueError(
                    "El archivo no incluye clasificación ASPRS. "
                    "Active la opción de usar todos los puntos o use un LAS clasificado."
                )
            datos.cantidad_terreno = datos.cantidad_puntos
            datos.x_terreno = datos.x
            datos.y_terreno = datos.y
            datos.z_terreno = datos.z
            return

        # Sin puntos de terreno: usar todos los puntos si está permitido.
        if self.contexto.filtrar_clase_terreno and datos.cantidad_terreno == 0:
            if self.contexto.usar_todas_clases_si_falla:
                datos.x_terreno = datos.x
                datos.y_terreno = datos.y
                datos.z_terreno = datos.z
                datos.cantidad_terreno = datos.cantidad_puntos
            else:
                raise ValueError(
                    "No se encontraron puntos clasificados como terreno (clase 2)."
                )

        if not self.contexto.filtrar_clase_terreno:
            datos.x_terreno = datos.x
            datos.y_terreno = datos.y
            datos.z_terreno = datos.z
            datos.cantidad_terreno = datos.cantidad_puntos

        if self.contexto.filtrar_clase_edificacion and datos.cantidad_edificacion == 0:
            if not self.contexto.usar_todas_clases_si_falla:
                pass

    def _reprojectar_si_necesario(self, datos):
        """Reproyecta coordenadas X/Y al CRS de trabajo del análisis."""
        crs_destino = self.contexto.crs
        crs_origen = datos.crs_origen

        if crs_origen is None or not crs_origen.isValid():
            datos.crs_trabajo = crs_destino
            return datos

        if crs_origen == crs_destino:
            datos.crs_trabajo = crs_destino
            return datos

        transformacion = QgsCoordinateTransform(
            crs_origen,
            crs_destino,
            QgsProject.instance(),
        )

        datos.x, datos.y = self._transformar_arrays(
            transformacion, datos.x, datos.y
        )
        if datos.x_terreno is not None and len(datos.x_terreno) > 0:
            datos.x_terreno, datos.y_terreno = self._transformar_arrays(
                transformacion, datos.x_terreno, datos.y_terreno
            )
        if datos.x_edificacion is not None and len(datos.x_edificacion) > 0:
            datos.x_edificacion, datos.y_edificacion = self._transformar_arrays(
                transformacion, datos.x_edificacion, datos.y_edificacion
            )

        datos.crs_trabajo = crs_destino
        return datos

    @staticmethod
    def _transformar_arrays(transformacion, x, y):
        """Transforma arrays de coordenadas (pyproj vectorizado o QGIS)."""
        try:
            from pyproj import Transformer

            origen = transformacion.sourceCrs().authid()
            destino = transformacion.destinationCrs().authid()
            if not origen or not destino:
                raise ValueError("CRS sin authid")
            transformador = Transformer.from_crs(origen, destino, always_xy=True)
            return transformar_coordenadas_en_lotes(transformador, np.asarray(x), np.asarray(y))
        except Exception:
            puntos_transformados = [
                transformacion.transform(float(xi), float(yi)) for xi, yi in zip(x, y)
            ]
            x_nuevo = np.array([p.x() for p in puntos_transformados], dtype=np.float64)
            y_nuevo = np.array([p.y() for p in puntos_transformados], dtype=np.float64)
            return x_nuevo, y_nuevo

    def _calcular_extension(self, datos):
        """Calcula la extensión combinada de los puntos en CRS de trabajo."""
        xmin = float(np.min(datos.x))
        xmax = float(np.max(datos.x))
        ymin = float(np.min(datos.y))
        ymax = float(np.max(datos.y))
        datos.extension = (xmin, ymin, xmax, ymax)
        self.contexto.extension_analisis = datos.extension
