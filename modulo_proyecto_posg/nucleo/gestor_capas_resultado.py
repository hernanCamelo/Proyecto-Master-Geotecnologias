# -*- coding: utf-8 -*-
"""
Carga y gestión de capas de resultados en el proyecto QGIS.
"""

import os

from qgis.core import QgsProject, QgsRasterLayer, QgsVectorLayer

from ..utilidades.constantes import (
    NOMBRE_CAPA_COINCIDENTES,
    NOMBRE_CAPA_DEMOLICIONES,
    NOMBRE_CAPA_DISCREPANCIAS,
    NOMBRE_CAPA_DSM,
    NOMBRE_CAPA_DTM,
    NOMBRE_CAPA_HUELLAS,
    NOMBRE_CAPA_NDSM,
    NOMBRE_CAPA_NUEVAS,
)


class GestorCapasResultado(object):
    """Añade capas al proyecto y controla su visibilidad."""

    NOMBRE_GRUPO = "Validador LiDAR - Resultados"

    def __init__(self, contexto):
        self.contexto = contexto

    def registrar_capas_en_proyecto(self):
        """
        Carga en QGIS los productos raster, huellas y validación catastral.
        Debe ejecutarse en el hilo principal de la interfaz.
        """
        self.contexto.capa_dsm = self._cargar_raster(
            self.contexto.ruta_dsm, NOMBRE_CAPA_DSM
        )
        self.contexto.capa_dtm = self._cargar_raster(
            self.contexto.ruta_dtm, NOMBRE_CAPA_DTM
        )
        self.contexto.capa_ndsm = self._cargar_raster(
            self.contexto.ruta_ndsm, NOMBRE_CAPA_NDSM
        )
        self.contexto.capa_huellas = self._cargar_vectorial(
            self.contexto.ruta_huellas, NOMBRE_CAPA_HUELLAS
        )
        self.contexto.capa_coincidentes = self._cargar_vectorial(
            self.contexto.ruta_coincidentes, NOMBRE_CAPA_COINCIDENTES
        )
        self.contexto.capa_discrepancias = self._cargar_vectorial(
            self.contexto.ruta_discrepancias, NOMBRE_CAPA_DISCREPANCIAS
        )
        self.contexto.capa_nuevas = self._cargar_vectorial(
            self.contexto.ruta_nuevas, NOMBRE_CAPA_NUEVAS
        )
        self.contexto.capa_demoliciones = self._cargar_vectorial(
            self.contexto.ruta_demoliciones, NOMBRE_CAPA_DEMOLICIONES
        )

        self._organizar_grupo_resultados()

    def _cargar_raster(self, ruta, nombre_capa):
        """Crea y registra una capa raster si el archivo existe."""
        if not ruta or not os.path.isfile(ruta):
            return None
        capa = QgsRasterLayer(ruta, nombre_capa)
        if not capa.isValid():
            return None
        QgsProject.instance().addMapLayer(capa)
        return capa

    def _cargar_vectorial(self, ruta, nombre_capa):
        """Crea y registra una capa vectorial desde GeoPackage u OGR."""
        if not ruta or not os.path.isfile(ruta):
            return None
        capa = QgsVectorLayer(ruta, nombre_capa, "ogr")
        if not capa.isValid():
            capa = QgsVectorLayer(
                "{}|layername={}".format(ruta, nombre_capa), nombre_capa, "ogr"
            )
        if not capa.isValid():
            return None
        QgsProject.instance().addMapLayer(capa)
        return capa

    def _organizar_grupo_resultados(self):
        """Agrupa las capas de resultados bajo un mismo nodo del árbol."""
        raiz = QgsProject.instance().layerTreeRoot()
        grupo = raiz.findGroup(self.NOMBRE_GRUPO)
        if grupo is None:
            grupo = raiz.insertGroup(0, self.NOMBRE_GRUPO)

        capas_ordenadas = (
            self.contexto.capa_dsm,
            self.contexto.capa_dtm,
            self.contexto.capa_ndsm,
            self.contexto.capa_huellas,
            self.contexto.capa_coincidentes,
            self.contexto.capa_discrepancias,
            self.contexto.capa_nuevas,
            self.contexto.capa_demoliciones,
        )
        for capa in capas_ordenadas:
            if capa is None:
                continue
            nodo = raiz.findLayer(capa.id())
            if nodo is not None:
                grupo.addChildNode(nodo.clone())
                raiz.removeChildNode(nodo)

    def agregar_capa_al_proyecto(self, capa, activar=True):
        """
        Registra una capa en el proyecto QGIS.

        :param capa: QgsMapLayer a añadir.
        :param activar: Si es True, deja la capa visible en el árbol.
        """
        if capa is None or not capa.isValid():
            return
        QgsProject.instance().addMapLayer(capa, addToLegend=activar)

    def establecer_visibilidad(self, capa, visible):
        """Activa o desactiva una capa en el árbol de capas."""
        if capa is None:
            return
        arbol = QgsProject.instance().layerTreeRoot()
        nodo = arbol.findLayer(capa.id())
        if nodo is not None:
            nodo.setItemVisibilityChecked(visible)

    def obtener_capas_del_contexto(self):
        """
        Devuelve diccionario nombre lógico -> capa para los resultados.

        :return: dict
        """
        return {
            "dsm": self.contexto.capa_dsm,
            "dtm": self.contexto.capa_dtm,
            "ndsm": self.contexto.capa_ndsm,
            "huellas": self.contexto.capa_huellas,
            "coincidentes": self.contexto.capa_coincidentes,
            "discrepancias": self.contexto.capa_discrepancias,
            "nuevas": self.contexto.capa_nuevas,
            "demoliciones": self.contexto.capa_demoliciones,
        }
