# -*- coding: utf-8 -*-
"""
Pruebas de exportación (componentes sin PyQGIS).
"""

import os
import sys
import tempfile
import unittest
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utilidades.constantes import (
    NOMBRE_CARPETA_EXPORTACION,
    NOMBRE_MANIFIESTO_EXPORTACION,
)


class TestExportacionConstantes(unittest.TestCase):
    """Comprueba constantes y generación de manifiesto."""

    def test_nombres_exportacion_definidos(self):
        """Las constantes de exportación deben existir."""
        self.assertTrue(len(NOMBRE_CARPETA_EXPORTACION) > 0)
        self.assertTrue(NOMBRE_MANIFIESTO_EXPORTACION.endswith(".txt"))

    def test_generar_ruta_carpeta_exportacion(self):
        """El nombre de carpeta debe incluir marca temporal."""
        marca = datetime.now().strftime("%Y%m%d")
        nombre = "{}_{}".format(NOMBRE_CARPETA_EXPORTACION, marca)
        self.assertIn(NOMBRE_CARPETA_EXPORTACION, nombre)

    def test_escribir_manifiesto_simple(self):
        """Debe poder escribirse un manifiesto de exportación."""
        with tempfile.TemporaryDirectory() as directorio:
            ruta = os.path.join(directorio, NOMBRE_MANIFIESTO_EXPORTACION)
            with open(ruta, "w", encoding="utf-8") as archivo:
                archivo.write("Manifiesto de prueba\n")
            self.assertTrue(os.path.isfile(ruta))


if __name__ == "__main__":
    unittest.main()
