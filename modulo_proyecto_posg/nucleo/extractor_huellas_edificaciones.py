# -*- coding: utf-8 -*-
"""
Extracción y vectorización de huellas de edificaciones desde el nDSM.
"""

import os

import numpy as np

from ..utilidades.constantes import NOMBRE_CAPA_HUELLAS
from .utilidades_raster import cerrar_mascara_binaria


class ExtractorHuellasEdificaciones(object):
    """Detecta y vectoriza huellas a partir del modelo normalizado."""

    def __init__(self, contexto):
        self.contexto = contexto

    def ejecutar(self):
        """
        Extrae polígonos de edificaciones aplicando umbrales del contexto.

        :return: Tupla (exito, mensaje).
        """
        if self.contexto.cancelado:
            return False, "Extracción de huellas cancelada."

        malla_ndsm = self.contexto.malla_ndsm
        if malla_ndsm is None:
            return False, "No existe nDSM en memoria. Genere los modelos derivados primero."

        try:
            umbral = self.contexto.altura_minima_edificacion
            area_minima = self.contexto.area_minima_deteccion

            mascara = np.isfinite(malla_ndsm) & (malla_ndsm >= umbral)

            # Alternativa: altura relativa estimada desde el DSM.
            if not np.any(mascara):
                malla_dsm = getattr(self.contexto, "malla_dsm", None)
                if malla_dsm is not None and np.any(np.isfinite(malla_dsm)):
                    valores_dsm = malla_dsm[np.isfinite(malla_dsm)]
                    nivel_suelo = np.nanpercentile(valores_dsm, 10)
                    malla_ndsm = np.where(
                        np.isfinite(malla_dsm),
                        np.maximum(malla_dsm - nivel_suelo, 0.0),
                        np.nan,
                    )
                    self.contexto.malla_ndsm = malla_ndsm
                    mascara = np.isfinite(malla_ndsm) & (malla_ndsm >= umbral)

            if not np.any(mascara):
                estadisticas = getattr(self.contexto, "estadisticas_raster", {})
                return False, (
                    "No se detectaron celdas sobre el umbral de altura ({0} m). "
                    "Altura máxima en nDSM: {1:.1f} m. Reduzca el umbral o compruebe "
                    "que el CRS del proyecto coincida con el LiDAR."
                ).format(
                    umbral,
                    estadisticas.get("altura_max_ndsm", 0.0),
                )

            # Cierre morfológico de la máscara binaria.
            iteraciones_cierre = max(1, int(round(2.0 / self.contexto.resolucion_raster)))
            mascara = cerrar_mascara_binaria(mascara, iteraciones=iteraciones_cierre)

            geometrias = self._vectorizar_mascara(mascara)
            geometrias = self._filtrar_por_area(geometrias, area_minima)

            if len(geometrias) == 0:
                return False, (
                    "No quedaron polígonos tras filtrar por área mínima ({0} m²)."
                ).format(area_minima)

            ruta_salida = os.path.join(
                self.contexto.directorio_salida,
                "{}.gpkg".format(NOMBRE_CAPA_HUELLAS),
            )
            self._guardar_capas_vectoriales(geometrias, ruta_salida)
            self.contexto.ruta_huellas = ruta_salida
            self.contexto.cantidad_huellas = len(geometrias)

            mensaje = "Huellas extraídas: {0} polígonos (umbral {1} m).".format(
                len(geometrias), umbral
            )
            return True, mensaje
        except ImportError as error:
            return False, "Falta dependencia para vectorización: {}".format(error)
        except Exception as error:
            return False, "Error al extraer huellas: {}".format(error)

    def _vectorizar_mascara(self, mascara):
        """
        Convierte la máscara booleana en geometrías de polígonos.

        :return: Lista de geometrías Shapely.
        """
        from rasterio.features import shapes
        from shapely.geometry import shape

        mascara_binaria = mascara.astype(np.uint8)
        transformacion = self.contexto.transformacion_raster

        geometrias = []
        for geom_dict, valor in shapes(mascara_binaria, mask=mascara, transform=transformacion):
            if valor != 1:
                continue
            geometria = shape(geom_dict)
            if not geometria.is_empty and geometria.area > 0:
                geometrias.append(geometria)
        return geometrias

    def _filtrar_por_area(self, geometrias, area_minima):
        """Elimina polígonos cuya área en unidades del CRS sea inferior al mínimo."""
        return [geom for geom in geometrias if geom.area >= area_minima]

    def _guardar_capas_vectoriales(self, geometrias, ruta_salida):
        """Persiste las huellas en GeoPackage."""
        try:
            import geopandas as gpd

            crs = self.contexto.crs.authid() if self.contexto.crs else None
            registros = [
                {"id_edif": indice + 1, "area_m2": round(geom.area, 2), "geometry": geom}
                for indice, geom in enumerate(geometrias)
            ]
            geodataframe = gpd.GeoDataFrame(registros, crs=crs)
            geodataframe.to_file(ruta_salida, driver="GPKG", layer=NOMBRE_CAPA_HUELLAS)
        except ImportError:
            self._guardar_con_qgis(geometrias, ruta_salida)

    def _guardar_con_qgis(self, geometrias, ruta_salida):
        """Escritura alternativa con PyQGIS si no hay geopandas."""
        from qgis.core import (
            QgsFeature,
            QgsFields,
            QgsField,
            QgsGeometry,
            QgsProject,
            QgsVectorFileWriter,
            QgsVectorLayer,
        )
        from qgis.PyQt.QtCore import QVariant

        capa_temporal = QgsVectorLayer(
            "Polygon?crs={}".format(self.contexto.crs.authid()),
            "temp_huellas",
            "memory",
        )
        proveedor = capa_temporal.dataProvider()
        campos = QgsFields()
        campos.append(QgsField("id_edif", QVariant.Int))
        campos.append(QgsField("area_m2", QVariant.Double))
        proveedor.addAttributes(campos)
        capa_temporal.updateFields()

        for indice, geom in enumerate(geometrias):
            feature = QgsFeature()
            feature.setGeometry(ExtractorHuellasEdificaciones._shapely_a_qgsgeometry(geom))
            feature.setAttributes([indice + 1, round(geom.area, 2)])
            proveedor.addFeature(feature)

        opciones = QgsVectorFileWriter.SaveVectorOptions()
        opciones.driverName = "GPKG"
        opciones.layerName = NOMBRE_CAPA_HUELLAS
        QgsVectorFileWriter.writeAsVectorFormatV3(
            capa_temporal,
            ruta_salida,
            QgsProject.instance().transformContext(),
            opciones,
        )

    @staticmethod
    def _shapely_a_qgsgeometry(geometria_shapely):
        """Convierte geometría Shapely a QgsGeometry."""
        from qgis.core import QgsGeometry

        return QgsGeometry.fromWkt(geometria_shapely.wkt)
