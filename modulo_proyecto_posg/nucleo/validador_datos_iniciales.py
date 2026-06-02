# -*- coding: utf-8 -*-
"""
Validaciones iniciales tras la extracción de huellas.
Comprobaciones de calidad antes de la validación catastral.
"""


class ValidadorDatosIniciales(object):
    """Realiza comprobaciones de coherencia espacial y de resultados intermedios."""

    def __init__(self, contexto):
        self.contexto = contexto

    def ejecutar(self):
        """
        Ejecuta validaciones iniciales y almacena resumen en el contexto.

        :return: Tupla (exito, mensaje).
        """
        if self.contexto.cancelado:
            return False, "Validación inicial cancelada."

        advertencias = []
        datos = self.contexto.datos_puntos

        if datos is None or datos.cantidad_puntos < 10:
            return False, "La nube de puntos es insuficiente para un análisis fiable."

        if self.contexto.cantidad_huellas == 0:
            return False, "No se generó ninguna huella de edificación."

        # Comprobar solapamiento de extensiones con la capa catastral.
        if self.contexto.capa_catastral is not None and self.contexto.extension_analisis:
            extension_lidar = self.contexto.extension_analisis
            extension_catastro = self.contexto.capa_catastral.extent()
            if not self._extensiones_solapan(extension_lidar, extension_catastro):
                advertencias.append(
                    "La extensión LiDAR y la catastral podrían no solaparse completamente."
                )

        if datos.tiene_clasificacion and datos.cantidad_terreno < 100:
            advertencias.append(
                "Pocos puntos de terreno (clase 2). El DTM puede ser impreciso."
            )

        self.contexto.resumen_validacion_inicial = {
            "puntos_totales": datos.cantidad_puntos,
            "puntos_terreno": datos.cantidad_terreno,
            "huellas_detectadas": self.contexto.cantidad_huellas,
            "advertencias": advertencias,
        }

        texto = (
            "Validación inicial correcta: {0} huellas, {1} puntos LiDAR."
        ).format(self.contexto.cantidad_huellas, datos.cantidad_puntos)

        if advertencias:
            texto += " Advertencias: " + " | ".join(advertencias)

        return True, texto

    @staticmethod
    def _extensiones_solapan(ext_a, ext_b):
        """Comprueba solapamiento entre dos extensiones (xmin, ymin, xmax, ymax)."""
        xmin_a, ymin_a, xmax_a, ymax_a = ext_a
        if hasattr(ext_b, "xMinimum"):
            xmin_b = ext_b.xMinimum()
            ymin_b = ext_b.yMinimum()
            xmax_b = ext_b.xMaximum()
            ymax_b = ext_b.yMaximum()
        else:
            xmin_b, ymin_b, xmax_b, ymax_b = ext_b

        solapa_x = not (xmax_a < xmin_b or xmax_b < xmin_a)
        solapa_y = not (ymax_a < ymin_b or ymax_b < ymin_a)
        return solapa_x and solapa_y
