# -*- coding: utf-8 -*-
"""
Pruebas de validación de parámetros numéricos (sin QGIS).
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestValidacionParametros(unittest.TestCase):
    """Replica las reglas de validación numérica para pruebas aisladas."""

    @staticmethod
    def validar_parametros(altura, resolucion, area_minima, tolerancia, porcentaje):
        """Misma lógica que GestorEntradas.validar_parametros_numericos."""
        if altura <= 0:
            return False, "La altura mínima de edificación debe ser mayor que cero."
        if resolucion <= 0:
            return False, "La resolución de rasterización debe ser mayor que cero."
        if area_minima <= 0:
            return False, "El área mínima de detección debe ser mayor que cero."
        if tolerancia < 0:
            return False, "La distancia de tolerancia no puede ser negativa."
        if porcentaje <= 0 or porcentaje > 100:
            return False, "El porcentaje mínimo de coincidencia debe estar entre 0 y 100."
        return True, ""

    def test_parametros_validos(self):
        es_valido, _ = self.validar_parametros(2.5, 1.0, 15.0, 2.0, 70.0)
        self.assertTrue(es_valido)

    def test_porcentaje_invalido(self):
        es_valido, _ = self.validar_parametros(2.5, 1.0, 15.0, 2.0, 150.0)
        self.assertFalse(es_valido)


if __name__ == "__main__":
    unittest.main()
