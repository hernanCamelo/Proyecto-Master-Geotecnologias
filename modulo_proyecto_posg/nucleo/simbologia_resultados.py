# -*- coding: utf-8 -*-
"""
Aplicación de simbología temática y etiquetado a las capas de resultados.
"""

import os

from qgis.core import (
    Qgis,
    QgsPalLayerSettings,
    QgsProperty,
    QgsSingleSymbolRenderer,
    QgsSymbol,
    QgsTextFormat,
    QgsVectorLayerSimpleLabeling,
)
from qgis.PyQt.QtGui import QColor


class SimbologiaResultados(object):
    """Carga estilos QML o aplica simbología programática."""

    # Colores temáticos (R, G, B, transparencia).
    COLORES = {
        "coincidentes": QColor(34, 139, 34, 180),
        "discrepancias": QColor(255, 140, 0, 180),
        "nuevas": QColor(220, 20, 60, 180),
        "demoliciones": QColor(128, 0, 128, 180),
        "huellas": QColor(70, 130, 180, 120),
    }

    def __init__(self, directorio_plugin):
        """
        :param directorio_plugin: Ruta raíz del complemento (para carpeta estilos/).
        """
        self.directorio_estilos = os.path.join(directorio_plugin, "estilos")

    def aplicar_simbologia(self, contexto):
        """
        Aplica estilos y etiquetas a las capas del contexto.

        :return: Tupla (exito, mensaje).
        """
        capas_aplicadas = 0
        configuracion = (
            (contexto.capa_coincidentes, "coincidentes.qml", "coincidentes", False),
            (contexto.capa_discrepancias, "discrepancias.qml", "discrepancias", True),
            (contexto.capa_nuevas, "nuevas_construcciones.qml", "nuevas", True),
            (contexto.capa_demoliciones, "posibles_demoliciones.qml", "demoliciones", True),
            (contexto.capa_huellas, None, "huellas", False),
        )

        for capa, archivo_qml, clave_color, etiquetar in configuracion:
            if capa is None or not capa.isValid():
                continue
            if archivo_qml and self._cargar_estilo_qml(capa, archivo_qml):
                capas_aplicadas += 1
            else:
                self._aplicar_color_relleno(capa, self.COLORES[clave_color])
                capas_aplicadas += 1
            if etiquetar:
                self._aplicar_etiquetas(capa, "tipo_inconsistencia")
            capa.triggerRepaint()

        if capas_aplicadas == 0:
            return False, "No hay capas de validación cargadas para simbolizar."
        return True, "Simbología aplicada a {} capas.".format(capas_aplicadas)

    def _cargar_estilo_qml(self, capa, nombre_archivo):
        """Intenta cargar un archivo QML; devuelve True si tuvo éxito."""
        ruta = self.ruta_estilo(nombre_archivo)
        if not os.path.isfile(ruta):
            return False
        estilo, exito = capa.loadNamedStyle(ruta)
        return exito

    def _aplicar_color_relleno(self, capa, color):
        """Aplica símbolo de polígono con color semitransparente."""
        simbolo = QgsSymbol.defaultSymbol(capa.geometryType())
        simbolo.setColor(color)
        capa.setRenderer(QgsSingleSymbolRenderer(simbolo))

    def _aplicar_etiquetas(self, capa, nombre_campo):
        """
        Activa etiquetas con el campo de tipo de inconsistencia.

        :param capa: Capa vectorial QGIS.
        :param nombre_campo: Nombre del atributo a etiquetar.
        """
        indice_campo = capa.fields().indexFromName(nombre_campo)
        if indice_campo < 0:
            return

        try:
            configuracion = QgsPalLayerSettings()
            configuracion.fieldName = nombre_campo
            configuracion.enabled = True
            configuracion.placement = Qgis.LabelPlacement.Horizontal

            formato_texto = QgsTextFormat()
            formato_texto.setColor(QColor(0, 0, 0))
            formato_texto.setSize(9)
            configuracion.setFormat(formato_texto)
            configuracion.setDataDefinedProperty(
                QgsPalLayerSettings.Property.Show,
                QgsProperty.fromField(nombre_campo),
            )

            capa.setLabeling(QgsVectorLayerSimpleLabeling(configuracion))
            capa.setLabelsEnabled(True)
        except Exception:
            # Si falla el etiquetado, se desactiva sin interrumpir la simbología.
            capa.setLabelsEnabled(False)

    def ruta_estilo(self, nombre_archivo):
        """Devuelve la ruta completa a un archivo QML de estilo."""
        return os.path.join(self.directorio_estilos, nombre_archivo)
