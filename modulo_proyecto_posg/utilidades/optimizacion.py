# -*- coding: utf-8 -*-
"""
Utilidades de optimización para procesamiento de grandes volúmenes de datos.
"""

import numpy as np

from .constantes import TAMANO_LOTE_REPROYECCION


def transformar_coordenadas_en_lotes(transformador, x, y, tamano_lote=None):
    """
    Reproyecta coordenadas en bloques para reducir picos de memoria.

    :param transformador: Instancia pyproj.Transformer con always_xy=True.
    :param x: Array de coordenadas X.
    :param y: Array de coordenadas Y.
    :param tamano_lote: Tamaño de cada bloque.
    :return: Tupla (x_nuevo, y_nuevo) como arrays numpy.
    """
    if tamano_lote is None:
        tamano_lote = TAMANO_LOTE_REPROYECCION

    cantidad = len(x)
    if cantidad == 0:
        return np.array([]), np.array([])

    if cantidad <= tamano_lote:
        x_nuevo, y_nuevo = transformador.transform(x, y)
        return np.asarray(x_nuevo, dtype=np.float64), np.asarray(y_nuevo, dtype=np.float64)

    lista_x = []
    lista_y = []
    for inicio in range(0, cantidad, tamano_lote):
        fin = min(inicio + tamano_lote, cantidad)
        bloque_x, bloque_y = transformador.transform(x[inicio:fin], y[inicio:fin])
        lista_x.append(np.asarray(bloque_x, dtype=np.float64))
        lista_y.append(np.asarray(bloque_y, dtype=np.float64))

    return np.concatenate(lista_x), np.concatenate(lista_y)


def advertir_archivo_muy_grande(cantidad_puntos, umbral):
    """
    Indica si conviene advertir al usuario por tamaño de nube de puntos.

    :return: Mensaje de advertencia o cadena vacía.
    """
    if cantidad_puntos > umbral:
        return (
            "La nube contiene {0} puntos. El procesamiento puede tardar varios minutos."
        ).format(cantidad_puntos)
    return ""
