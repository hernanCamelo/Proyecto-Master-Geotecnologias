# -*- coding: utf-8 -*-
"""
Pruebas unitarias de métricas geométricas (sin dependencia de QGIS).
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shapely.geometry import box

from nucleo.utilidades_geometria import (
    calcular_area_discrepancia,
    calcular_iou,
)


class TestUtilidadesGeometria(unittest.TestCase):
    """Comprueba IoU y área de discrepancia."""

    def test_iou_poligonos_identicos(self):
        """Dos cuadrados iguales deben tener IoU = 1."""
        geometria = box(0, 0, 10, 10)
        self.assertAlmostEqual(calcular_iou(geometria, geometria), 1.0, places=5)

    def test_iou_sin_solapamiento(self):
        """Polígonos separados deben tener IoU = 0."""
        geometria_a = box(0, 0, 5, 5)
        geometria_b = box(10, 10, 15, 15)
        self.assertEqual(calcular_iou(geometria_a, geometria_b), 0.0)

    def test_iou_solapamiento_parcial(self):
        """Comprueba un caso de solapamiento del 50 % en unión."""
        geometria_a = box(0, 0, 10, 10)
        geometria_b = box(5, 0, 15, 10)
        iou = calcular_iou(geometria_a, geometria_b)
        self.assertGreater(iou, 0.0)
        self.assertLess(iou, 1.0)

    def test_area_discrepancia_sin_contacto(self):
        """Sin intersección, la discrepancia es la suma de áreas."""
        geometria_a = box(0, 0, 2, 2)
        geometria_b = box(5, 5, 7, 7)
        esperado = geometria_a.area + geometria_b.area
        self.assertAlmostEqual(
            calcular_area_discrepancia(geometria_a, geometria_b),
            esperado,
            places=3,
        )


if __name__ == "__main__":
    unittest.main()
