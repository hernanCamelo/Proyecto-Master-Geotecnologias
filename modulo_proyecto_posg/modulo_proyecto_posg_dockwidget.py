# -*- coding: utf-8 -*-
"""
Panel dock del complemento Validador LiDAR de huella urbana.
Gestiona la interfaz, validación de entradas y orquestación del hilo de procesamiento.
"""

import os

from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtCore import pyqtSignal, Qt
from qgis.PyQt.QtWidgets import QFileDialog
from qgis.core import QgsProject, QgsVectorLayer
from qgis.utils import iface as iface_qgis
from qgis.gui import QgsFileWidget, QgsMapLayerComboBox
from qgis.core import QgsMapLayerProxyModel

from .nucleo.contexto_analisis import ContextoAnalisis
from .nucleo.exportador_resultados import ExportadorResultados
from .nucleo.gestor_capas_resultado import GestorCapasResultado
from .nucleo.gestor_entradas import GestorEntradas
from .nucleo.hilo_controlador_procesamiento import HiloControladorProcesamiento
from .nucleo.simbologia_resultados import SimbologiaResultados
from .utilidades.constantes import VERSION_COMPLEMENTO
from .utilidades.mensajes import (
    mostrar_advertencia,
    mostrar_error,
    mostrar_informacion,
    registrar_mensaje,
)
from .utilidades.verificador_dependencias import VerificadorDependencias

FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "modulo_proyecto_posg_dockwidget_base.ui")
)


