# -*- coding: utf-8 -*-
"""
Configuración del entorno GDAL/PROJ para el complemento en QGIS.
"""


def configurar_entorno_geoespacial_qgis():
    """
    Configura GDAL_DATA de QGIS y prioriza paquetes del Python de QGIS.

    No se debe forzar PROJ_LIB/PROJ_DATA hacia share/proj de QGIS cuando
    rasterio/pyproj de pip están activos (conflicto proj.db v4 vs PROJ v6+).
    """
    import os

    priorizar_paquetes_python_qgis()
    _limpiar_proj_forzado_a_qgis()

    try:
        from qgis.core import QgsApplication

        prefijo = QgsApplication.prefixPath()
        ruta_gdal = os.path.join(prefijo, "share", "gdal")
        if os.path.isdir(ruta_gdal):
            os.environ["GDAL_DATA"] = ruta_gdal
    except Exception:
        pass


def priorizar_paquetes_python_qgis():
    """
    Coloca site-packages de QGIS antes que el de usuario (Roaming).

    Reduce errores 'numpy.core.multiarray failed to import' al cargar osgeo.gdal
    u otras extensiones compiladas contra el NumPy de QGIS.
    """
    import os
    import sys

    try:
        ejecutable = sys.executable
        if "qgis" not in ejecutable.lower() and "QGIS" not in ejecutable:
            return
        ruta_lib = os.path.join(os.path.dirname(ejecutable), "Lib", "site-packages")
        ruta_lib = os.path.normpath(ruta_lib)
        if os.path.isdir(ruta_lib) and ruta_lib not in sys.path:
            sys.path.insert(0, ruta_lib)
    except Exception:
        pass


def _limpiar_proj_forzado_a_qgis():
    """
    Elimina PROJ_LIB/PROJ_DATA si apuntan al directorio proj de QGIS.

    Así las librerías de pip usan su propia base de datos PROJ compatible.
    """
    import os

    for variable in ("PROJ_LIB", "PROJ_DATA"):
        ruta = os.environ.get(variable, "")
        if not ruta:
            continue
        ruta_normalizada = ruta.replace("\\", "/").lower()
        if "qgis" in ruta_normalizada and "/share/proj" in ruta_normalizada:
            os.environ.pop(variable, None)


def obtener_wkt_desde_crs(crs):
    """
    Obtiene WKT del CRS de QGIS sin resolver códigos EPSG externos.

    :param crs: QgsCoordinateReferenceSystem
    :return: Cadena WKT o None.
    """
    if crs is None:
        return None
    if hasattr(crs, "isValid") and not crs.isValid():
        return None
    if hasattr(crs, "toWkt"):
        wkt = crs.toWkt()
        if wkt:
            return wkt
    return None


def escribir_archivo_prj_companion(ruta_tif, wkt):
    """
    Escribe un .prj junto al GeoTIFF por si GDAL no acepta el WKT en cabecera.

    :param ruta_tif: Ruta al .tif.
    :param wkt: WKT del sistema de referencia.
    """
    if not wkt:
        return
    import os

    ruta_prj = os.path.splitext(ruta_tif)[0] + ".prj"
    with open(ruta_prj, "w", encoding="utf-8") as archivo:
        archivo.write(wkt)
