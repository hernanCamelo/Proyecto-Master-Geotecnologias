# -*- coding: utf-8 -*-
"""
Hilo de trabajo para ejecutar el pipeline sin bloquear la interfaz de QGIS.
"""

from qgis.PyQt.QtCore import QThread, pyqtSignal

from .extractor_huellas_edificaciones import ExtractorHuellasEdificaciones
from .generador_modelos_derivados import GeneradorModelosDerivados
from .procesador_lidar import ProcesadorLidar
from .validador_catastral import ValidadorCatastral
from .validador_datos_iniciales import ValidadorDatosIniciales
from ..utilidades.constantes import ETAPAS_PROCESAMIENTO


class HiloControladorProcesamiento(QThread):
    """
    Orquesta las etapas del análisis en segundo plano.
    Emite señales de progreso y mensajes hacia el dockwidget.
    """

    # Señales hacia la interfaz
    progreso_actualizado = pyqtSignal(int, str)
    mensaje_registrado = pyqtSignal(str, bool)
    procesamiento_finalizado = pyqtSignal(bool, str)

    def __init__(self, contexto, parent=None):
        super(HiloControladorProcesamiento, self).__init__(parent)
        self.contexto = contexto

    def run(self):
        """Ejecuta secuencialmente las etapas del pipeline."""
        try:
            etapas_ejecutores = [
                ("Validación de entradas", self._etapa_validacion_interna),
                ("Procesamiento LiDAR", self._etapa_procesador_lidar),
                ("Generación DSM/DTM/nDSM", self._etapa_generador_modelos),
                ("Extracción de huellas", self._etapa_extractor_huellas),
                ("Validaciones iniciales", self._etapa_validaciones_iniciales),
                ("Validación catastral", self._etapa_validador_catastral),
                ("Finalización", self._etapa_finalizacion),
            ]

            for nombre_etapa, funcion_etapa in etapas_ejecutores:
                if self.contexto.cancelado:
                    self.procesamiento_finalizado.emit(
                        False, "Análisis cancelado por el usuario."
                    )
                    return

                porcentaje = self._obtener_porcentaje_etapa(nombre_etapa)
                self.progreso_actualizado.emit(porcentaje, nombre_etapa)
                self.mensaje_registrado.emit(
                    "Iniciando: {}...".format(nombre_etapa), False
                )

                exito, mensaje = funcion_etapa()
                self.mensaje_registrado.emit(mensaje, not exito)

                if not exito:
                    self.procesamiento_finalizado.emit(False, mensaje)
                    return

            self.contexto.completado = True
            self.progreso_actualizado.emit(100, "Procesamiento finalizado")
            self.procesamiento_finalizado.emit(
                True,
                "Análisis completado. Use la pestaña Exportación para guardar "
                "productos finales y el proyecto QGIS.",
            )
        except Exception as error:
            self.procesamiento_finalizado.emit(
                False, "Error inesperado en el procesamiento: {}".format(error)
            )

    def _obtener_porcentaje_etapa(self, nombre):
        """Obtiene el porcentaje asociado a una etapa."""
        for nombre_etapa, porcentaje in ETAPAS_PROCESAMIENTO:
            if nombre_etapa == nombre:
                return porcentaje
        return 0

    def _etapa_validacion_interna(self):
        """La validación principal se realiza en el dock antes de lanzar el hilo."""
        return True, "Entradas validadas correctamente."

    def _etapa_procesador_lidar(self):
        return ProcesadorLidar(self.contexto).ejecutar()

    def _etapa_generador_modelos(self):
        return GeneradorModelosDerivados(self.contexto).ejecutar()

    def _etapa_extractor_huellas(self):
        return ExtractorHuellasEdificaciones(self.contexto).ejecutar()

    def _etapa_validaciones_iniciales(self):
        return ValidadorDatosIniciales(self.contexto).ejecutar()

    def _etapa_validador_catastral(self):
        return ValidadorCatastral(self.contexto).ejecutar()

    def _etapa_finalizacion(self):
        return True, "Archivos de salida listos para carga en el mapa."