class ModuloProyectoDockWidget(QtWidgets.QDockWidget, FORM_CLASS):
    """Widget acoplable principal del complemento."""

    closingPlugin = pyqtSignal()

    def __init__(self, parent=None):
        """Inicializa la interfaz y las conexiones de señales."""
        super(ModuloProyectoDockWidget, self).__init__(parent)
        self.setupUi(self)

        self.directorio_plugin = os.path.dirname(__file__)
        self.contexto = ContextoAnalisis()
        self.hilo_procesamiento = None
        self.gestor_capas = GestorCapasResultado(self.contexto)
        self.simbologia = SimbologiaResultados(self.directorio_plugin)

        self._configurar_widgets()
        self._conectar_senales()
        self._estado_inicial_interfaz()
        self._configurar_entorno_geoespacial()  # Antes de comprobar dependencias

        registrar_mensaje(self.panel_mensajes, "Complemento iniciado correctamente.")
        registrar_mensaje(
            self.panel_mensajes, VerificadorDependencias.obtener_resumen()
        )

    def closeEvent(self, event):
        """Emite señal de cierre para limpieza del plugin principal."""
        if self.hilo_procesamiento is not None and self.hilo_procesamiento.isRunning():
            self.contexto.cancelado = True
            self.hilo_procesamiento.wait(3000)
        self.closingPlugin.emit()
        event.accept()

    def _configurar_entorno_geoespacial(self):
        """Alinea GDAL/NumPy/PROJ con el Python de QGIS al abrir el panel."""
        from .utilidades.entorno_geoespacial import (
            configurar_entorno_geoespacial_qgis,
            priorizar_paquetes_python_qgis,
        )

        priorizar_paquetes_python_qgis()
        configurar_entorno_geoespacial_qgis()

    def _configurar_widgets(self):
        """Configura filtros, valores por defecto y widgets QGIS nativos."""
        self.etiqueta_version_complemento.setText(
            "Versión {}".format(VERSION_COMPLEMENTO)
        )

        # Selector de archivo LiDAR.
        self.selector_archivo_lidar.setFilter("Archivos LiDAR (*.las *.laz)")
        self.selector_archivo_lidar.setStorageMode(QgsFileWidget.GetFile)

        # Directorio de salida.
        self.selector_directorio_salida.setStorageMode(QgsFileWidget.GetDirectory)

        # Capa catastral: solo polígonos del proyecto.
        self.selector_capa_catastral.setFilters(
            QgsMapLayerProxyModel.PolygonLayer
        )

        # CRS por defecto: del proyecto activo.
        crs_proyecto = QgsProject.instance().crs()
        if crs_proyecto.isValid():
            self.selector_sistema_referencia.setCrs(crs_proyecto)

        # Árbol de capas de resultados.
        self.arbol_capas_resultado.setHeaderLabels(["Capa", "Tipo"])
        self.arbol_capas_resultado.setColumnWidth(0, 220)

    def _conectar_senales(self):
        """Conecta botones y casillas de verificación a sus manejadores."""
        self.btn_ejecutar_procesamiento.clicked.connect(self._al_ejecutar_procesamiento)
        self.btn_cancelar_analisis.clicked.connect(self._al_cancelar_analisis)
        self.btn_limpiar_mensajes.clicked.connect(self._al_limpiar_mensajes)
        self.btn_cargar_catastro_desde_archivo.clicked.connect(
            self._al_cargar_catastro_desde_archivo
        )
        self.btn_aplicar_simbologia.clicked.connect(self._al_aplicar_simbologia)
        self.btn_zoom_resultados.clicked.connect(self._al_zoom_resultados)
        self.btn_exportar_resultados.clicked.connect(self._al_exportar_resultados)
        self.btn_ayuda.clicked.connect(self._al_mostrar_ayuda)

        # Visibilidad de capas de resultados.
        self.chk_mostrar_dsm.toggled.connect(
            lambda v: self._al_cambiar_visibilidad("dsm", v)
        )
        self.chk_mostrar_dtm.toggled.connect(
            lambda v: self._al_cambiar_visibilidad("dtm", v)
        )
        self.chk_mostrar_ndsm.toggled.connect(
            lambda v: self._al_cambiar_visibilidad("ndsm", v)
        )
        self.chk_mostrar_huellas_detectadas.toggled.connect(
            lambda v: self._al_cambiar_visibilidad("huellas", v)
        )
        self.chk_mostrar_coincidentes.toggled.connect(
            lambda v: self._al_cambiar_visibilidad("coincidentes", v)
        )
        self.chk_mostrar_discrepancias.toggled.connect(
            lambda v: self._al_cambiar_visibilidad("discrepancias", v)
        )
        self.chk_mostrar_nuevas_construcciones.toggled.connect(
            lambda v: self._al_cambiar_visibilidad("nuevas", v)
        )
        self.chk_mostrar_posibles_demoliciones.toggled.connect(
            lambda v: self._al_cambiar_visibilidad("demoliciones", v)
        )

    def _estado_inicial_interfaz(self):
        """Define el estado inicial de botones dependientes de resultados."""
        self.barra_progreso.setValue(0)
        self.etiqueta_estado.setText("Listo.")
        self._habilitar_controles_procesamiento(en_ejecucion=False)
        self._habilitar_controles_resultados(hay_resultados=False)

    def _habilitar_controles_procesamiento(self, en_ejecucion):
        """Activa o desactiva controles durante la ejecución del pipeline."""
        self.btn_ejecutar_procesamiento.setEnabled(not en_ejecucion)
        self.btn_cancelar_analisis.setEnabled(en_ejecucion)
        self.pestanero_principal.setEnabled(not en_ejecucion)

    def _habilitar_controles_resultados(self, hay_resultados):
        """Habilita pestaña de resultados y exportación cuando hay datos."""
        controles_check = (
            self.chk_mostrar_dsm,
            self.chk_mostrar_dtm,
            self.chk_mostrar_ndsm,
            self.chk_mostrar_huellas_detectadas,
            self.chk_mostrar_coincidentes,
            self.chk_mostrar_discrepancias,
            self.chk_mostrar_nuevas_construcciones,
            self.chk_mostrar_posibles_demoliciones,
        )
        for control in controles_check:
            control.setEnabled(hay_resultados)
        self.btn_aplicar_simbologia.setEnabled(hay_resultados)
        self.btn_zoom_resultados.setEnabled(hay_resultados)
        self.arbol_capas_resultado.setEnabled(hay_resultados)
        self.btn_exportar_resultados.setEnabled(hay_resultados)

    def _rellenar_contexto_desde_interfaz(self):
        """Transfiere los valores del formulario al contexto de análisis."""
        self.contexto.reiniciar_resultados()
        self.contexto.cancelado = False

        self.contexto.ruta_archivo_lidar = self.selector_archivo_lidar.filePath()
        self.contexto.capa_catastral = self.selector_capa_catastral.currentLayer()
        self.contexto.directorio_salida = self.selector_directorio_salida.filePath()
        self.contexto.crs = self.selector_sistema_referencia.crs()

        self.contexto.altura_minima_edificacion = (
            self.spin_altura_minima_edificacion.value()
        )
        self.contexto.resolucion_raster = self.spin_resolucion_raster.value()
        self.contexto.area_minima_deteccion = self.spin_area_minima_deteccion.value()
        self.contexto.distancia_tolerancia = self.spin_distancia_tolerancia.value()
        self.contexto.porcentaje_minimo_coincidencia = (
            self.spin_porcentaje_minimo_coincidencia.value()
        )
        self.contexto.filtrar_clase_terreno = self.chk_filtrar_clase_terreno.isChecked()
        self.contexto.filtrar_clase_edificacion = (
            self.chk_filtrar_clase_edificacion.isChecked()
        )
        self.contexto.usar_todas_clases_si_falla = (
            self.chk_usar_todas_clases_si_falla.isChecked()
        )

    def _validar_formulario(self):
        """
        Valida todas las entradas antes de iniciar el procesamiento.

        :return: True si el formulario es válido.
        """
        gestor = GestorEntradas

        validaciones = [
            gestor.validar_archivo_lidar(self.selector_archivo_lidar.filePath()),
            gestor.validar_capa_catastral(self.selector_capa_catastral.currentLayer()),
            gestor.validar_directorio_salida(
                self.selector_directorio_salida.filePath()
            ),
            gestor.validar_sistema_referencia(
                self.selector_sistema_referencia.crs()
            ),
            gestor.validar_parametros_numericos(
                self.spin_altura_minima_edificacion.value(),
                self.spin_resolucion_raster.value(),
                self.spin_area_minima_deteccion.value(),
                self.spin_distancia_tolerancia.value(),
                self.spin_porcentaje_minimo_coincidencia.value(),
            ),
        ]

        for es_valido, mensaje in validaciones:
            if not es_valido:
                registrar_mensaje(self.panel_mensajes, mensaje, es_error=True)
                mostrar_error("Validación de entradas", mensaje, self)
                return False

        dependencias_criticas = ("numpy", "laspy", "rasterio", "shapely", "geopandas")
        faltantes, _ = VerificadorDependencias.comprobar_dependencias(
            opcionales=("pdal", "geopandas")
        )
        faltantes_criticos = [d for d in faltantes if d in dependencias_criticas]
        if faltantes_criticos:
            texto = (
                "Faltan dependencias obligatorias: {}. "
                "Instálelas en el Python de QGIS antes de continuar."
            ).format(", ".join(faltantes_criticos))
            registrar_mensaje(self.panel_mensajes, texto, es_error=True)
            mostrar_error("Dependencias", texto, self)
            return False

        faltantes_opcionales = [d for d in faltantes if d not in dependencias_criticas]
        if faltantes_opcionales:
            texto = (
                "Dependencias opcionales no instaladas: {}. "
                "El análisis puede continuar; algunas funciones estarán limitadas."
            ).format(", ".join(faltantes_opcionales))
            registrar_mensaje(self.panel_mensajes, texto, es_error=False)

        return True

    def _al_ejecutar_procesamiento(self):
        """Inicia el pipeline en un hilo secundario."""
        if self.hilo_procesamiento is not None and self.hilo_procesamiento.isRunning():
            mostrar_advertencia(
                "Procesamiento en curso",
                "Ya hay un análisis en ejecución.",
                self,
            )
            return

        if not self._validar_formulario():
            return

        self._rellenar_contexto_desde_interfaz()
        self._habilitar_controles_procesamiento(en_ejecucion=True)
        self.barra_progreso.setValue(0)
        self.etiqueta_estado.setText("Iniciando procesamiento...")
        registrar_mensaje(self.panel_mensajes, "——— Nuevo análisis ———")

        self.hilo_procesamiento = HiloControladorProcesamiento(self.contexto)
        self.hilo_procesamiento.progreso_actualizado.connect(
            self._al_actualizar_progreso
        )
        self.hilo_procesamiento.mensaje_registrado.connect(self._al_registrar_mensaje_hilo)
        self.hilo_procesamiento.procesamiento_finalizado.connect(
            self._al_finalizar_procesamiento
        )
        self.hilo_procesamiento.start()

    def _al_cancelar_analisis(self):
        """Solicita la cancelación del análisis en curso."""
        self.contexto.cancelado = True
        registrar_mensaje(
            self.panel_mensajes, "Cancelación solicitada. Espere el cierre del hilo..."
        )
        self.etiqueta_estado.setText("Cancelando...")

    def _al_actualizar_progreso(self, porcentaje, texto_estado):
        """Actualiza barra y etiqueta de estado."""
        self.barra_progreso.setValue(porcentaje)
        self.etiqueta_estado.setText(texto_estado)

    def _al_registrar_mensaje_hilo(self, texto, es_error):
        """Recibe mensajes emitidos desde el hilo de procesamiento."""
        registrar_mensaje(self.panel_mensajes, texto, es_error=es_error)

    def _al_finalizar_procesamiento(self, exito, mensaje):
        """Restaura la interfaz tras finalizar o fallar el pipeline."""
        self._habilitar_controles_procesamiento(en_ejecucion=False)
        self.btn_cancelar_analisis.setEnabled(False)

        if exito:
            self.contexto.completado = True
            try:
                self.gestor_capas.registrar_capas_en_proyecto()
                registrar_mensaje(
                    self.panel_mensajes, "Capas de resultados añadidas al proyecto QGIS."
                )
                exito_simbologia, mensaje_simbologia = self.simbologia.aplicar_simbologia(
                    self.contexto
                )
                registrar_mensaje(
                    self.panel_mensajes, mensaje_simbologia, es_error=not exito_simbologia
                )
            except Exception as error:
                registrar_mensaje(
                    self.panel_mensajes,
                    "No se pudieron cargar todas las capas: {}".format(error),
                    es_error=True,
                )
            self._habilitar_controles_resultados(hay_resultados=True)
            self._sincronizar_checkboxes_visibilidad()
            self._actualizar_arbol_capas()
            if self.contexto.ruta_informe_csv:
                registrar_mensaje(
                    self.panel_mensajes,
                    "Informe CSV: {}".format(self.contexto.ruta_informe_csv),
                )
            self.pestanero_principal.setCurrentWidget(self.pestana_resultados)
            mostrar_informacion("Procesamiento", mensaje, self)
        else:
            mostrar_error("Procesamiento", mensaje, self)

        self.etiqueta_estado.setText("Listo." if exito else "Finalizado con errores.")
        registrar_mensaje(self.panel_mensajes, mensaje, es_error=not exito)

    def _al_limpiar_mensajes(self):
        """Vacía el panel de registro."""
        self.panel_mensajes.clear()

    def _al_cargar_catastro_desde_archivo(self):
        """Carga un archivo vectorial catastral y lo selecciona en el combo."""
        ruta, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar cartografía catastral",
            "",
            "Vectoriales (*.shp *.gpkg *.geojson);;Todos (*.*)",
        )
        if not ruta:
            return

        es_valido, mensaje = GestorEntradas.validar_archivo_catastro_externo(ruta)
        if not es_valido:
            mostrar_error("Carga catastral", mensaje, self)
            return

        nombre_capa = os.path.splitext(os.path.basename(ruta))[0]
        capa = QgsVectorLayer(ruta, nombre_capa, "ogr")
        if not capa.isValid():
            mostrar_error(
                "Carga catastral",
                "No se pudo cargar la capa: {}".format(ruta),
                self,
            )
            return

        QgsProject.instance().addMapLayer(capa)
        self.selector_capa_catastral.setLayer(capa)
        registrar_mensaje(
            self.panel_mensajes, "Capa catastral cargada: {}".format(nombre_capa)
        )

    def _al_cambiar_visibilidad(self, clave_capa, visible):
        """Cambia la visibilidad de una capa de resultado en el proyecto."""
        capas = self.gestor_capas.obtener_capas_del_contexto()
        capa = capas.get(clave_capa)
        self.gestor_capas.establecer_visibilidad(capa, visible)

    def _sincronizar_checkboxes_visibilidad(self):
        """Marca los checkboxes de capas que ya fueron generadas."""
        pares = (
            (self.chk_mostrar_dsm, self.contexto.capa_dsm),
            (self.chk_mostrar_dtm, self.contexto.capa_dtm),
            (self.chk_mostrar_ndsm, self.contexto.capa_ndsm),
            (self.chk_mostrar_huellas_detectadas, self.contexto.capa_huellas),
            (self.chk_mostrar_coincidentes, self.contexto.capa_coincidentes),
            (self.chk_mostrar_discrepancias, self.contexto.capa_discrepancias),
            (self.chk_mostrar_nuevas_construcciones, self.contexto.capa_nuevas),
            (self.chk_mostrar_posibles_demoliciones, self.contexto.capa_demoliciones),
        )
        for checkbox, capa in pares:
            if capa is not None:
                checkbox.setChecked(True)

    def _actualizar_arbol_capas(self):
        """Rellena el árbol con el estado de las capas en el contexto."""
        self.arbol_capas_resultado.clear()
        elementos = [
            ("DSM", "Ráster", self.contexto.capa_dsm),
            ("DTM", "Ráster", self.contexto.capa_dtm),
            ("nDSM", "Ráster", self.contexto.capa_ndsm),
            ("Huellas LiDAR", "Vectorial", self.contexto.capa_huellas),
            ("Coincidentes", "Vectorial", self.contexto.capa_coincidentes),
            ("Discrepancias", "Vectorial", self.contexto.capa_discrepancias),
            ("Nuevas construcciones", "Vectorial", self.contexto.capa_nuevas),
            ("Posibles demoliciones", "Vectorial", self.contexto.capa_demoliciones),
        ]
        for nombre, tipo, capa in elementos:
            item = QtWidgets.QTreeWidgetItem([nombre, tipo])
            if capa is not None:
                item.setToolTip(0, "Capa cargada en el proyecto")
                if capa.featureCount() >= 0:
                    item.setText(1, "{} ({} ent.)".format(tipo, capa.featureCount()))
            else:
                item.setForeground(0, Qt.gray)
                item.setToolTip(0, "No generada")
            self.arbol_capas_resultado.addTopLevelItem(item)

    def _al_aplicar_simbologia(self):
        """Aplica estilos temáticos a las capas de resultado."""
        exito, mensaje = self.simbologia.aplicar_simbologia(self.contexto)
        registrar_mensaje(self.panel_mensajes, mensaje, es_error=not exito)
        if exito:
            mostrar_informacion("Simbología", mensaje, self)
        else:
            mostrar_advertencia("Simbología", mensaje, self)

    def _al_zoom_resultados(self):
        """Ajusta la extensión del mapa a las capas con geometría válida."""
        extension = None
        for capa in self.gestor_capas.obtener_capas_del_contexto().values():
            if capa is not None and capa.isValid():
                ext_capa = capa.extent()
                if extension is None:
                    extension = ext_capa
                else:
                    extension.combineExtentWith(ext_capa)
        if extension is not None and not extension.isEmpty():
            if iface_qgis is not None:
                iface_qgis.mapCanvas().setExtent(extension)
                iface_qgis.mapCanvas().refresh()
            registrar_mensaje(self.panel_mensajes, "Zoom aplicado a resultados.")
        else:
            mostrar_advertencia(
                "Zoom",
                "No hay capas de resultados cargadas en el mapa todavía.",
                self,
            )

    def _al_exportar_resultados(self):
        """Lanza la exportación según las opciones de la pestaña Exportación."""
        opciones = {
            "exportar_rasteres": self.chk_exportar_rasteres.isChecked(),
            "exportar_vectores": self.chk_exportar_vectores.isChecked(),
            "formato_vectorial": self.combo_formato_vectorial.currentText(),
            "exportar_csv": self.chk_exportar_csv.isChecked(),
            "exportar_proyecto": self.chk_exportar_proyecto_qgis.isChecked(),
        }
        exportador = ExportadorResultados(self.contexto)
        exito, mensaje, ruta = exportador.exportar(opciones)
        registrar_mensaje(self.panel_mensajes, mensaje, es_error=not exito)
        if ruta:
            self.contexto.ultima_ruta_exportacion = ruta
            self.etiqueta_ruta_ultima_exportacion.setText(
                "Última exportación: {}".format(ruta)
            )
        if exito:
            mostrar_informacion("Exportación", mensaje, self)
        else:
            mostrar_advertencia("Exportación", mensaje, self)

    def _al_mostrar_ayuda(self):
        """Muestra información básica de uso del complemento."""
        texto_ayuda = (
            "Validador LiDAR de huella urbana\n\n"
            "1. Pestaña Entradas: seleccione LiDAR, capa catastral, salida y CRS.\n"
            "2. Parámetros: configure umbrales de detección y validación.\n"
            "3. Procesamiento: ejecute el análisis y revise el registro.\n"
            "4. Resultados: controle visibilidad y simbología.\n"
            "5. Exportación: guarde productos en disco.\n\n"
            "Versión 1.0: LiDAR, validación catastral, simbología "
            "y exportación desde la pestaña Exportación."
        )
        mostrar_informacion("Ayuda", texto_ayuda, self)
