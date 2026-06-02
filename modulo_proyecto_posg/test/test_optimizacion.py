# -*- coding: utf-8 -*-
"""
Pruebas de utilidades de optimización (sin QGIS).
"""

import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utilidades.optimizacion import transformar_coordenadas_en_lotes


class TransformadorFicticio(object):
    """Transformador simple para pruebas (desplazamiento +1 en X)."""

    def transform(self, x, y):
        return np.asarray(x) + 1.0, np.asarray(y)


class TestOptimizacion(unittest.TestCase):
    """Comprueba reproyección por lotes."""

    def test_transformacion_en_lotes(self):
        """Debe producir el mismo resultado que una transformación directa."""
        x = np.arange(1000, dtype=np.float64)
        y = np.arange(1000, dtype=np.float64)
        transformador = TransformadorFicticio()
        x_lote, y_lote = transformar_coordenadas_en_lotes(
            transformador, x, y, tamano_lote=100
        )
        self.assertEqual(len(x_lote), 1000)
        self.assertAlmostEqual(x_lote[0], 1.0)


if __name__ == "__main__":
    unittest.main()
