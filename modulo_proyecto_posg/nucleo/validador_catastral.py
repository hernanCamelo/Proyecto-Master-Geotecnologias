# -*- coding: utf-8 -*-
"""
Comparación espacial entre huellas LiDAR y cartografía catastral.
"""

import os

from ..utilidades.constantes import (
    NOMBRE_CAPA_COINCIDENTES,
    NOMBRE_CAPA_DEMOLICIONES,
    NOMBRE_CAPA_DISCREPANCIAS,
    NOMBRE_CAPA_HUELLAS,
    NOMBRE_CAPA_NUEVAS,
)
from .utilidades_geometria import (
    calcular_area_discrepancia,
    calcular_iou,
    capa_qgis_a_geodataframe,
    escribir_informe_csv,
    guardar_geodataframe,
    leer_huellas_desde_archivo,
)

# Columnas del informe CSV según especificación del proyecto.
COLUMNAS_INFORME_CSV = [
    "id_edificacion",
    "tipo_resultado",
    "area_lidar_m2",
    "area_catastro_m2",
    "area_discrepancia_m2",
    "porcentaje_coincidencia",
    "diferencia_superficies_m2",
    "distancia_centroides_m",
]


class ValidadorCatastral(object):
    """Calcula métricas de coincidencia e identifica inconsistencias."""

    def __init__(self, contexto):
        self.contexto = contexto

    def ejecutar(self):
        """
        Ejecuta la validación catastral y rellena métricas en el contexto.

        :return: Tupla (exito, mensaje).
        """
        if self.contexto.cancelado:
            return False, "Validación catastral cancelada."

        if not self.contexto.ruta_huellas or not os.path.isfile(self.contexto.ruta_huellas):
            return False, "No existen huellas LiDAR para validar."

        if self.contexto.capa_catastral is None:
            return False, "No hay capa catastral seleccionada."

        try:
            import geopandas as gpd
        except ImportError:
            return False, "Se requiere geopandas para la validación catastral."

        try:
            crs_trabajo = self.contexto.crs.authid()
            geodataframe_lidar = leer_huellas_desde_archivo(
                self.contexto.ruta_huellas,
                NOMBRE_CAPA_HUELLAS,
                crs_destino=crs_trabajo,
            )
            geodataframe_catastro = capa_qgis_a_geodataframe(self.contexto.capa_catastral)
            if geodataframe_catastro.crs and str(geodataframe_catastro.crs) != crs_trabajo:
                geodataframe_catastro = geodataframe_catastro.to_crs(crs_trabajo)

            resultados = self._clasificar_edificaciones(geodataframe_lidar, geodataframe_catastro)
            self._guardar_capas_resultado(resultados, crs_trabajo)
            self._generar_informe_csv(resultados["metricas"])

            resumen = resultados["resumen"]
            mensaje = (
                "Validación catastral: {0} coincidentes, {1} discrepancias, "
                "{2} nuevas, {3} posibles demoliciones."
            ).format(
                resumen["coincidentes"],
                resumen["discrepancias"],
                resumen["nuevas"],
                resumen["demoliciones"],
            )
            self.contexto.resumen_validacion_catastral = resumen
            return True, mensaje
        except Exception as error:
            return False, "Error en validación catastral: {}".format(error)

    def _clasificar_edificaciones(self, geodataframe_lidar, geodataframe_catastro):
        """
        Compara cada huella LiDAR con la cartografía y clasifica el resultado.

        :return: dict con GeoDataFrames por categoría y lista de métricas.
        """
        import geopandas as gpd

        umbral_iou = self.contexto.porcentaje_minimo_coincidencia / 100.0
        tolerancia = self.contexto.distancia_tolerancia
        umbral_cambio_area = 0.15

        lista_coincidentes = []
        lista_discrepancias = []
        lista_nuevas = []
        metricas = []
        catastro_emparejado = set()

        # Índice espacial para acelerar la búsqueda de candidatos catastrales.
        indice_espacial = geodataframe_catastro.sindex

        for indice_lidar, fila_lidar in geodataframe_lidar.iterrows():
            if self.contexto.cancelado:
                break

            geometria_lidar = fila_lidar.geometry
            id_lidar = fila_lidar.get("id_edif", indice_lidar)
            area_lidar = geometria_lidar.area

            mejor_iou, mejor_indice_catastro, mejor_distancia = (
                self._buscar_mejor_emparejamiento(
                    geometria_lidar, geodataframe_catastro, indice_espacial
                )
            )

            id_catastro = None
            area_catastro = 0.0
            tipo_resultado = "nueva_construccion"
            geometria_salida = geometria_lidar

            if mejor_indice_catastro is not None and mejor_iou > 0.01:
                fila_cat = geodataframe_catastro.loc[mejor_indice_catastro]
                id_catastro = fila_cat.get("id_catastro", mejor_indice_catastro)
                area_catastro = fila_cat.geometry.area
                area_discrepancia = calcular_area_discrepancia(
                    geometria_lidar, fila_cat.geometry
                )
                diferencia_superficies = area_lidar - area_catastro
                cambio_relativo = (
                    abs(diferencia_superficies) / area_catastro if area_catastro > 0 else 1.0
                )

                if (
                    mejor_iou >= umbral_iou
                    and mejor_distancia <= tolerancia
                    and cambio_relativo <= umbral_cambio_area
                ):
                    tipo_resultado = "coincidente"
                    geometria_salida = geometria_lidar.intersection(fila_cat.geometry)
                    if geometria_salida.is_empty:
                        geometria_salida = geometria_lidar
                    lista_coincidentes.append(
                        self._crear_registro(
                            id_lidar, id_catastro, geometria_salida, tipo_resultado,
                            area_lidar, area_catastro, area_discrepancia,
                            mejor_iou, diferencia_superficies, mejor_distancia,
                        )
                    )
                    catastro_emparejado.add(mejor_indice_catastro)
                else:
                    if mejor_distancia > tolerancia:
                        tipo_resultado = "desplazamiento_espacial"
                    elif cambio_relativo > umbral_cambio_area:
                        tipo_resultado = "cambio_superficie"
                    else:
                        tipo_resultado = "discrepancia_geometrica"
                    lista_discrepancias.append(
                        self._crear_registro(
                            id_lidar, id_catastro, geometria_lidar, tipo_resultado,
                            area_lidar, area_catastro, area_discrepancia,
                            mejor_iou, diferencia_superficies, mejor_distancia,
                        )
                    )
                    catastro_emparejado.add(mejor_indice_catastro)
            else:
                area_discrepancia = area_lidar
                diferencia_superficies = area_lidar
                mejor_distancia = 0.0
                mejor_iou = 0.0
                lista_nuevas.append(
                    self._crear_registro(
                        id_lidar, None, geometria_lidar, tipo_resultado,
                        area_lidar, 0.0, area_discrepancia,
                        mejor_iou, diferencia_superficies, mejor_distancia,
                    )
                )

            metricas.append(
                self._crear_fila_metrica(
                    id_lidar, id_catastro, tipo_resultado,
                    area_lidar, area_catastro,
                    area_discrepancia if mejor_indice_catastro is not None else area_lidar,
                    mejor_iou, diferencia_superficies if mejor_indice_catastro is not None else area_lidar,
                    mejor_distancia if mejor_distancia is not None else 0.0,
                )
            )

        lista_demoliciones = []
        for indice_cat, fila_cat in geodataframe_catastro.iterrows():
            if indice_cat in catastro_emparejado:
                continue
            id_catastro = fila_cat.get("id_catastro", indice_cat)
            registro = {
                "id_edif_lidar": None,
                "id_edif_catastro": id_catastro,
                "tipo_inconsistencia": "posible_demolicion",
                "area_lidar_m2": 0.0,
                "area_catastro_m2": round(fila_cat.geometry.area, 2),
                "area_discrepancia_m2": round(fila_cat.geometry.area, 2),
                "porcentaje_coincidencia": 0.0,
                "diferencia_superficies_m2": round(-fila_cat.geometry.area, 2),
                "distancia_centroides_m": 0.0,
                "geometry": fila_cat.geometry,
            }
            lista_demoliciones.append(registro)
            metricas.append(
                self._crear_fila_metrica(
                    "CAT_{}".format(id_catastro),
                    id_catastro,
                    "posible_demolicion",
                    0.0,
                    fila_cat.geometry.area,
                    fila_cat.geometry.area,
                    0.0,
                    -fila_cat.geometry.area,
                    0.0,
                )
            )

        def a_geodataframe(lista_registros, crs):
            if not lista_registros:
                return gpd.GeoDataFrame(
                    columns=["geometry"], crs=crs, geometry="geometry"
                )
            return gpd.GeoDataFrame(lista_registros, crs=crs)

        crs = geodataframe_lidar.crs
        return {
            "coincidentes": a_geodataframe(lista_coincidentes, crs),
            "discrepancias": a_geodataframe(lista_discrepancias, crs),
            "nuevas": a_geodataframe(lista_nuevas, crs),
            "demoliciones": a_geodataframe(lista_demoliciones, crs),
            "metricas": metricas,
            "resumen": {
                "coincidentes": len(lista_coincidentes),
                "discrepancias": len(lista_discrepancias),
                "nuevas": len(lista_nuevas),
                "demoliciones": len(lista_demoliciones),
            },
        }

    @staticmethod
    def _buscar_mejor_emparejamiento(geometria_lidar, geodataframe_catastro, indice_espacial):
        """
        Busca el polígono catastral con mayor IoU usando el índice espacial R-tree.

        :return: Tupla (mejor_iou, indice_catastro, distancia_centroides).
        """
        mejor_iou = 0.0
        mejor_indice = None
        mejor_distancia = None

        candidatos = list(indice_espacial.intersection(geometria_lidar.bounds))
        if not candidatos:
            return mejor_iou, mejor_indice, mejor_distancia

        for indice_cat in candidatos:
            if indice_cat not in geodataframe_catastro.index:
                continue
            fila_cat = geodataframe_catastro.loc[indice_cat]
            geometria_cat = fila_cat.geometry
            iou = calcular_iou(geometria_lidar, geometria_cat)
            if iou > mejor_iou:
                mejor_iou = iou
                mejor_indice = indice_cat
                mejor_distancia = geometria_lidar.centroid.distance(geometria_cat.centroid)

        return mejor_iou, mejor_indice, mejor_distancia

    @staticmethod
    def _crear_registro(
        id_lidar, id_catastro, geometria, tipo, area_lidar, area_catastro,
        area_discrepancia, iou, diferencia_superficies, distancia,
    ):
        """Construye un registro para GeoDataFrame de salida."""
        return {
            "id_edif_lidar": id_lidar,
            "id_edif_catastro": id_catastro,
            "tipo_inconsistencia": tipo,
            "area_lidar_m2": round(area_lidar, 2),
            "area_catastro_m2": round(area_catastro, 2),
            "area_discrepancia_m2": round(area_discrepancia, 2),
            "porcentaje_coincidencia": round(iou * 100.0, 2),
            "diferencia_superficies_m2": round(diferencia_superficies, 2),
            "distancia_centroides_m": round(distancia, 2),
            "geometry": geometria,
        }

    @staticmethod
    def _crear_fila_metrica(
        id_edificacion, id_catastro, tipo, area_lidar, area_catastro,
        area_discrepancia, iou, diferencia_superficies, distancia,
    ):
        """Construye una fila para el informe CSV."""
        return {
            "id_edificacion": id_edificacion,
            "tipo_resultado": tipo,
            "area_lidar_m2": round(area_lidar, 2),
            "area_catastro_m2": round(area_catastro, 2),
            "area_discrepancia_m2": round(area_discrepancia, 2),
            "porcentaje_coincidencia": round(iou * 100.0, 2),
            "diferencia_superficies_m2": round(diferencia_superficies, 2),
            "distancia_centroides_m": round(distancia, 2),
        }

    def _guardar_capas_resultado(self, resultados, crs):
        """Guarda las capas vectoriales clasificadas en el directorio de salida."""
        directorio = self.contexto.directorio_salida

        rutas = {
            "coincidentes": os.path.join(directorio, "{}.gpkg".format(NOMBRE_CAPA_COINCIDENTES)),
            "discrepancias": os.path.join(directorio, "{}.gpkg".format(NOMBRE_CAPA_DISCREPANCIAS)),
            "nuevas": os.path.join(directorio, "{}.gpkg".format(NOMBRE_CAPA_NUEVAS)),
            "demoliciones": os.path.join(directorio, "{}.gpkg".format(NOMBRE_CAPA_DEMOLICIONES)),
        }
        nombres_capa = {
            "coincidentes": NOMBRE_CAPA_COINCIDENTES,
            "discrepancias": NOMBRE_CAPA_DISCREPANCIAS,
            "nuevas": NOMBRE_CAPA_NUEVAS,
            "demoliciones": NOMBRE_CAPA_DEMOLICIONES,
        }

        for clave, ruta in rutas.items():
            guardar_geodataframe(resultados[clave], ruta, nombres_capa[clave])

        self.contexto.ruta_coincidentes = rutas["coincidentes"]
        self.contexto.ruta_discrepancias = rutas["discrepancias"]
        self.contexto.ruta_nuevas = rutas["nuevas"]
        self.contexto.ruta_demoliciones = rutas["demoliciones"]

    def _generar_informe_csv(self, metricas):
        """Escribe el CSV de métricas en el directorio de salida."""
        ruta_csv = os.path.join(
            self.contexto.directorio_salida, "informe_validacion_catastral.csv"
        )
        escribir_informe_csv(ruta_csv, metricas, COLUMNAS_INFORME_CSV)
        self.contexto.metricas_validacion = metricas
        self.contexto.ruta_informe_csv = ruta_csv
