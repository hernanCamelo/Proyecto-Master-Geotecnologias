# -*- coding: utf-8 -*-
"""
Utilidades de conversión y métricas geométricas para validación catastral.
"""

import csv
import os


def calcular_iou(geometria_a, geometria_b):
    """
    Calcula el índice de solapamiento (IoU) entre dos geometrías.

    :return: Valor entre 0 y 1.
    """
    if geometria_a is None or geometria_b is None:
        return 0.0
    if geometria_a.is_empty or geometria_b.is_empty:
        return 0.0
    if not geometria_a.intersects(geometria_b):
        return 0.0
    interseccion = geometria_a.intersection(geometria_b).area
    union = geometria_a.union(geometria_b).area
    if union <= 0:
        return 0.0
    return interseccion / union


def calcular_area_discrepancia(geometria_a, geometria_b):
    """Área de la diferencia simétrica entre dos polígonos."""
    if not geometria_a.intersects(geometria_b):
        return geometria_a.area + geometria_b.area
    return geometria_a.symmetric_difference(geometria_b).area


def capa_qgis_a_geodataframe(capa_vectorial):
    """
    Convierte una QgsVectorLayer a GeoDataFrame.

    :param capa_vectorial: Capa poligonal QGIS.
    :return: geopandas.GeoDataFrame
    """
    import geopandas as gpd
    from shapely import wkt

    registros = []
    for feature in capa_vectorial.getFeatures():
        geometria_qgis = feature.geometry()
        if geometria_qgis is None or geometria_qgis.isEmpty():
            continue
        registros.append(
            {
                "id_catastro": feature.id(),
                "geometry": wkt.loads(geometria_qgis.asWkt()),
            }
        )

    if not registros:
        raise ValueError("La capa catastral no contiene geometrías válidas.")

    crs = capa_vectorial.crs().authid() if capa_vectorial.crs().isValid() else None
    return gpd.GeoDataFrame(registros, crs=crs)


def leer_huellas_desde_archivo(ruta, nombre_capa, crs_destino=None):
    """
    Lee las huellas LiDAR desde GeoPackage.

    :return: geopandas.GeoDataFrame
    """
    import geopandas as gpd

    geodataframe = gpd.read_file(ruta, layer=nombre_capa)
    if crs_destino is not None and geodataframe.crs is not None:
        geodataframe = geodataframe.to_crs(crs_destino)
    elif crs_destino is not None:
        geodataframe.set_crs(crs_destino, inplace=True)
    return geodataframe


def guardar_geodataframe(geodataframe, ruta, nombre_capa):
    """Persiste un GeoDataFrame en GeoPackage (admite capas vacías)."""
    import geopandas as gpd

    if geodataframe is None:
        return False
    if len(geodataframe) == 0:
        geodataframe = gpd.GeoDataFrame(
            {
                "id_edif_lidar": [],
                "id_edif_catastro": [],
                "tipo_inconsistencia": [],
                "geometry": [],
            },
            crs=geodataframe.crs,
        )
    geodataframe.to_file(ruta, layer=nombre_capa, driver="GPKG")
    return True


def escribir_informe_csv(ruta, filas, nombres_columnas):
    """
    Escribe el informe CSV de métricas de validación.

    :param filas: Lista de diccionarios con las métricas.
    """
    directorio = os.path.dirname(ruta)
    if directorio and not os.path.isdir(directorio):
        os.makedirs(directorio)

    with open(ruta, "w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=nombres_columnas)
        escritor.writeheader()
        for fila in filas:
            escritor.writerow(fila)
