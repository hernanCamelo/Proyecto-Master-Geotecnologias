# -*- coding: utf-8 -*-
"""
Comprobación de librerías externas requeridas por el complemento.
"""

# Lista de dependencias previstas en la especificación del proyecto.
DEPENDENCIAS_REQUERIDAS = (
    "numpy",
    "shapely",
    "rasterio",
    "geopandas",
    "laspy",
)


class VerificadorDependencias(object):
    """Verifica la disponibilidad de librerías Python en el entorno de QGIS."""

    @staticmethod
    def comprobar_dependencias(opcionales=None):
        """
        Comprueba qué dependencias están instaladas.

        :param opcionales: Tupla de nombres adicionales (p. ej. pdal).
        :return: Tupla (faltantes, disponibles) con listas de nombres de módulo.
        """
        nombres = list(DEPENDENCIAS_REQUERIDAS)
        if opcionales:
            nombres.extend(opcionales)

        disponibles = []
        faltantes = []
        for nombre in nombres:
            try:
                __import__(nombre)
                disponibles.append(nombre)
            except ImportError:
                faltantes.append(nombre)

        return faltantes, disponibles

    @staticmethod
    def comprobar_pdal():
        """
        Comprueba si PDAL está disponible (módulo pdal o ejecutable en PATH).

        :return: True si se detecta PDAL.
        """
        try:
            import pdal  # noqa: F401
            return True
        except ImportError:
            pass
        import shutil
        return shutil.which("pdal") is not None

    @staticmethod
    def obtener_resumen():
        """
        Genera un texto resumen del estado de dependencias.

        :return: Cadena multilínea para el panel de mensajes.
        """
        faltantes, disponibles = VerificadorDependencias.comprobar_dependencias(
            opcionales=("pdal",)
        )
        lineas = ["Dependencias disponibles: {}".format(", ".join(disponibles) or "ninguna")]
        if faltantes:
            lineas.append("Dependencias faltantes: {}".format(", ".join(faltantes)))
        else:
            lineas.append("Todas las dependencias principales están instaladas.")
        if not VerificadorDependencias.comprobar_pdal() and "pdal" in faltantes:
            lineas.append(
                "PDAL no detectado (opcional). La lectura LiDAR usa laspy por defecto."
            )
        return "\n".join(lineas)
