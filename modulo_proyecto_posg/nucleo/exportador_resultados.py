# -*- coding: utf-8 -*-
"""
Exportación de productos del análisis a disco.
"""

import os
import shutil
from datetime import datetime

from ..utilidades.constantes import (
    NOMBRE_CAPA_COINCIDENTES,
    NOMBRE_CAPA_DEMOLICIONES,
    NOMBRE_CAPA_DISCREPANCIAS,
    NOMBRE_CAPA_HUELLAS,
    NOMBRE_CAPA_NUEVAS,
    NOMBRE_CARPETA_EXPORTACION,
    NOMBRE_MANIFIESTO_EXPORTACION,
    NOMBRE_PROYECTO_QGIS,
)


class ExportadorResultados(object):
    """Exporta rásteres, vectores, CSV y proyecto QGIS."""

    # Mapeo de formatos de la interfaz a controladores OGR/geopandas.
    FORMATOS_VECTORIALES = {
        "Shapefile": {"extension": ".shp", "controlador": "ESRI Shapefile"},
        "GeoPackage": {"extension": ".gpkg", "controlador": "GPKG"},
        "GeoJSON": {"extension": ".geojson", "controlador": "GeoJSON"},
    }

    CAPAS_VECTORIALES = (
        ("huellas", "ruta_huellas", NOMBRE_CAPA_HUELLAS),
        ("coincidentes", "ruta_coincidentes", NOMBRE_CAPA_COINCIDENTES),
        ("discrepancias", "ruta_discrepancias", NOMBRE_CAPA_DISCREPANCIAS),
        ("nuevas", "ruta_nuevas", NOMBRE_CAPA_NUEVAS),
        ("demoliciones", "ruta_demoliciones", NOMBRE_CAPA_DEMOLICIONES),
    )

    def __init__(self, contexto):
        self.contexto = contexto

    def exportar(self, opciones):
        """
        Exporta según las opciones indicadas por la interfaz.

        :param opciones: dict con claves exportar_rasteres, exportar_vectores, etc.
        :return: Tupla (exito, mensaje, ruta_principal).
        """
        if not self.contexto.completado:
            return False, "No hay resultados para exportar. Ejecute el procesamiento primero.", ""

        directorio_base = self.contexto.directorio_salida
        marca_tiempo = datetime.now().strftime("%Y%m%d_%H%M%S")
        directorio_exportacion = os.path.join(
            directorio_base,
            "{}_{}".format(NOMBRE_CARPETA_EXPORTACION, marca_tiempo),
        )

        try:
            os.makedirs(directorio_exportacion, exist_ok=True)
            archivos_generados = []

            if opciones.get("exportar_rasteres"):
                archivos_generados.extend(
                    self._exportar_rasteres(directorio_exportacion)
                )

            if opciones.get("exportar_vectores"):
                archivos_generados.extend(
                    self._exportar_vectores(
                        directorio_exportacion,
                        opciones.get("formato_vectorial", "GeoPackage (.gpkg)"),
                    )
                )

            if opciones.get("exportar_csv"):
                ruta_csv = self._exportar_csv(directorio_exportacion)
                if ruta_csv:
                    archivos_generados.append(ruta_csv)
                else:
                    return (
                        False,
                        "No se encontró el informe CSV. Ejecute la validación catastral.",
                        directorio_exportacion,
                    )

            if opciones.get("exportar_proyecto"):
                ruta_proyecto = self._exportar_proyecto_qgis(directorio_exportacion)
                if ruta_proyecto:
                    archivos_generados.append(ruta_proyecto)
                    self.contexto.ruta_proyecto_exportado = ruta_proyecto

            if not archivos_generados:
                return False, "No se encontraron archivos para exportar.", directorio_exportacion

            ruta_manifiesto = self._escribir_manifiesto(
                directorio_exportacion, archivos_generados, opciones
            )
            archivos_generados.append(ruta_manifiesto)

            mensaje = (
                "Exportación completada en: {} ({} archivos)."
            ).format(directorio_exportacion, len(archivos_generados))
            return True, mensaje, directorio_exportacion
        except Exception as error:
            return False, "Error al exportar: {}".format(error), directorio_base

    def _exportar_rasteres(self, directorio):
        """Copia los GeoTIFF generados a la carpeta de exportación."""
        subcarpeta = os.path.join(directorio, "raster")
        os.makedirs(subcarpeta, exist_ok=True)
        rutas_generadas = []
        for ruta_origen in (
            self.contexto.ruta_dsm,
            self.contexto.ruta_dtm,
            self.contexto.ruta_ndsm,
        ):
            if ruta_origen and os.path.isfile(ruta_origen):
                ruta_destino = os.path.join(subcarpeta, os.path.basename(ruta_origen))
                shutil.copy2(ruta_origen, ruta_destino)
                rutas_generadas.append(ruta_destino)
        return rutas_generadas

    def _exportar_vectores(self, directorio, texto_formato):
        """Convierte capas vectoriales al formato seleccionado."""
        formato = self._resolver_formato(texto_formato)
        subcarpeta = os.path.join(directorio, "vectorial")
        os.makedirs(subcarpeta, exist_ok=True)
        rutas_generadas = []

        for clave, atributo_ruta, nombre_capa in self.CAPAS_VECTORIALES:
            ruta_origen = getattr(self.contexto, atributo_ruta, "")
            if not ruta_origen or not os.path.isfile(ruta_origen):
                continue
            nombre_archivo = "{}{}".format(nombre_capa, formato["extension"])
            ruta_destino = os.path.join(subcarpeta, nombre_archivo)
            self._convertir_vector(ruta_origen, nombre_capa, ruta_destino, formato)
            rutas_generadas.append(ruta_destino)
        return rutas_generadas

    def _convertir_vector(self, ruta_origen, nombre_capa, ruta_destino, formato):
        """Lee GeoPackage origen y escribe en el formato destino."""
        try:
            import geopandas as gpd

            geodataframe = gpd.read_file(ruta_origen, layer=nombre_capa)
            if len(geodataframe) == 0:
                geodataframe = gpd.read_file(ruta_origen)
            kwargs = {"driver": formato["controlador"]}
            if formato["controlador"] == "GPKG":
                kwargs["layer"] = nombre_capa
            geodataframe.to_file(ruta_destino, **kwargs)
        except ImportError:
            self._convertir_vector_con_qgis(ruta_origen, ruta_destino, formato)

    def _convertir_vector_con_qgis(self, ruta_origen, ruta_destino, formato):
        """Conversión vectorial alternativa con PyQGIS."""
        from qgis.core import QgsProject, QgsVectorFileWriter, QgsVectorLayer

        capa = QgsVectorLayer(ruta_origen, "capa_export", "ogr")
        if not capa.isValid():
            raise ValueError("No se pudo leer la capa: {}".format(ruta_origen))

        opciones = QgsVectorFileWriter.SaveVectorOptions()
        opciones.driverName = formato["controlador"]
        error = QgsVectorFileWriter.writeAsVectorFormatV3(
            capa,
            ruta_destino,
            QgsProject.instance().transformContext(),
            opciones,
        )
        if error[0] != QgsVectorFileWriter.NoError:
            raise IOError("Error al escribir vector: {}".format(error))

    def _exportar_csv(self, directorio):
        """Copia el informe CSV a la carpeta de exportación."""
        if not self.contexto.ruta_informe_csv or not os.path.isfile(
            self.contexto.ruta_informe_csv
        ):
            return None
        ruta_destino = os.path.join(directorio, os.path.basename(self.contexto.ruta_informe_csv))
        shutil.copy2(self.contexto.ruta_informe_csv, ruta_destino)
        return ruta_destino

    def _exportar_proyecto_qgis(self, directorio):
        """Guarda una copia del proyecto QGIS actual con las capas cargadas."""
        from qgis.core import QgsProject

        ruta_proyecto = os.path.join(directorio, NOMBRE_PROYECTO_QGIS)
        proyecto = QgsProject.instance()
        if not proyecto.write(ruta_proyecto):
            raise IOError("No se pudo guardar el proyecto QGIS en: {}".format(ruta_proyecto))
        return ruta_proyecto

    def _escribir_manifiesto(self, directorio, archivos, opciones):
        """Genera un archivo de texto con el listado de productos exportados."""
        ruta_manifiesto = os.path.join(directorio, NOMBRE_MANIFIESTO_EXPORTACION)
        with open(ruta_manifiesto, "w", encoding="utf-8") as archivo:
            archivo.write("Manifiesto de exportación - Validador LiDAR\n")
            archivo.write("Fecha: {}\n\n".format(datetime.now().isoformat()))
            archivo.write("Opciones:\n")
            for clave, valor in sorted(opciones.items()):
                archivo.write("  - {}: {}\n".format(clave, valor))
            archivo.write("\nArchivos:\n")
            for ruta in archivos:
                archivo.write("  - {}\n".format(ruta))
        return ruta_manifiesto

    def _resolver_formato(self, texto_formato):
        """Obtiene la configuración del formato a partir del texto del combo."""
        for clave, configuracion in self.FORMATOS_VECTORIALES.items():
            if clave in texto_formato:
                return configuracion
        return self.FORMATOS_VECTORIALES["GeoPackage"]
