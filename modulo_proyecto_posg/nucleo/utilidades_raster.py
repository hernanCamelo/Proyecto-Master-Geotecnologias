# -*- coding: utf-8 -*-
"""
Utilidades de rasterización y escritura GeoTIFF para modelos derivados LiDAR.
"""

import numpy as np

# Clasificaciones ASPRS usadas en el filtrado.
CLASE_TERRENO_ASPRS = 2
CLASE_EDIFICACION_ASPRS = 6
CLASES_RUIDO_ASPRS = (7, 18)


def calcular_extension_y_dimensiones(x, y, resolucion, margen_celdas=1):
    """
    Calcula extensión espacial y tamaño de la malla raster.

    :return: Tupla (xmin, ymin, xmax, ymax, ncols, nrows).
    """
    xmin = float(np.min(x))
    xmax = float(np.max(x))
    ymin = float(np.min(y))
    ymax = float(np.max(y))

    ancho = xmax - xmin
    alto = ymax - ymin
    if ancho <= 0 or alto <= 0:
        raise ValueError("La extensión de los puntos LiDAR no es válida.")

    ncols = int(np.ceil(ancho / resolucion)) + (2 * margen_celdas)
    nrows = int(np.ceil(alto / resolucion)) + (2 * margen_celdas)

    xmin = xmin - (margen_celdas * resolucion)
    ymax = ymax + (margen_celdas * resolucion)

    return xmin, ymin, xmax, ymax, ncols, nrows


def rasterizar_maximo(x, y, z, xmin, ymax, resolucion, ncols, nrows):
    """
    Rasteriza elevaciones usando el valor máximo por celda (DSM).

    :return: Matriz numpy (nrows, ncols) con nodata=np.nan.
    """
    return _rasterizar_agregacion(
        x, y, z, xmin, ymax, resolucion, ncols, nrows, metodo="maximo"
    )


def rasterizar_minimo(x, y, z, xmin, ymax, resolucion, ncols, nrows):
    """
    Rasteriza elevaciones usando el valor mínimo por celda (DTM).

    :return: Matriz numpy (nrows, ncols) con nodata=np.nan.
    """
    return _rasterizar_agregacion(
        x, y, z, xmin, ymax, resolucion, ncols, nrows, metodo="minimo"
    )


def _rasterizar_agregacion(x, y, z, xmin, ymax, resolucion, ncols, nrows, metodo):
    """Agrega puntos a celdas mediante máximo o mínimo."""
    malla = np.full((nrows, ncols), np.nan, dtype=np.float64)

    columnas = np.floor((x - xmin) / resolucion).astype(np.int64)
    filas = np.floor((ymax - y) / resolucion).astype(np.int64)

    mascara_valida = (
        (columnas >= 0)
        & (columnas < ncols)
        & (filas >= 0)
        & (filas < nrows)
        & np.isfinite(z)
    )
    columnas = columnas[mascara_valida]
    filas = filas[mascara_valida]
    valores = z[mascara_valida]

    if len(valores) == 0:
        return malla

    if metodo == "maximo":
        # np.maximum.at con NaN contamina el resultado; base temporal en -inf.
        temp = np.full((nrows, ncols), -np.inf, dtype=np.float64)
        np.maximum.at(temp, (filas, columnas), valores)
        mascara_finita = np.isfinite(temp)
        malla[mascara_finita] = temp[mascara_finita]
    else:
        temp = np.full((nrows, ncols), np.inf, dtype=np.float64)
        np.minimum.at(temp, (filas, columnas), valores)
        mascara_inf = np.isfinite(temp)
        malla[mascara_inf] = temp[mascara_inf]

    return malla


def calcular_ndsm(malla_dsm, malla_dtm):
    """
    Calcula el modelo normalizado nDSM = DSM - DTM.

    :return: Matriz nDSM con nodata donde falte DSM o DTM.
    """
    ndsm = np.full(malla_dsm.shape, np.nan, dtype=np.float64)
    mascara = np.isfinite(malla_dsm) & np.isfinite(malla_dtm)
    ndsm[mascara] = malla_dsm[mascara] - malla_dtm[mascara]
    return ndsm


def combinar_mallas_maximo(malla_a, malla_b):
    """Combina dos mallas tomando el máximo celda a celda (ignora nodata)."""
    resultado = malla_a.copy()
    mascara_b = np.isfinite(malla_b)
    mascara_a = np.isfinite(resultado)
    ambas = mascara_a & mascara_b
    solo_b = mascara_b & ~mascara_a
    if np.any(ambas):
        resultado[ambas] = np.maximum(resultado[ambas], malla_b[ambas])
    if np.any(solo_b):
        resultado[solo_b] = malla_b[solo_b]
    return resultado


