# Importación opcional de QGIS (solo disponible en el intérprete de QGIS).
try:
    import qgis  # pylint: disable=W0611  # NOQA
except ImportError:
    pass
