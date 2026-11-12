"""Ventana principal de Hexabloq: coordina documento, historial, selección y paneles."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QSettings, QSize, Qt
from PySide6.QtGui import QAction, QActionGroup, QGuiApplication, QKeySequence
from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QSplitter,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .. import operaciones as op
from ..archivo import ErrorDeArchivo, abrir, guardar
from ..chunks import limites_chunk
from ..construccion import Construccion, construir, describir_posicion, instrucciones, instrucciones_por_chunk
from ..documento import COMPUESTA, FUSION_SILUETA, Documento, Objeto, limites_de
from ..geometria import ErrorDeTamano
from ..guia import formato_num
from ..historial import Historial
from . import dialogos, recursos, tema
from .barra import BarraAdaptable
from .exportar import DialogoInstrucciones, DialogoPNG, renderizar_png
from .lienzo import ANADIR, MANO, REEMPLAZAR, SELECCIONAR, SUMAR, Lienzo, posicionar_centrado
from .panel_construccion import SELECCION, PanelConstruccion
from .panel_objetos import PanelObjetos
from .panel_propiedades import PanelPropiedades

ANCHO_PANEL = 320
ANCHO_DERECHO = 340
TAMANO_MINIMO_VENTANA = QSize(1000, 640)
FILTRO_DISENO = f"Diseño de {tema.NOMBRE_APP} (*.json)"
MENSAJE_VACIO = ("Diseño vacío. Elige una figura en el panel izquierdo y pulsa «Añadir figura», "
                 "o usa la herramienta Añadir (A) y haz clic en la cuadrícula.")


class VentanaPrincipal(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.ajustes = QSettings()
        self.setMinimumSize(TAMANO_MINIMO_VENTANA)
        self.historial = Historial(Documento())
        self._guardado = Documento()
        self._ruta: Path | None = None
        self.seleccion: tuple[str, ...] = ()
        self.construccion = Construccion({})

        self.lienzo = Lienzo()
        self.lienzo.mensaje_vacio = MENSAJE_VACIO
        self.propiedades = PanelPropiedades()
        self.panel_objetos = PanelObjetos()
        self.panel_construccion = PanelConstruccion()

        self._crear_acciones()
        self.setMenuWidget(self._crear_barra_superior())
        self.setCentralWidget(self._crear_cuerpo())
        self._crear_estado()
        self._conectar()
        self._cargar_ajustes()
        self._empezar(self._documento_inicial(), None)

    # ================================================================== acciones
    def _accion(self, texto, icono=None, atajos=(), consejo="", slot=None, marcable=False, destino=None):
        accion = QAction(texto, destino or self)
        if icono:
            accion.setIcon(recursos.icono(icono))
        if atajos:
            accion.setShortcuts([QKeySequence(a) for a in atajos])
        teclas = " · ".join(atajos)
        accion.setToolTip(f"{consejo or texto} ({teclas})" if teclas else (consejo or texto))
        accion.setCheckable(marcable)
        if slot:
            (accion.toggled if marcable else accion.triggered).connect(slot)
        (destino or self).addAction(accion)
        return accion

    def _crear_acciones(self) -> None:
        a = self._accion
        self.acc_nuevo = a("Nuevo", "nuevo", ("Ctrl+N",), "Empezar un diseño nuevo", self.nuevo)
        self.acc_abrir = a("Abrir", "abrir", ("Ctrl+O",), "Abrir un diseño guardado", self.abrir_diseno)
        self.acc_guardar = a("Guardar", "guardar", ("Ctrl+S",), "Guardar el diseño en JSON", self.guardar)
        self.acc_guardar_como = a("Guardar como…", "guardar", ("Ctrl+Shift+S",), "Guardar con otro nombre",
                                  self.guardar_como)
        self.acc_png = a("Exportar PNG", "exportar", ("Ctrl+E",), "Exportar el diseño o la selección como PNG",
                         self.exportar_png)
        self.acc_texto = a("Exportar instrucciones…", "texto", ("Ctrl+Shift+E",),
                           "Guardar las instrucciones en un archivo de texto", self.exportar_instrucciones)
        self.acc_copiar = a("Copiar instrucciones", "copiar", ("Ctrl+Shift+C",), "Copiar la guía por filas",
                            lambda: self.copiar_instrucciones("completa"))
        self.acc_salir = a("Salir", None, ("Ctrl+Q",), "Cerrar la aplicación", self.close)
        self.acc_deshacer = a("Deshacer", "deshacer", ("Ctrl+Z",), "Deshacer", self.deshacer)
        self.acc_rehacer = a("Rehacer", "rehacer", ("Ctrl+Y", "Ctrl+Shift+Z"), "Rehacer", self.rehacer)
        self.acc_todo = a("Seleccionar todo", None, ("Ctrl+A",), "", self.seleccionar_todo)
        self.acc_anadir = a("Añadir figura", "anadir", ("Insert",), "Añadir la figura de la plantilla en el centro "
                            "de la vista", lambda: self._ejecutar("anadir"))
        self.acc_duplicar = a("Duplicar", "duplicar", ("Ctrl+D",), "", lambda: self._ejecutar("duplicar"))
        self.acc_eliminar = a("Eliminar", "eliminar", ("Del",), "", lambda: self._ejecutar("eliminar"))
        self.acc_agrupar = a("Agrupar", "agrupar", ("Ctrl+G",), "", lambda: self._ejecutar("agrupar"))
        self.acc_desagrupar = a("Desagrupar", "desagrupar", ("Ctrl+Shift+G",), "",
                                lambda: self._ejecutar("desagrupar"))
        self.acc_fusionar = a("Fusionar…", "fusionar", ("Ctrl+M",), "", lambda: self._ejecutar("fusionar"))
        self.acc_separar = a("Separar figura compuesta", "separar", ("Ctrl+Shift+M",), "",
                             lambda: self._ejecutar("separar"))
        self.acc_subir = a("Subir", "subir", ("Ctrl+]",), "", lambda: self._ejecutar("subir"))
        self.acc_bajar = a("Bajar", "bajar", ("Ctrl+[",), "", lambda: self._ejecutar("bajar"))
        self.acc_frente = a("Traer al frente", "frente", ("Ctrl+Shift+]",), "", lambda: self._ejecutar("frente"))
        self.acc_fondo = a("Enviar al fondo", "fondo", ("Ctrl+Shift+[",), "", lambda: self._ejecutar("fondo"))
        self.acc_acercar = a("Acercar", "zoom_mas", ("Ctrl++", "Ctrl+="), "", lambda: self.lienzo.zoom(1.25))
        self.acc_alejar = a("Alejar", "zoom_menos", ("Ctrl+-",), "", lambda: self.lienzo.zoom(1 / 1.25))
        self.acc_ajustar = a("Ajustar", "ajustar", ("Ctrl+0",), "Encuadrar todo el diseño (F)", self.ajustar_vista)
        self.acc_centrar = a("Centrar", "centrar", (), "Centrar en la selección o en el origen (C)",
                             self.centrar_vista)
        self.acc_panel = a("Panel", "panel_guia", ("Ctrl+B",), "Mostrar u ocultar el panel de objetos y "
                           "construcción", self._mostrar_panel_derecho, marcable=True)
        self.acc_ayuda = a("Ayuda", "ayuda", ("F1",), "", lambda: dialogos.mostrar_ayuda(self))
        self.acc_atajos = a("Atajos de teclado", "teclado", ("Ctrl+/",), "", lambda: dialogos.mostrar_atajos(self))
        self.acc_acerca = a(f"Acerca de {tema.NOMBRE_APP}", "info", (), "", lambda: dialogos.mostrar_acerca_de(self))
        a("Ir al tamaño", None, ("Ctrl+L",), "", self.propiedades.enfocar_tamano)
        a("Alternar contorno y relleno", None, ("Ctrl+T",), "", self.propiedades.alternar_modo)
        a("Fila anterior", None, ("Alt+Up",), "", lambda: self.panel_construccion.mover_fila(-1))
        a("Fila siguiente", None, ("Alt+Down",), "", lambda: self.panel_construccion.mover_fila(1))
        for i, tipo in enumerate(("hexagono", "circulo", "triangulo"), 1):
            a(f"Figura {i}", None, (f"Ctrl+{i}",), "", lambda _=False, t=tipo: self.propiedades.seleccionar_tipo(t))

    def _acciones_lienzo(self, zona: QWidget) -> None:
        def local(texto, icono, tecla, consejo, slot=None, marcable=False):
            accion = self._accion(texto, icono, (tecla,) if tecla else (), consejo, slot, marcable, destino=zona)
            accion.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            return accion

        def opcion(nombre):
            return lambda valor: self.lienzo.set_opcion(nombre, valor)

        self.grupo_herramientas = QActionGroup(self)
        self.herramientas = {}
        for clave, texto, icono, tecla, consejo in (
            (SELECCIONAR, "Seleccionar", "seleccionar", "V", "Seleccionar y mover figuras"),
            (MANO, "Mover vista", "mano", "H", "Desplazar la vista sin tocar las figuras"),
            (ANADIR, "Añadir", "anadir", "A", "Clic en la cuadrícula para añadir la figura de la plantilla"),
        ):
            accion = local(texto, icono, tecla, consejo, marcable=True)
            accion.triggered.connect(lambda _=False, c=clave: self.set_herramienta(c))
            self.grupo_herramientas.addAction(accion)
            self.herramientas[clave] = accion
        self.herramientas[SELECCIONAR].setChecked(True)
        self.acc_cuadricula = local("Bloques", "cuadricula", "G", "Cuadrícula de bloques", opcion("cuadricula"), True)
        self.acc_chunks = local("Chunks", "chunks", "K", "Límites de chunks de 16 × 16", opcion("chunks"), True)
        self.acc_coordenadas = local("Coordenadas", "coordenadas", "N", "Coordenadas de bloques y chunks",
                                     opcion("coordenadas"), True)
        self.acc_ejes = local("Ejes", "ejes", "X", "Ejes del mundo y origen (0, 0)", opcion("ejes"), True)
        self.acc_ajuste_chunk = local("Ajustar a chunks", "iman", "S", "Al arrastrar, la esquina de la selección "
                                      "se ajusta al chunk más cercano", self._cambiar_ajuste_chunk, True)
        self.acc_fondo_claro = local("Fondo claro", "lienzo", "B", "Fondo de la cuadrícula claro u oscuro",
                                     self._cambiar_fondo, True)
        for accion in (self.acc_cuadricula, self.acc_chunks, self.acc_coordenadas, self.acc_ejes):
            accion.setChecked(True)
        local("Ajustar al diseño", None, "F", "", self.ajustar_vista)
        local("Centrar", None, "C", "", self.centrar_vista)
        local("Quitar selección", None, "Esc", "", self._escape)

    # ================================================================== interfaz
    def _crear_barra_superior(self) -> QWidget:
        barra = BarraAdaptable("barraSuperior")
        barra.layout().setContentsMargins(14, 6, 10, 6)
        logo = QLabel()
        logo.setPixmap(recursos.logo(26))
        logo.setAccessibleName(tema.NOMBRE_APP)
        nombre = QLabel(tema.NOMBRE_APP)
        nombre.setObjectName("nombreApp")
        self.lbl_documento = QLabel()
        self.lbl_documento.setObjectName("nombreArchivo")
        barra.widget(logo)
        barra.espacio(6)
        barra.widget(nombre)
        barra.espacio(10)
        barra.widget(self.lbl_documento)
        barra.separador()
        for accion in (self.acc_nuevo, self.acc_abrir, self.acc_guardar):
            barra.boton(accion, nombre="accionBarra")
        barra.widget(self._boton_exportar())
        barra.separador()
        barra.boton(self.acc_deshacer, texto_visible=False, nombre="accionBarra")
        barra.boton(self.acc_rehacer, texto_visible=False, nombre="accionBarra")
        barra.cerrar()
        boton_panel = QToolButton()
        boton_panel.setObjectName("herramienta")
        boton_panel.setDefaultAction(self.acc_panel)
        boton_panel.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        boton_panel.setIconSize(QSize(18, 18))
        barra.al_final(boton_panel)
        barra.al_final(self._boton_ayuda())
        return barra

    def _boton_exportar(self) -> QToolButton:
        menu = QMenu(self)
        menu.addActions([self.acc_png, self.acc_texto, self.acc_copiar])
        boton = QToolButton()
        boton.setObjectName("accionBarra")
        boton.setDefaultAction(self.acc_png)
        boton.setText("Exportar")
        boton.setIconSize(QSize(18, 18))
        boton.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        boton.setMenu(menu)
        boton.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        return boton

    def _boton_ayuda(self) -> QToolButton:
        menu = QMenu(self)
        menu.addActions([self.acc_ayuda, self.acc_atajos])
        menu.addSeparator()
        menu.addAction(self.acc_guardar_como)
        menu.addSeparator()
        menu.addAction(self.acc_acerca)
        boton = QToolButton()
        boton.setObjectName("accionBarra")
        boton.setIcon(recursos.icono("ayuda"))
        boton.setIconSize(QSize(18, 18))
        boton.setToolTip("Ayuda, atajos e información")
        boton.setAccessibleName("Ayuda")
        boton.setMenu(menu)
        boton.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        return boton

    def _crear_cuerpo(self) -> QSplitter:
        self.pestanas = QTabWidget()
        self.pestanas.addTab(self.panel_objetos, recursos.icono("grupo"), "Objetos")
        self.pestanas.addTab(self.panel_construccion, recursos.icono("texto"), "Construcción")
        self.pestanas.setMinimumWidth(300)
        self.divisor = QSplitter(Qt.Orientation.Horizontal)
        self.divisor.addWidget(self.propiedades)
        self.divisor.addWidget(self._crear_zona_lienzo())
        self.divisor.addWidget(self.pestanas)
        self.divisor.setStretchFactor(1, 1)
        self.divisor.setCollapsible(0, False)
        self.divisor.setCollapsible(1, False)
        self.divisor.setSizes([ANCHO_PANEL, 800, ANCHO_DERECHO])
        return self.divisor

    def _crear_zona_lienzo(self) -> QWidget:
        zona = QWidget()
        zona.setObjectName("zonaLienzo")
        zona.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._acciones_lienzo(zona)
        lay = QVBoxLayout(zona)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(8)
        barra = BarraAdaptable("barraLienzo")
        for accion in self.herramientas.values():
            barra.boton(accion)
        barra.separador()
        barra.boton(self.acc_alejar, texto_visible=False)
        barra.boton(self.acc_acercar, texto_visible=False)
        barra.boton(self.acc_ajustar, texto_visible=False)
        barra.boton(self.acc_centrar, texto_visible=False)
        barra.separador()
        for accion in (self.acc_cuadricula, self.acc_chunks, self.acc_coordenadas, self.acc_ejes):
            barra.boton(accion)
        barra.separador()
        barra.boton(self.acc_ajuste_chunk)
        barra.boton(self.acc_fondo_claro, texto_visible=False)
        barra.cerrar()
        lay.addWidget(barra)
        lay.addWidget(self.lienzo, 1)
        return zona

    def _crear_estado(self) -> None:
        estado = self.statusBar()
        self.lbl_cursor = QLabel()
        self.lbl_cursor.setMinimumWidth(80)
        self.lbl_resumen = QLabel()
        self.lbl_zoom = QLabel()
        estado.addWidget(self.lbl_cursor, 1)
        estado.addPermanentWidget(self.lbl_resumen)
        estado.addPermanentWidget(self.lbl_zoom)
        self._mostrar_cursor(None)

    def _conectar(self) -> None:
        lz = self.lienzo
        lz.celdaBajoCursor.connect(self._mostrar_cursor)
        lz.zoomCambiado.connect(lambda z: self.lbl_zoom.setText(f"Zoom: {formato_num(z, 1)} px/bloque"))
        lz.seleccionPedida.connect(self._pedir_seleccion)
        lz.arrastreMovido.connect(self._arrastre_previo)
        lz.arrastreTerminado.connect(self._arrastre_final)
        lz.colocarPedido.connect(self._colocar)
        lz.moverPedido.connect(self.mover_seleccion)
        lz.menuPedido.connect(self._menu_contextual)
        self.propiedades.plantillaCambiada.connect(self._al_cambiar_plantilla)
        self.propiedades.cambio.connect(self._editar_seleccion)
        self.propiedades.posicionPedida.connect(self._colocar_seleccion)
        self.propiedades.accion.connect(self._ejecutar)
        self.panel_objetos.seleccionCambiada.connect(lambda ids: self.set_seleccion(ids))
        self.panel_objetos.alternarVisible.connect(lambda ids: self._alternar(ids, "visible"))
        self.panel_objetos.alternarBloqueo.connect(lambda ids: self._alternar(ids, "bloqueado"))
        self.panel_objetos.renombrar.connect(self._renombrar)
        self.panel_objetos.accion.connect(self._ejecutar)
        self.panel_construccion.ambitoCambiado.connect(lambda _a: self._refrescar())
        self.panel_construccion.chunkElegido.connect(self._mostrar_chunk)
        self.panel_construccion.filaElegida.connect(self.lienzo.set_fila)
        self.panel_construccion.copiarPedido.connect(self.copiar_instrucciones)
        self.panel_construccion.exportarPedido.connect(self.exportar_instrucciones)
        self.divisor.splitterMoved.connect(self._al_mover_divisor)

    # ================================================================== estado
    @property
    def documento(self) -> Documento:
        return self.historial.actual

    def _documento_inicial(self) -> Documento:
        doc, _ = op.agregar(Documento(), posicionar_centrado(self.propiedades.plantilla(), 0, 0))
        return doc

    def _empezar(self, doc: Documento, ruta: Path | None) -> None:
        self.historial.reiniciar(doc)
        self._guardado = doc
        self._ruta = ruta
        self.seleccion = ()
        self.lienzo.set_fila(None)
        self._refrescar()
        self.lienzo.ajustar()

    def _refrescar(self, previa: Documento | None = None) -> None:
        """Actualiza la vista. ``previa`` es el documento provisional de un arrastre en curso:
        solo se muestra en el lienzo y nunca sustituye al documento real."""
        doc = previa if previa is not None else self.documento
        self.seleccion = tuple(i for i in self.seleccion if doc.buscar(i))
        self.construccion = construir(doc.objetos)
        self.lienzo.plantilla = self.propiedades.plantilla()
        self.lienzo.set_estado(self.construccion, doc, self.seleccion)
        self._actualizar_resumen(doc)
        if previa is not None:
            return
        self.panel_objetos.mostrar(doc, self.seleccion)
        self.propiedades.mostrar(doc, self.seleccion)
        self.panel_construccion.mostrar(self._construccion_del_ambito(), bool(self.seleccion))
        self._actualizar_acciones()
        self._actualizar_titulo()

    def construccion_seleccion(self) -> Construccion | None:
        if not self.seleccion:
            return None
        return construir(self.documento.seleccionados(self.seleccion))

    def _construccion_del_ambito(self) -> Construccion:
        if self.panel_construccion.ambito() == SELECCION and self.seleccion:
            return self.construccion_seleccion()
        return self.construccion

    def _actualizar_resumen(self, doc: Documento) -> None:
        c = self.construccion
        partes = [f"{len(doc.objetos)} objetos", f"{c.total} bloques únicos", f"{len(c.por_chunk)} chunks"]
        if self.seleccion:
            partes.insert(0, f"{len(self.seleccion)} seleccionados")
        self.lbl_resumen.setText(" · ".join(partes))

    def _actualizar_acciones(self) -> None:
        sel = self.documento.seleccionados(self.seleccion)
        hay, varios = bool(sel), len(sel) >= 2
        estados = {
            self.acc_duplicar: hay, self.acc_eliminar: hay, self.acc_subir: hay, self.acc_bajar: hay,
            self.acc_frente: hay, self.acc_fondo: hay, self.acc_agrupar: varios, self.acc_fusionar: varios,
            self.acc_desagrupar: any(o.grupo for o in sel),
            self.acc_separar: len(sel) == 1 and sel[0].es_compuesta,
            self.acc_png: not self.construccion.vacia, self.acc_texto: not self.construccion.vacia,
            self.acc_copiar: not self.construccion.vacia,
            self.acc_deshacer: self.historial.puede_deshacer(), self.acc_rehacer: self.historial.puede_rehacer(),
        }
        for accion, activa in estados.items():
            accion.setEnabled(activa)
        self.acc_deshacer.setToolTip(f"Deshacer {self.historial.descripcion_deshacer().lower()} (Ctrl+Z)".strip())
        self.acc_rehacer.setToolTip(f"Rehacer {self.historial.descripcion_rehacer().lower()} (Ctrl+Y)".strip())

    def hay_cambios(self) -> bool:
        return self.documento != self._guardado

    def _nombre_documento(self) -> str:
        return self._ruta.name if self._ruta else "Sin título"

    def _actualizar_titulo(self) -> None:
        cambios = self.hay_cambios()
        self.setWindowTitle(f"{self._nombre_documento()}[*] — {tema.NOMBRE_APP}")
        self.setWindowModified(cambios)
        self.lbl_documento.setText(self._nombre_documento() + (" · sin guardar" if cambios else ""))

    # ================================================================== edición
    def _aplicar(self, doc: Documento, descripcion: str, seleccion=None, clave: str | None = None) -> None:
        self.historial.registrar(doc, descripcion, clave)
        if seleccion is not None:
            self.seleccion = tuple(seleccion)
        self._refrescar()

    def _avisar(self, mensaje: str) -> None:
        self.statusBar().showMessage(mensaje, 6000)
        QMessageBox.information(self, "No se puede completar la acción", mensaje)

    def set_seleccion(self, ids) -> None:
        self.historial.cortar_fusion()
        self.seleccion = tuple(ids)
        self._refrescar()

    def _pedir_seleccion(self, ids: tuple, modo: str) -> None:
        actual = list(self.seleccion)
        if modo == REEMPLAZAR:
            nueva = list(ids)
        elif modo == SUMAR:
            nueva = actual + [i for i in ids if i not in actual]
        elif all(i in actual for i in ids):
            nueva = [i for i in actual if i not in ids]
        else:
            nueva = actual + [i for i in ids if i not in actual]
        self.set_seleccion(nueva)

    def seleccionar_todo(self) -> None:
        self.set_seleccion(o.id for o in self.documento.objetos)

    def _escape(self) -> None:
        if self.lienzo.herramienta != SELECCIONAR:
            self.set_herramienta(SELECCIONAR)
        else:
            self.set_seleccion(())

    def set_herramienta(self, herramienta: str) -> None:
        self.herramientas[herramienta].setChecked(True)
        self.lienzo.set_herramienta(herramienta)

    def _arrastre_previo(self, dx: int, dz: int) -> None:
        self._refrescar(previa=op.mover(self.documento, self.seleccion, dx, dz))

    def _arrastre_final(self, dx: int, dz: int) -> None:
        self._mover(dx, dz, "Mover")

    def mover_seleccion(self, dx: int, dz: int) -> None:
        if self.seleccion:
            self._mover(dx, dz, "Mover", clave=f"teclado:{','.join(self.seleccion)}")

    def _mover(self, dx: int, dz: int, descripcion: str, clave: str | None = None) -> None:
        doc = op.mover(self.documento, self.seleccion, dx, dz)
        if doc == self.documento:
            self._refrescar()
            if any(o.bloqueado for o in self.documento.seleccionados(self.seleccion)):
                self.statusBar().showMessage("Los objetos bloqueados no se mueven.", 4000)
            return
        self._aplicar(doc, descripcion, clave=clave)

    def _colocar(self, x: int, z: int) -> None:
        objeto = posicionar_centrado(self.propiedades.plantilla(), x, z)
        doc, nuevo = op.agregar(self.documento, objeto)
        self._aplicar(doc, "Añadir figura", seleccion=(nuevo,))

    def _colocar_seleccion(self, x: int, z: int) -> None:
        self._aplicar(op.colocar(self.documento, self.seleccion, x, z), "Mover",
                      clave=f"posicion:{','.join(self.seleccion)}")

    def _al_cambiar_plantilla(self) -> None:
        self.lienzo.plantilla = self.propiedades.plantilla()
        self.lienzo.update()

    def _editar_seleccion(self, cambios: dict, clave: str) -> None:
        doc = self.documento
        objetivos = self.documento.seleccionados(self.seleccion)
        try:
            for objeto in objetivos:
                aplicables = _cambios_aplicables(objeto, cambios, len(objetivos) > 1)
                if aplicables and (not objeto.bloqueado or set(aplicables) <= op.CAMPOS_LIBRES_SI_BLOQUEADO):
                    doc = op.editar(doc, objeto.id, **aplicables)
        except (op.ErrorDeOperacion, ErrorDeTamano) as e:
            self._refrescar()
            self._avisar(str(e))
            return
        self._aplicar(doc, "Editar propiedades", clave=f"editar:{','.join(self.seleccion)}:{clave}")

    def _alternar(self, ids, campo: str) -> None:
        objetos = self.documento.seleccionados(ids)
        if not objetos:
            return
        valor = not all(getattr(o, campo) for o in objetos)
        doc = self.documento
        for objeto in objetos:
            doc = op.editar(doc, objeto.id, **{campo: valor})
        nombre = {"visible": "Mostrar" if valor else "Ocultar", "bloqueado": "Bloquear" if valor else "Desbloquear"}
        self._aplicar(doc, nombre[campo])

    def _renombrar(self, referencia: str, nombre: str) -> None:
        clase, valor = referencia.split(":", 1)
        if clase == "grupo":
            grupos = tuple(replace(g, nombre=nombre) if g.id == valor else g for g in self.documento.grupos)
            self._aplicar(replace(self.documento, grupos=grupos), "Renombrar grupo")
        else:
            self._aplicar(op.editar(self.documento, valor, nombre=nombre), "Renombrar")

    def _ejecutar(self, accion: str) -> None:
        try:
            self._ejecutar_sin_control(accion)
        except op.ErrorDeOperacion as e:
            self._avisar(str(e))

    def _ejecutar_sin_control(self, accion: str) -> None:
        doc, sel = self.documento, self.seleccion
        if accion == "anadir":
            self._colocar(*self.lienzo.centro_visible())
        elif accion == "duplicar" and sel:
            nuevo, ids = op.duplicar(doc, sel)
            self._aplicar(nuevo, "Duplicar", seleccion=ids)
        elif accion == "eliminar" and sel:
            nuevo = op.eliminar(doc, sel)
            if nuevo == doc:
                raise op.ErrorDeOperacion("Los objetos bloqueados no se pueden eliminar: desbloquéalos primero.")
            self._aplicar(nuevo, "Eliminar")
        elif accion == "agrupar":
            nuevo, _ = op.agrupar(doc, sel)
            self._aplicar(nuevo, "Agrupar")
        elif accion == "desagrupar":
            self._aplicar(op.desagrupar(doc, sel), "Desagrupar")
        elif accion == "fusionar":
            self._fusionar()
        elif accion == "separar":
            if len(sel) != 1:
                raise op.ErrorDeOperacion("Selecciona una sola figura compuesta para separarla.")
            nuevo, ids = op.separar(doc, sel[0])
            self._aplicar(nuevo, "Separar figura compuesta", seleccion=ids)
        elif accion in ("subir", "bajar", "frente", "fondo") and sel:
            self._aplicar(op.reordenar(doc, sel, accion), "Cambiar orden")
        elif accion.startswith("alinear:"):
            self._aplicar(op.alinear(doc, sel, accion.split(":", 1)[1]), "Alinear")

    def _fusionar(self) -> None:
        if len(self.seleccion) < 2:
            raise op.ErrorDeOperacion("Selecciona al menos dos figuras para fusionarlas.")
        dialogo = dialogos.DialogoFusion(self, len(self.seleccion), op.nombre_nuevo(self.documento, COMPUESTA))
        if dialogo.exec() != dialogos.DialogoFusion.DialogCode.Accepted:
            return
        fusion, modo, nombre = dialogo.resultado()
        self.fusionar(fusion, modo, nombre)

    def fusionar(self, fusion: str = FUSION_SILUETA, modo: str = "contorno", nombre: str = "") -> None:
        nuevo, id_compuesta = op.fusionar(self.documento, self.seleccion, fusion, modo, nombre)
        self._aplicar(nuevo, "Fusionar", seleccion=(id_compuesta,))

    def deshacer(self) -> None:
        self.historial.deshacer()
        self._refrescar()

    def rehacer(self) -> None:
        self.historial.rehacer()
        self._refrescar()

    def _menu_contextual(self, posicion) -> None:
        menu = QMenu(self)
        menu.addActions([self.acc_duplicar, self.acc_eliminar])
        menu.addSeparator()
        menu.addActions([self.acc_agrupar, self.acc_desagrupar, self.acc_fusionar, self.acc_separar])
        menu.addSeparator()
        menu.addActions([self.acc_frente, self.acc_subir, self.acc_bajar, self.acc_fondo])
        menu.addSeparator()
        menu.addActions([self.acc_anadir, self.acc_todo])
        menu.exec(posicion)

    # ================================================================== vista
    def ajustar_vista(self) -> None:
        self.lienzo.ajustar(self.construccion.limites)

    def centrar_vista(self) -> None:
        caja = limites_de(self.documento.seleccionados(self.seleccion))
        if caja is None:
            self.lienzo.centrar_en(0, 0)
        else:
            self.lienzo.centrar_en((caja[0] + caja[2] + 1) / 2, (caja[1] + caja[3] + 1) / 2)

    def _mostrar_chunk(self, chunk) -> None:
        if chunk is not None:
            self.lienzo.ajustar(limites_chunk(*chunk))

    def _mostrar_cursor(self, celda) -> None:
        if celda is None:
            self.lbl_cursor.setText("Pasa el ratón por la cuadrícula para ver las coordenadas.")
            return
        texto = describir_posicion(*celda)
        objeto = self.lienzo.objeto_en(*celda)
        color = self.construccion.color_en(*celda)
        if color:
            texto += " · bloque"
        if objeto is not None:
            texto += f" · {objeto.nombre}"
        self.lbl_cursor.setText(texto)

    def _mostrar_panel_derecho(self, visible: bool) -> None:
        self.pestanas.setVisible(visible)
        tamanos = self.divisor.sizes()
        if visible and tamanos[2] == 0:
            self.divisor.setSizes([tamanos[0], max(200, tamanos[1] - ANCHO_DERECHO), ANCHO_DERECHO])

    def _al_mover_divisor(self, _pos: int, _indice: int) -> None:
        visible = self.divisor.sizes()[2] > 0
        if visible != self.acc_panel.isChecked():
            self.acc_panel.blockSignals(True)
            self.acc_panel.setChecked(visible)
            self.acc_panel.blockSignals(False)

    def _cambiar_fondo(self, claro: bool) -> None:
        self.lienzo.set_opcion("paleta", tema.LIENZO_CLARO if claro else tema.LIENZO_OSCURO)

    def _cambiar_ajuste_chunk(self, activo: bool) -> None:
        self.lienzo.ajuste_chunk = activo

    # ================================================================== archivos
    def confirmar_descarte(self) -> bool:
        if not self.hay_cambios():
            return True
        decision = dialogos.preguntar_cambios(self, self._nombre_documento(), True)
        if decision is dialogos.Decision.GUARDAR:
            return self.guardar()
        return decision is dialogos.Decision.DESCARTAR

    def nuevo(self) -> None:
        if self.confirmar_descarte():
            self._empezar(Documento(), None)
            self.statusBar().showMessage("Diseño nuevo.", 3000)

    def abrir_diseno(self) -> None:
        if not self.confirmar_descarte():
            return
        ruta, _ = QFileDialog.getOpenFileName(self, "Abrir diseño", self._carpeta(),
                                              f"{FILTRO_DISENO};;Todos los archivos (*)")
        if ruta:
            self.abrir_ruta(ruta)

    def abrir_ruta(self, ruta: str) -> bool:
        try:
            cargado = abrir(ruta)
        except ErrorDeArchivo as e:
            QMessageBox.warning(self, "No se pudo abrir el diseño",
                                f"{e}\n\nComprueba que el archivo es un diseño guardado con {tema.NOMBRE_APP} "
                                "(extensión .json) y vuelve a intentarlo.")
            return False
        self._empezar(cargado.documento, Path(ruta))
        self.ajustes.setValue("archivos/carpeta", str(Path(ruta).parent))
        detalle = " (formato anterior de una figura)" if cargado.version == 1 else ""
        self.statusBar().showMessage(f"Diseño abierto: {Path(ruta).name}{detalle}", 5000)
        if cargado.aviso:
            QMessageBox.information(self, "Diseño recalculado", cargado.aviso)
        return True

    def guardar(self) -> bool:
        if self._ruta is None or self._ruta.suffix.lower() != ".json":
            return self.guardar_como()
        return self._escribir(self._ruta)

    def guardar_como(self) -> bool:
        nombre = self._ruta.name if self._ruta else "diseno.json"
        ruta, _ = QFileDialog.getSaveFileName(self, "Guardar diseño", str(Path(self._carpeta()) / nombre),
                                              FILTRO_DISENO)
        if not ruta:
            return False
        return self._escribir(Path(ruta if ruta.lower().endswith(".json") else ruta + ".json"))

    def _escribir(self, ruta: Path) -> bool:
        try:
            guardar(self.documento, ruta)
        except OSError as e:
            QMessageBox.critical(self, "No se pudo guardar",
                                 f"No se pudo escribir «{ruta}»: {e.strerror or e}.\n\nComprueba que la carpeta "
                                 "existe y que tienes permiso de escritura, o elige otra ubicación.")
            return False
        self._ruta = ruta
        self._guardado = self.documento
        self.ajustes.setValue("archivos/carpeta", str(ruta.parent))
        self._actualizar_titulo()
        self.statusBar().showMessage(f"Diseño guardado: {ruta.name}", 5000)
        return True

    def exportar_png(self) -> None:
        if self.construccion.vacia:
            return
        preferencias = {clave: self.ajustes.value(f"exportar/{clave}", defecto)
                        for clave, defecto in (("fondo", "claro"), ("cuadricula", True), ("chunks", True),
                                               ("coordenadas", True))}
        preferencias = {k: (_booleano(v) if k != "fondo" else v) for k, v in preferencias.items()}
        dialogo = DialogoPNG(self, self.construccion, self.construccion_seleccion(), preferencias)
        if dialogo.exec() != DialogoPNG.DialogCode.Accepted:
            return
        opciones = dialogo.opciones()
        sugerido = Path(self._carpeta()) / f"{Path(self._nombre_documento()).stem}.png"
        ruta, _ = QFileDialog.getSaveFileName(self, "Exportar PNG", str(sugerido), "Imagen PNG (*.png)")
        if not ruta:
            return
        ruta = ruta if ruta.lower().endswith(".png") else ruta + ".png"
        imagen = renderizar_png(dialogo.construccion(), **opciones)
        if not imagen.save(ruta, "PNG"):
            QMessageBox.critical(self, "No se pudo exportar",
                                 f"No se pudo escribir la imagen en «{ruta}».\n\nComprueba que la carpeta existe "
                                 "y que tienes permiso de escritura, o elige otra ubicación.")
            return
        for clave in ("fondo", "cuadricula", "chunks", "coordenadas"):
            self.ajustes.setValue(f"exportar/{clave}", opciones[clave])
        self.ajustes.setValue("archivos/carpeta", str(Path(ruta).parent))
        self.statusBar().showMessage(f"Imagen exportada: {Path(ruta).name} ({imagen.width()} × {imagen.height()} px)",
                                     6000)

    def texto_instrucciones(self, tipo: str, seleccion: bool = False) -> str:
        c = self.construccion_seleccion() if seleccion and self.seleccion else self.construccion
        titulo = f"{tema.NOMBRE_APP} — {self._nombre_documento()}" + (" (selección)" if seleccion else "")
        return instrucciones_por_chunk(c, titulo) if tipo == "chunks" else instrucciones(c, titulo)

    def copiar_instrucciones(self, tipo: str = "completa") -> None:
        if self.construccion.vacia:
            return
        seleccion = self.panel_construccion.ambito() == SELECCION and bool(self.seleccion)
        QGuiApplication.clipboard().setText(self.texto_instrucciones(tipo, seleccion))
        forma = "por chunk" if tipo == "chunks" else "completas"
        self.statusBar().showMessage(f"Instrucciones {forma} copiadas al portapapeles.", 4000)

    def exportar_instrucciones(self) -> None:
        if self.construccion.vacia:
            return
        dialogo = DialogoInstrucciones(self, bool(self.seleccion))
        if dialogo.exec() != DialogoInstrucciones.DialogCode.Accepted:
            return
        tipo = dialogo.tipo.currentData()
        seleccion = dialogo.ambito.currentData() == SELECCION
        sugerido = Path(self._carpeta()) / f"{Path(self._nombre_documento()).stem}_instrucciones.txt"
        ruta, _ = QFileDialog.getSaveFileName(self, "Exportar instrucciones", str(sugerido), "Texto (*.txt)")
        if not ruta:
            return
        ruta = ruta if ruta.lower().endswith(".txt") else ruta + ".txt"
        try:
            Path(ruta).write_text(self.texto_instrucciones(tipo, seleccion), encoding="utf-8")
        except OSError as e:
            QMessageBox.critical(self, "No se pudo exportar", f"No se pudo escribir «{ruta}»: {e.strerror or e}.")
            return
        self.statusBar().showMessage(f"Instrucciones exportadas: {Path(ruta).name}", 5000)

    def _carpeta(self) -> str:
        return str(self.ajustes.value("archivos/carpeta", str(Path.home() / "Documents")))

    # ================================================================== ajustes
    def _cargar_ajustes(self) -> None:
        a = self.ajustes
        for accion, clave, defecto in (
            (self.acc_cuadricula, "vista/cuadricula", True), (self.acc_chunks, "vista/chunks", True),
            (self.acc_coordenadas, "vista/coordenadas", True), (self.acc_ejes, "vista/ejes", True),
            (self.acc_fondo_claro, "vista/fondo_claro", False), (self.acc_ajuste_chunk, "vista/ajuste_chunk", False),
            (self.acc_panel, "vista/panel", True),
        ):
            accion.setChecked(_booleano(a.value(clave, defecto)))
        self._mostrar_panel_derecho(self.acc_panel.isChecked())
        self.propiedades.set_plantilla(self._plantilla_guardada())
        geometria = a.value("ventana/geometria")
        if geometria is None or not self.restoreGeometry(geometria):
            self._tamano_inicial()
        divisor = a.value("ventana/divisor")
        if divisor is not None:
            self.divisor.restoreState(divisor)
            self.pestanas.setVisible(self.acc_panel.isChecked())

    def _plantilla_guardada(self) -> Objeto:
        a = self.ajustes
        try:
            objeto = Objeto("", "", str(a.value("plantilla/tipo", "hexagono")),
                            tamano=int(a.value("plantilla/tamano", 21)),
                            orientacion=str(a.value("plantilla/orientacion", "plano")),
                            modo=str(a.value("plantilla/modo", "contorno")),
                            color=str(a.value("plantilla/color", "#5B8C3A")))
            objeto.configuracion().validada()
            objeto.forma()
            return objeto
        except (ErrorDeTamano, ValueError, TypeError):
            return Objeto("", "", "hexagono")

    def _tamano_inicial(self) -> None:
        pantalla = QGuiApplication.primaryScreen()
        if pantalla is None:
            self.resize(1400, 860)
            return
        disponible = pantalla.availableGeometry()
        self.resize(min(1500, int(disponible.width() * 0.92)), min(920, int(disponible.height() * 0.9)))
        self.move(disponible.center() - self.rect().center())

    def guardar_ajustes(self) -> None:
        plantilla = self.propiedades.plantilla()
        valores = {
            "vista/cuadricula": self.acc_cuadricula.isChecked(), "vista/chunks": self.acc_chunks.isChecked(),
            "vista/coordenadas": self.acc_coordenadas.isChecked(), "vista/ejes": self.acc_ejes.isChecked(),
            "vista/fondo_claro": self.acc_fondo_claro.isChecked(),
            "vista/ajuste_chunk": self.acc_ajuste_chunk.isChecked(), "vista/panel": self.acc_panel.isChecked(),
            "plantilla/tipo": plantilla.tipo, "plantilla/tamano": plantilla.tamano,
            "plantilla/orientacion": plantilla.orientacion, "plantilla/modo": plantilla.modo,
            "plantilla/color": plantilla.color,
            "ventana/geometria": self.saveGeometry(), "ventana/divisor": self.divisor.saveState(),
        }
        for clave, valor in valores.items():
            self.ajustes.setValue(clave, valor)

    def closeEvent(self, event) -> None:  # noqa: N802
        if not self.confirmar_descarte():
            event.ignore()
            return
        self.guardar_ajustes()
        super().closeEvent(event)


def _cambios_aplicables(objeto: Objeto, cambios: dict, varios: bool) -> dict:
    """En selecciones múltiples solo se aplica lo que tiene sentido para cada objeto."""
    if objeto.es_compuesta:
        return {k: v for k, v in cambios.items() if k in ("color", "nombre", "visible", "bloqueado", "fusion")
                or (k == "modo" and objeto.fusion == FUSION_SILUETA)}
    if varios:
        return {k: v for k, v in cambios.items() if k in ("color", "modo")}
    return cambios


def _booleano(valor) -> bool:
    return valor in (True, "true", "1", 1)
