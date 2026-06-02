# -*- coding: utf-8 -*-
"""
Estructura de datos en memoria para una nube de puntos LiDAR procesada.
"""


class DatosPuntosLidar(object):
    """
    Almacena coordenadas y metadatos tras la lectura y filtrado del archivo LAS/LAZ.
    Los arrays numpy se asignan en el procesador LiDAR.
    """

    def __init__(self):
        """Inicializa contenedores vacíos."""
        self.x = None
        self.y = None
        self.z = None

        # Subconjuntos por clasificación ASPRS.
        self.x_terreno = None
        self.y_terreno = None
        self.z_terreno = None
        self.x_edificacion = None
        self.y_edificacion = None
        self.z_edificacion = None

        self.tiene_clasificacion = False
        self.cantidad_puntos = 0
        self.cantidad_terreno = 0
        self.cantidad_edificacion = 0

        # CRS detectado en el archivo (QgsCoordinateReferenceSystem o None).
        self.crs_origen = None
        self.crs_trabajo = None

        # Extensión en CRS de trabajo: (xmin, ymin, xmax, ymax).
        self.extension = None