def preparar_dtm_para_ndsm(malla_dtm, malla_dsm, max_iteraciones=40):
    """
    Interpola el DTM hacia celdas con DSM para poder calcular el nDSM.
    """
    resultado = malla_dtm.copy()
    mascara_dsm = np.isfinite(malla_dsm)

    for _ in range(max_iteraciones):
        falta = mascara_dsm & ~np.isfinite(resultado)
        if not np.any(falta):
            break
        relleno = _promedio_vecinos(resultado)
        resultado[falta & np.isfinite(relleno)] = relleno[falta & np.isfinite(relleno)]

    # Relleno final solo con elevación de terreno.
    falta = mascara_dsm & ~np.isfinite(resultado)
    if np.any(falta):
        minimo_terreno = np.nanmin(resultado)
        if np.isfinite(minimo_terreno):
            resultado[falta] = minimo_terreno

    return resultado


def calcular_ndsm_desde_dsm_dtm(malla_dsm, malla_dtm):
    """
    Calcula nDSM = DSM - DTM con interpolación del terreno bajo cubiertas.

    :return: Tupla (malla_ndsm, malla_dtm_preparado, malla_dsm_rellenado).
    """
    # Relleno de huecos del DSM antes de la resta.
    malla_dsm_listo = rellenar_nodata_maximo_vecino(malla_dsm, max_iteraciones=30)
    malla_dtm_listo = preparar_dtm_para_ndsm(malla_dtm, malla_dsm_listo)
    malla_ndsm = calcular_ndsm(malla_dsm_listo, malla_dtm_listo)

    # Valores negativos por ruido se truncan a cero.
    mascara = np.isfinite(malla_ndsm)
    malla_ndsm[mascara & (malla_ndsm < 0)] = 0.0
    return malla_ndsm, malla_dtm_listo, malla_dsm_listo


def resumir_estadisticas_mallas(malla_dsm, malla_dtm, malla_ndsm):
    """
    Genera estadísticas de cobertura para el registro de mensajes.

    :return: dict con conteos y altura máxima en nDSM.
    """
    mascara_dsm = np.isfinite(malla_dsm)
    mascara_dtm = np.isfinite(malla_dtm)
    mascara_ambas = mascara_dsm & mascara_dtm
    mascara_ndsm = np.isfinite(malla_ndsm)

    altura_max = float(np.nanmax(malla_ndsm)) if np.any(mascara_ndsm) else 0.0
    return {
        "celdas_dsm": int(np.sum(mascara_dsm)),
        "celdas_dtm": int(np.sum(mascara_dtm)),
        "celdas_solapadas": int(np.sum(mascara_ambas)),
        "celdas_ndsm": int(np.sum(mascara_ndsm)),
        "altura_max_ndsm": altura_max,
    }


def rellenar_nodata_vecino(malla, max_iteraciones=5):
    """
    Rellena celdas nodata con la media de vecinos válidos (suavizado simple).

    Útil cuando el DTM tiene huecos entre puntos de terreno.
    """
    resultado = malla.copy()
    for _ in range(max_iteraciones):
        mascara_nodata = ~np.isfinite(resultado)
        if not np.any(mascara_nodata):
            break
        relleno = _promedio_vecinos(resultado)
        resultado[mascara_nodata & np.isfinite(relleno)] = relleno[
            mascara_nodata & np.isfinite(relleno)
        ]
    return resultado


def rellenar_nodata_maximo_vecino(malla, max_iteraciones=20):
    """
    Rellena nodata con el máximo de vecinos (propaga alturas de cubierta en el DSM).
    """
    resultado = malla.copy()
    for _ in range(max_iteraciones):
        mascara_nodata = ~np.isfinite(resultado)
        if not np.any(mascara_nodata):
            break
        relleno = _maximo_vecinos(resultado)
        resultado[mascara_nodata & np.isfinite(relleno)] = relleno[
            mascara_nodata & np.isfinite(relleno)
        ]
    return resultado


def cerrar_mascara_binaria(mascara, iteraciones=2):
    """
    Cierra huecos interiores en la máscara de edificios (operación morfológica).

    Convierte anillos de celdas altas en polígonos rellenos antes de vectorizar.
    """
    mascara_bool = np.asarray(mascara, dtype=bool)
    if iteraciones <= 0:
        return mascara_bool

    try:
        from scipy.ndimage import binary_closing, generate_binary_structure

        estructura = generate_binary_structure(2, 2)
        return binary_closing(
            mascara_bool, structure=estructura, iterations=iteraciones
        )
    except ImportError:
        return _cerrar_mascara_numpy(mascara_bool, iteraciones)


