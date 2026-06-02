# coding=utf-8
"""
Pruebas del panel dock del complemento (requiere entorno QGIS).
"""

__author__ = "idu082127@usal.es"
__date__ = "2026-06-01"
__copyright__ = "Copyright 2026, Hernan Dario Camelo Pinzon"

import unittest

from qgis.PyQt.QtWidgets import QDockWidget

from modulo_proyecto_posg_dockwidget import ModuloProyectoDockWidget

from utilities import get_qgis_app

QGIS_APP = get_qgis_app()


class ModuloProyectoDockWidgetTest(unittest.TestCase):
    """Comprueba la creación del dock y widgets principales."""

    def setUp(self):
        """Inicializa el dock antes de cada prueba."""
        self.dockwidget = ModuloProyectoDockWidget(None)

    def tearDown(self):
        """Libera referencias tras cada prueba."""
        self.dockwidget.close()
        self.dockwidget = None

    def test_dockwidget_es_qdockwidget(self):
        """El widget raíz debe ser un QDockWidget."""
        self.assertIsInstance(self.dockwidget, QDockWidget)

    def test_pestanas_principales_existen(self):
        """Deben existir las cinco pestañas del diseño."""
        self.assertIsNotNone(self.dockwidget.pestana_entradas)
        self.assertIsNotNone(self.dockwidget.pestana_parametros)
        self.assertIsNotNone(self.dockwidget.pestana_procesamiento)
        self.assertIsNotNone(self.dockwidget.pestana_resultados)
        self.assertIsNotNone(self.dockwidget.pestana_exportacion)

    def test_botones_procesamiento_conectados(self):
        """Los botones principales deben estar habilitados según estado inicial."""
        self.assertTrue(self.dockwidget.btn_ejecutar_procesamiento.isEnabled())
        self.assertFalse(self.dockwidget.btn_cancelar_analisis.isEnabled())


if __name__ == "__main__":
    suite = unittest.makeSuite(ModuloProyectoDockWidgetTest)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
