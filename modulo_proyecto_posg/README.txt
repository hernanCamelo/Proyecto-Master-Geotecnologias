Validador LiDAR de huella urbana
=================================

Complemento QGIS para validacion de huellas urbanas (LiDAR + catastro).

Version: 1.0
Autor: Hernan Dario Camelo Pinzon

INSTALACION DE DEPENDENCIAS (Python de QGIS)
--------------------------------------------
python -m pip install numpy laspy lazrs rasterio shapely geopandas

USO RAPIDO
----------
1. Activar el complemento en QGIS.
2. Menu: Validador LiDAR de huella urbana.
3. Entradas: archivo LAS/LAZ, capa catastral, directorio salida, CRS.
4. Parametros: umbrales de deteccion y validacion.
5. Procesamiento: Ejecutar procesamiento.
6. Resultados: visibilidad y simbologia.
7. Exportacion: raster, vectorial, CSV y proyecto .qgz.

DOCUMENTACION
-----------
Ver DOCUMENTACION_TECNICA.md

PRUEBAS
-------
python -m unittest test.test_utilidades_geometria test.test_gestor_entradas test.test_exportador