def _cerrar_mascara_numpy(mascara, iteraciones):
    """Cierre morfológico sin scipy (dilatación + erosión)."""
    resultado = mascara.copy()
    for _ in range(iteraciones):
        resultado = _erosionar_binaria(_dilatar_binaria(resultado))
    return resultado


def _dilatar_binaria(mascara):
    """Dilatación binaria 8-vecinos."""
    acumulado = mascara.copy()
    for desplazamiento_fila in (-1, 0, 1):
        for desplazamiento_col in (-1, 0, 1):
            acumulado |= np.roll(
                np.roll(mascara, desplazamiento_fila, axis=0),
                desplazamiento_col,
                axis=1,
            )
    return acumulado


def _erosionar_binaria(mascara):
    """Erosión binaria 8-vecinos."""
    acumulado = mascara.copy()
    for desplazamiento_fila in (-1, 0, 1):
        for desplazamiento_col in (-1, 0, 1):
            acumulado &= np.roll(
                np.roll(mascara, desplazamiento_fila, axis=0),
                desplazamiento_col,
                axis=1,
            )
    return acumulado


def _maximo_vecinos(malla):
    """Calcula el máximo 3x3 de vecinos válidos."""
    vecinos = []
    for desplazamiento_fila in (-1, 0, 1):
        for desplazamiento_col in (-1, 0, 1):
            vecino = np.roll(malla, desplazamiento_fila, axis=0)
            vecinos.append(np.roll(vecino, desplazamiento_col, axis=1))
    return np.nanmax(np.stack(vecinos), axis=0)


def _promedio_vecinos(malla):
    """Calcula promedio 3x3 de vecinos válidos."""
    acumulado = np.zeros_like(malla, dtype=np.float64)
    cuenta = np.zeros_like(malla, dtype=np.float64)
    for desplazamiento_fila in (-1, 0, 1):
        for desplazamiento_col in (-1, 0, 1):
            vecino = np.roll(malla, desplazamiento_fila, axis=0)
            vecino = np.roll(vecino, desplazamiento_col, axis=1)
            mascara = np.isfinite(vecino)
            acumulado[mascara] += vecino[mascara]
            cuenta[mascara] += 1
    with np.errstate(invalid="ignore"):
        return acumulado / cuenta


def crear_transformacion_raster(xmin, ymax, resolucion):
    """
    Crea transformación afín desde origen superior izquierdo (sin PROJ/EPSG).

    :return: Objeto Affine compatible con rasterio.features.shapes.
    """
    try:
        from affine import Affine

        return Affine(resolucion, 0.0, xmin, 0.0, -resolucion, ymax)
    except ImportError:
        from rasterio.transform import from_origin

        return from_origin(xmin, ymax, resolucion, resolucion)


def guardar_geotiff(malla, xmin, ymax_superior, resolucion, ruta, crs):
    """
    Guarda una matriz float32 como GeoTIFF.

    Escribe el GeoTIFF con rasterio sin crs en cabecera; el CRS va en un .prj
    asociado para evitar conflictos PROJ entre pip y QGIS.

    :param malla: Matriz (nrows, ncols).
    :param xmin: Origen X del raster.
    :param ymax_superior: Coordenada Y superior (origen fila 0).
    :param resolucion: Tamaño de celda en unidades del CRS.
    :param ruta: Ruta de salida .tif.
    :param crs: QgsCoordinateReferenceSystem.
    """
    from ..utilidades.entorno_geoespacial import (
        configurar_entorno_geoespacial_qgis,
        escribir_archivo_prj_companion,
        obtener_wkt_desde_crs,
    )

    configurar_entorno_geoespacial_qgis()

    import rasterio

    nodata = -9999.0
    datos = np.where(np.isfinite(malla), malla, nodata).astype(np.float32)
    transformacion = crear_transformacion_raster(xmin, ymax_superior, resolucion)

    # Sin crs= en rasterio.open (compatibilidad PROJ).
    with rasterio.open(
        ruta,
        "w",
        driver="GTiff",
        height=datos.shape[0],
        width=datos.shape[1],
        count=1,
        dtype=datos.dtype,
        transform=transformacion,
        nodata=nodata,
    ) as dataset:
        dataset.write(datos, 1)

    wkt = obtener_wkt_desde_crs(crs)
    escribir_archivo_prj_companion(ruta, wkt)
