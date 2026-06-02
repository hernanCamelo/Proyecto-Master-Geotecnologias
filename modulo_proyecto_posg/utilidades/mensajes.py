# -*- coding: utf-8 -*-
"""
Funciones auxiliares para registro de mensajes en la interfaz del complemento.
"""

from qgis.PyQt.QtWidgets import QMessageBox


def registrar_mensaje(panel, texto, es_error=False):
    """
    Añade una línea al panel de mensajes del dock.

    :param panel: QPlainTextEdit del complemento.
    :param texto: Texto a registrar.
    :param es_error: Si es True, antepone el prefijo ERROR.
    """
    if panel is None:
        return
    prefijo = "ERROR: " if es_error else ""
    panel.appendPlainText("{}{}".format(prefijo, texto))


def mostrar_advertencia(titulo, mensaje, ventana_padre=None):
    """Muestra un cuadro de diálogo de advertencia."""
    QMessageBox.warning(ventana_padre, titulo, mensaje)


def mostrar_error(titulo, mensaje, ventana_padre=None):
    """Muestra un cuadro de diálogo de error."""
    QMessageBox.critical(ventana_padre, titulo, mensaje)


def mostrar_informacion(titulo, mensaje, ventana_padre=None):
    """Muestra un cuadro de diálogo informativo."""
    QMessageBox.information(ventana_padre, titulo, mensaje)
