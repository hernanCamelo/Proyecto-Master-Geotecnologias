# -*- coding: utf-8 -*-
"""
Generación de modelos DSM, DTM y nDSM a partir de datos LiDAR.
"""

import os

import numpy as np

from ..utilidades.constantes import NOMBRE_CAPA_DSM, NOMBRE_CAPA_DTM, NOMBRE_CAPA_NDSM
from ..utilidades.entorno_geoespacial import configurar_entorno_geoespacial_qgis
from .utilidades_raster import (
    calcular_extension_y_dimensiones,
    calcular_ndsm_desde_dsm_dtm,
    combinar_mallas_maximo,
    crear_transformacion_raster,
    guardar_geotiff,
    rasterizar_maximo,
    rasterizar_minimo,
    rellenar_nodata_vecino,
    resumir_estadisticas_mallas,
)


class GeneradorModelosDerivados(object):
    """Genera rásteres derivados y registra sus rutas en el contexto."""

    def __init__(self, contexto):
        self.contexto = contexto

    def ejecutar(self):
        """
        Genera DSM, DTM y nDSM en el directorio de salida.

        :return: Tupla (exito, mensaje).
        """
        if self.contexto.cancelado:
            return False, "Generación de modelos cancelada."

        datos = self.contexto.datos_puntos
        if datos is None:
            return False, "No hay datos LiDAR cargados. Ejecute primero el procesador LiDAR."

        try:
            configurar_entorno_geoespacial_qgis()
            resolucion = self.contexto.resolucion_raster
            xmin, ymin, xmax, ymax_superior, ncols, nrows = calcular_extension_y_dimensiones(
                datos.x, datos.y, resolucion
            )

            # DSM: máximo por celda (superficie y, si existe, clase edificación).
            malla_dsm = rasterizar_maximo(
                datos.x, datos.y, datos.z,
                xmin, ymax_superior, resolucion, ncols, nrows,
            )
            if (
                datos.x_edificacion is not None
                and len(datos.x_edificacion) > 0
            ):
                malla_dsm_edificacion = rasterizar_maximo(
                    datos.x_edificacion,
                    datos.y_edificacion,
                    datos.z_edificacion,
                    xmin,
                    ymax_superior,
                    resolucion,
                    ncols,
                    nrows,
                )
                malla_dsm = combinar_mallas_maximo(malla_dsm, malla_dsm_edificacion)

            # DTM: mínimo por celda en puntos de terreno.
            x_terreno = datos.x_terreno
            y_terreno = datos.y_terreno
            z_terreno = datos.z_terreno
            if x_terreno is None or len(x_terreno) == 0:
                x_terreno, y_terreno, z_terreno = datos.x, datos.y, datos.z

            malla_dtm = rasterizar_minimo(
                x_terreno, y_terreno, z_terreno,
                xmin, ymax_superior, resolucion, ncols, nrows,
            )
            # DTM exclusivamente de terreno (sin mínimo de todos los puntos).
            malla_dtm = rellenar_nodata_vecino(malla_dtm, max_iteraciones=15)
            malla_ndsm, malla_dtm, malla_dsm = calcular_ndsm_desde_dsm_dtm(
                malla_dsm, malla_dtm
            )

            estadisticas = resumir_estadisticas_mallas(malla_dsm, malla_dtm, malla_ndsm)
            self.contexto.estadisticas_raster = estadisticas
            self.contexto.malla_dsm = malla_dsm

            transformacion = crear_transformacion_raster(xmin, ymax_superior, resolucion)
            crs = self.contexto.crs
            directorio = self.contexto.directorio_salida

            self.contexto.ruta_dsm = os.path.join(directorio, "{}.tif".format(NOMBRE_CAPA_DSM))
            self.contexto.ruta_dtm = os.path.join(directorio, "{}.tif".format(NOMBRE_CAPA_DTM))
            self.contexto.ruta_ndsm = os.path.join(directorio, "{}.tif".format(NOMBRE_CAPA_NDSM))

            guardar_geotiff(
                malla_dsm, xmin, ymax_superior, resolucion, self.contexto.ruta_dsm, crs
            )
            guardar_geotiff(
                malla_dtm, xmin, ymax_superior, resolucion, self.contexto.ruta_dtm, crs
            )
            guardar_geotiff(
                malla_ndsm, xmin, ymax_superior, resolucion, self.contexto.ruta_ndsm, crs
            )

            self.contexto.transformacion_raster = transformacion
            self.contexto.dimensiones_raster = (ncols, nrows)
            self.contexto.origen_raster = (xmin, ymax_superior)
            self.contexto.malla_ndsm = malla_ndsm
            self.contexto.extension_analisis = (xmin, ymin, xmax, ymax_superior)

            celdas_validas = estadisticas["celdas_ndsm"]
            if celdas_validas == 0:
                return False, (
                    "No se pudo calcular nDSM (0 celdas válidas). "
                    "Compruebe que el CRS del análisis coincida con el LiDAR. "
                    "Celdas con datos: DSM {0}, DTM {1}, solapamiento {2}."
                ).format(
                    estadisticas["celdas_dsm"],
                    estadisticas["celdas_dtm"],
                    estadisticas["celdas_solapadas"],
                )

            mensaje = (
                "Modelos generados: DSM, DTM y nDSM ({0}×{1} celdas; "
                "{2} celdas en nDSM; altura máxima {3:.1f} m)."
            ).format(
                ncols,
                nrows,
                celdas_validas,
                estadisticas["altura_max_ndsm"],
            )
            return True, mensaje
        except ImportError as error:
            texto = str(error)
            if "multiarray" in texto:
                return False, (
                    "Error de compatibilidad con NumPy ({}). "
                    "Cierre y vuelva a abrir QGIS. Si el error continúa, reinstale "
                    "las dependencias con el instalador de complementos de QGIS."
                ).format(texto)
            return False, "Falta dependencia para rásteres: {}".format(texto)
        except Exception as error:
            return False, "Error al generar modelos derivados: {}".format(error)
