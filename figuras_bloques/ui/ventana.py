"""Ventana principal de Hexabloq."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings, QSize, Qt
from PySide6.QtGui import QAction, QGuiApplication, QKeySequence
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QSizePolicy,
    QSplitter,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..archivo import ErrorDeArchivo, abrir, guardar
from ..geometria import TAMANO_MAXIMO, TAMANO_MINIMO, Configuracion, ErrorDeTamano, Figura, generar
from ..guia import formato_num, instrucciones
from . import dialogos, recursos, tema
from .exportar import DialogoPNG, renderizar_png
from .lienzo import Lienzo
from .panel_config import PanelConfiguracion
from .panel_guia import PanelGuia

ANCHO_PANEL = 300
ANCHO_GUIA = 340
TAMANO_MINIMO_VENTANA = QSize(960, 620)
FILTRO_DISENO = f"Diseño de {tema.NOMBRE_APP} (*.json)"


class BarraAdaptable(QWidget):
    """Fila de botones que oculta los textos cuando no hay espacio para mostrarlos."""

    def __init__(self, nombre_objeto: str) -> None:
        super().__init__()
        self.setObjectName(nombre_objeto)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._lay = QHBoxLayout(self)
        self._lay.setContentsMargins(6, 4, 6, 4)
        self._lay.setSpacing(2)
        self._con_texto: list[QToolButton] = []
        self._ancho_con_texto = 0
        self._compacta = False
        self._final = QHBoxLayout()
        self._final.setSpacing(2)

    def boton(self, accion: QAction, texto_visible: bool = True, nombre: str = "herramienta") -> QToolButton:
        boton = QToolButton()
        boton.setObjectName(nombre)
        boton.setDefaultAction(accion)
        boton.setIconSize(QSize(18, 18))
        boton.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon if texto_visible else Qt.ToolButtonStyle.ToolButtonIconOnly
        )
        if texto_visible:
            self._con_texto.append(boton)
        self._lay.addWidget(boton)
        return boton

    def separador(self) -> None:
        linea = QFrame()
        linea.setObjectName("separador")
        linea.setFixedHeight(20)
        self._lay.addSpacing(4)
        self._lay.addWidget(linea)
        self._lay.addSpacing(4)

    def widget(self, w: QWidget) -> None:
        self._lay.addWidget(w)

    def espacio(self, px: int) -> None:
        self._lay.addSpacing(px)

    def cerrar(self) -> None:
        self._lay.addStretch(1)
        self._lay.addLayout(self._final)

    def al_final(self, w: QWidget) -> None:
        self._final.addWidget(w)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if not self._compacta:
            self._ancho_con_texto = self._lay.sizeHint().width()
        compacta = self.width() < self._ancho_con_texto
        if compacta != self._compacta:
            self._compacta = compacta
            estilo = (Qt.ToolButtonStyle.ToolButtonIconOnly if compacta
                      else Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            for boton in self._con_texto:
                boton.setToolButtonStyle(estilo)


class VentanaPrincipal(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.ajustes = QSettings()
        self.setMinimumSize(TAMANO_MINIMO_VENTANA)
        self.figura: Figura | None = None
        self._ruta: Path | None = None
        self._config_base = Configuracion()

        self.lienzo = Lienzo()
        self.lienzo.mensaje_vacio = "No hay figura que mostrar. Corrige el tamaño en el panel de la izquierda."
        self.panel = PanelConfiguracion()
        self.guia = PanelGuia()

        self._crear_acciones()
        self.setMenuWidget(self._crear_barra_superior())
        self.setCentralWidget(self._crear_cuerpo())
        self._crear_estado()
        self._conectar()
        self._cargar_ajustes()
        self.regenerar(reajustar=True)
        self._marcar_guardado()

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
        self.acc_png = a("Exportar PNG", "exportar", ("Ctrl+E",), "Exportar la figura como imagen PNG",
                         self.exportar_png)
        self.acc_copiar = a("Copiar instrucciones", "copiar", ("Ctrl+Shift+C",), "Copiar la guía por filas",
                            self.copiar_instrucciones)
        self.acc_salir = a("Salir", None, ("Ctrl+Q",), "Cerrar la aplicación", self.close)
        self.acc_acercar = a("Acercar", "zoom_mas", ("Ctrl++", "Ctrl+="), "Acercar", lambda: self.lienzo.zoom(1.25))
        self.acc_alejar = a("Alejar", "zoom_menos", ("Ctrl+-",), "Alejar", lambda: self.lienzo.zoom(1 / 1.25))
        self.acc_ajustar = a("Ajustar", "ajustar", ("Ctrl+0",), "Ajustar la figura a la ventana (F)",
                             self.lienzo.ajustar)
        self.acc_centrar = a("Centrar", "centrar", (), "Centrar la figura sin cambiar el zoom (C)",
                             self.lienzo.centrar)
        self.acc_guia = a("Guía", "panel_guia", ("Ctrl+B",), "Mostrar u ocultar la guía de construcción",
                          self._mostrar_guia, marcable=True)
        self.acc_ayuda = a("Cómo se miden las figuras", "ayuda", ("F1",), "", lambda: dialogos.mostrar_ayuda(self))
        self.acc_atajos = a("Atajos de teclado", "teclado", ("Ctrl+/",), "", lambda: dialogos.mostrar_atajos(self))
        self.acc_acerca = a(f"Acerca de {tema.NOMBRE_APP}", "info", (), "",
                            lambda: dialogos.mostrar_acerca_de(self))
        a("Ir al tamaño", None, ("Ctrl+L",), "", lambda: self.panel.enfocar_tamano())
        a("Alternar contorno y relleno", None, ("Ctrl+T",), "", lambda: self.panel.alternar_modo())
        for i, figura in enumerate(("hexagono", "circulo", "triangulo"), 1):
            a(f"Figura {i}", None, (f"Ctrl+{i}",), "", lambda _=False, f=figura: self.panel.seleccionar_figura(f))

    def _acciones_lienzo(self, zona: QWidget) -> None:
        def interruptor(texto, icono, tecla, consejo, slot, marcada=True):
            accion = self._accion(texto, icono, (tecla,), consejo, slot, marcable=True, destino=zona)
            accion.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            accion.setChecked(marcada)
            return accion

        def opcion(nombre):
            return lambda valor: self.lienzo.set_opcion(nombre, valor)

        self.acc_cuadricula = interruptor("Cuadrícula", "cuadricula", "G", "Mostrar u ocultar la cuadrícula",
                                          opcion("cuadricula"))
        self.acc_ejes = interruptor("Ejes", "ejes", "X", "Mostrar u ocultar los ejes que pasan por el centro",
                                    opcion("ejes"))
        self.acc_centro = interruptor("Centro", "centro", "M", "Mostrar u ocultar la marca del centro",
                                      opcion("centro"))
        self.acc_numeros = interruptor("Números", "numeros", "N", "Numeración de filas y columnas",
                                       opcion("numeros"))
        self.acc_fondo_claro = interruptor("Fondo claro", "lienzo", "B",
                                           "Alternar el fondo de la cuadrícula entre oscuro y claro",
                                           self._cambiar_fondo, marcada=False)
        self.acc_auto = interruptor("Auto-ajuste", "ajustar", "A",
                                    "Reencuadrar la vista cuando cambian el tamaño o la figura", None)
        for tecla, slot in (("F", self.lienzo.ajustar), ("C", self.lienzo.centrar)):
            atajo = QAction(zona)
            atajo.setShortcut(QKeySequence(tecla))
            atajo.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            atajo.triggered.connect(slot)
            zona.addAction(atajo)

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
        for accion in (self.acc_nuevo, self.acc_abrir, self.acc_guardar, self.acc_png):
            barra.boton(accion, nombre="accionBarra")
        barra.cerrar()
        boton_guia = QToolButton()
        boton_guia.setObjectName("herramienta")
        boton_guia.setDefaultAction(self.acc_guia)
        boton_guia.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        boton_guia.setIconSize(QSize(18, 18))
        barra.al_final(boton_guia)
        barra.al_final(self._crear_boton_ayuda())
        return barra

    def _crear_boton_ayuda(self) -> QToolButton:
        menu = QMenu(self)
        menu.addActions([self.acc_ayuda, self.acc_atajos])
        menu.addSeparator()
        menu.addActions([self.acc_guardar_como, self.acc_copiar])
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
        self.divisor = QSplitter(Qt.Orientation.Horizontal)
        self.divisor.addWidget(self.panel)
        self.divisor.addWidget(self._crear_zona_lienzo())
        self.divisor.addWidget(self.guia)
        self.divisor.setStretchFactor(1, 1)
        self.divisor.setCollapsible(0, False)
        self.divisor.setCollapsible(1, False)
        self.divisor.setSizes([ANCHO_PANEL, 800, ANCHO_GUIA])
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
        barra.boton(self.acc_alejar, texto_visible=False)
        barra.boton(self.acc_acercar, texto_visible=False)
        barra.boton(self.acc_ajustar)
        barra.boton(self.acc_centrar)
        barra.separador()
        for accion in (self.acc_cuadricula, self.acc_ejes, self.acc_centro, self.acc_numeros):
            barra.boton(accion)
        barra.separador()
        barra.boton(self.acc_fondo_claro)
        barra.boton(self.acc_auto)
        barra.cerrar()
        lay.addWidget(barra)
        lay.addWidget(self.lienzo, 1)
        return zona

    def _crear_estado(self) -> None:
        estado = self.statusBar()
        self.lbl_cursor = QLabel()
        self.lbl_cursor.setMinimumWidth(80)
        self.lbl_figura = QLabel()
        self.lbl_zoom = QLabel()
        estado.addWidget(self.lbl_cursor, 1)
        estado.addPermanentWidget(self.lbl_figura)
        estado.addPermanentWidget(self.lbl_zoom)
        self._mostrar_cursor(None)

    def _conectar(self) -> None:
        self.panel.cambiado.connect(self._al_cambiar_parametros)
        self.lienzo.celdaBajoCursor.connect(self._mostrar_cursor)
        self.lienzo.filaSeleccionada.connect(self.guia.seleccionar_fila)
        self.lienzo.zoomCambiado.connect(self._mostrar_zoom)
        self.guia.filaElegida.connect(lambda fila: self.lienzo.set_fila(fila, emitir=False))
        self.guia.copiarPedido.connect(self.copiar_instrucciones)
        self.divisor.splitterMoved.connect(self._al_mover_divisor)

    def _al_cambiar_parametros(self, afecta_geometria: bool) -> None:
        self.regenerar(reajustar=afecta_geometria and self.acc_auto.isChecked())

    def regenerar(self, reajustar: bool = False) -> None:
        try:
            figura = generar(self.panel.configuracion())
        except ErrorDeTamano as e:
            self.panel.mostrar_error(
                f"{e} Escribe un número entre {TAMANO_MINIMO} y {TAMANO_MAXIMO} o usa el deslizador."
            )
            self._set_figura(None, False)
        else:
            self.panel.mostrar_error(None)
            self._set_figura(figura, reajustar)
        self._actualizar_titulo()

    def _set_figura(self, figura: Figura | None, reajustar: bool) -> None:
        self.figura = figura
        for accion in (self.acc_guardar, self.acc_guardar_como, self.acc_png, self.acc_copiar):
            accion.setEnabled(figura is not None)
        fila = self.lienzo.opciones.fila_resaltada
        self.lienzo.set_figura(figura, reajustar)
        self.guia.set_figura(figura)
        self.panel.mostrar_figura(figura)
        if figura is None:
            self.lbl_figura.setText("Sin figura")
            return
        self.lbl_figura.setText(f"{figura.ancho} × {figura.alto} · {figura.total} bloques")
        if fila is not None and fila < figura.alto:
            self.lienzo.set_fila(fila, emitir=False)
            self.guia.seleccionar_fila(fila)

    def hay_cambios(self) -> bool:
        return self.panel.configuracion() != self._config_base

    def _marcar_guardado(self) -> None:
        self._config_base = self.panel.configuracion()
        self._actualizar_titulo()

    def _nombre_documento(self) -> str:
        return self._ruta.name if self._ruta else "Sin título"

    def _actualizar_titulo(self) -> None:
        cambios = self.hay_cambios()
        self.setWindowTitle(f"{self._nombre_documento()}[*] — {tema.NOMBRE_APP}")
        self.setWindowModified(cambios)
        self.lbl_documento.setText(self._nombre_documento() + (" · sin guardar" if cambios else ""))

    def confirmar_descarte(self) -> bool:
        if not self.hay_cambios():
            return True
        decision = dialogos.preguntar_cambios(self, self._nombre_documento(), self.figura is not None)
        if decision is dialogos.Decision.GUARDAR:
            return self.guardar()
        return decision is dialogos.Decision.DESCARTAR

    def nuevo(self) -> None:
        if not self.confirmar_descarte():
            return
        self._ruta = None
        self.panel.set_configuracion(Configuracion(color=self.panel.configuracion().color))
        self.lienzo.set_fila(None)
        self.regenerar(reajustar=True)
        self._marcar_guardado()
        self.statusBar().showMessage("Diseño nuevo.", 3000)

    def abrir_diseno(self) -> None:
        if not self.confirmar_descarte():
            return
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Abrir diseño", self._carpeta(), f"{FILTRO_DISENO};;Todos los archivos (*)"
        )
        if ruta:
            self.abrir_ruta(ruta)

    def abrir_ruta(self, ruta: str) -> bool:
        try:
            cargado = abrir(ruta)
        except ErrorDeArchivo as e:
            QMessageBox.warning(
                self, "No se pudo abrir el diseño",
                f"{e}\n\nComprueba que el archivo es un diseño guardado con {tema.NOMBRE_APP} "
                "(extensión .json) y vuelve a intentarlo.",
            )
            return False
        self._ruta = Path(ruta)
        self.ajustes.setValue("archivos/carpeta", str(self._ruta.parent))
        self.panel.set_configuracion(cargado.figura.config)
        self.lienzo.set_fila(None)
        self.regenerar(reajustar=True)
        self._marcar_guardado()
        self.statusBar().showMessage(f"Diseño abierto: {self._ruta.name}", 5000)
        if cargado.aviso:
            QMessageBox.information(self, "Diseño recalculado", cargado.aviso)
        return True

    def guardar(self) -> bool:
        if self._ruta is None:
            return self.guardar_como()
        return self._escribir(self._ruta)

    def guardar_como(self) -> bool:
        if self.figura is None:
            return False
        nombre = self._ruta.name if self._ruta else f"{self._nombre_base()}.json"
        ruta, _ = QFileDialog.getSaveFileName(self, "Guardar diseño", str(Path(self._carpeta()) / nombre),
                                              FILTRO_DISENO)
        if not ruta:
            return False
        return self._escribir(Path(ruta if ruta.lower().endswith(".json") else ruta + ".json"))

    def _escribir(self, ruta: Path) -> bool:
        if self.figura is None:
            return False
        try:
            guardar(self.figura, ruta)
        except OSError as e:
            QMessageBox.critical(
                self, "No se pudo guardar",
                f"No se pudo escribir «{ruta}»: {e.strerror or e}.\n\nComprueba que la carpeta existe "
                "y que tienes permiso de escritura, o elige otra ubicación con «Guardar como…».",
            )
            return False
        self._ruta = ruta
        self.ajustes.setValue("archivos/carpeta", str(ruta.parent))
        self._marcar_guardado()
        self.statusBar().showMessage(f"Diseño guardado: {ruta.name}", 5000)
        return True

    def exportar_png(self) -> None:
        if self.figura is None:
            return
        fondo = str(self.ajustes.value("exportar/fondo", "claro"))
        dialogo = DialogoPNG(self, self.figura, self.acc_cuadricula.isChecked(), fondo)
        if dialogo.exec() != DialogoPNG.DialogCode.Accepted:
            return
        opciones = dialogo.opciones()
        sufijo = "_cuadricula" if opciones["cuadricula"] else ""
        sugerido = Path(self._carpeta()) / f"{self._nombre_base()}{sufijo}.png"
        ruta, _ = QFileDialog.getSaveFileName(self, "Exportar PNG", str(sugerido), "Imagen PNG (*.png)")
        if not ruta:
            return
        ruta = ruta if ruta.lower().endswith(".png") else ruta + ".png"
        imagen = renderizar_png(self.figura, **opciones)
        if not imagen.save(ruta, "PNG"):
            QMessageBox.critical(
                self, "No se pudo exportar",
                f"No se pudo escribir la imagen en «{ruta}».\n\nComprueba que la carpeta existe y que "
                "tienes permiso de escritura, o elige otra ubicación.",
            )
            return
        self.ajustes.setValue("archivos/carpeta", str(Path(ruta).parent))
        self.ajustes.setValue("exportar/fondo", opciones["fondo"])
        self.statusBar().showMessage(
            f"Imagen exportada: {Path(ruta).name} ({imagen.width()} × {imagen.height()} px)", 6000
        )

    def copiar_instrucciones(self) -> None:
        if self.figura is None:
            return
        QGuiApplication.clipboard().setText(instrucciones(self.figura))
        self.statusBar().showMessage(
            f"Instrucciones copiadas: {self.figura.alto} filas, {self.figura.total} bloques.", 4000
        )

    def _carpeta(self) -> str:
        return str(self.ajustes.value("archivos/carpeta", str(Path.home() / "Documents")))

    def _nombre_base(self) -> str:
        cfg = self.figura.config
        return "_".join(p for p in (cfg.figura, str(cfg.tamano), cfg.orientacion, cfg.modo) if p)

    def _mostrar_cursor(self, celda) -> None:
        if celda is None or self.figura is None:
            self.lbl_cursor.setText("Pasa el ratón por la cuadrícula para ver las coordenadas.")
            return
        x, y = celda
        dx = (x + 0.5) - self.figura.centro[0]
        dy = self.figura.centro[1] - (y + 0.5)
        partes = [t for t in (_distancia(dx, "a la derecha", "a la izquierda"), _distancia(dy, "arriba", "abajo")) if t]
        estado = "bloque" if self.figura.contiene(x, y) else "vacío"
        relativo = ", ".join(partes) if partes else "en el centro"
        self.lbl_cursor.setText(f"Columna {x + 1} · Fila {y + 1} · {estado} · desde el centro: {relativo}")

    def _mostrar_zoom(self, px_bloque: float) -> None:
        self.lbl_zoom.setText(f"Zoom: {formato_num(px_bloque, 1)} px/bloque")

    def _mostrar_guia(self, visible: bool) -> None:
        self.guia.setVisible(visible)
        tamanos = self.divisor.sizes()
        if visible and tamanos[2] == 0:
            self.divisor.setSizes([tamanos[0], max(200, tamanos[1] - ANCHO_GUIA), ANCHO_GUIA])

    def _al_mover_divisor(self, _pos: int, _indice: int) -> None:
        visible = self.divisor.sizes()[2] > 0
        if visible != self.acc_guia.isChecked():
            self.acc_guia.blockSignals(True)
            self.acc_guia.setChecked(visible)
            self.acc_guia.blockSignals(False)

    def _cambiar_fondo(self, claro: bool) -> None:
        self.lienzo.set_paleta(tema.LIENZO_CLARO if claro else tema.LIENZO_OSCURO)

    def _cargar_ajustes(self) -> None:
        a = self.ajustes
        self.panel.set_configuracion(self._config_guardada())
        for accion, clave, defecto in (
            (self.acc_cuadricula, "vista/cuadricula", True), (self.acc_ejes, "vista/ejes", True),
            (self.acc_centro, "vista/centro", True), (self.acc_numeros, "vista/numeros", True),
            (self.acc_auto, "vista/auto_ajuste", True), (self.acc_guia, "vista/guia", True),
            (self.acc_fondo_claro, "vista/fondo_claro", False),
        ):
            accion.setChecked(_booleano(a.value(clave, defecto)))
        self._mostrar_guia(self.acc_guia.isChecked())
        self.guia.btn_plegar.setChecked(_booleano(a.value("vista/tabla", True)))
        geometria = a.value("ventana/geometria")
        if geometria is None or not self.restoreGeometry(geometria):
            self._tamano_inicial()
        divisor = a.value("ventana/divisor")
        if divisor is not None:
            self.divisor.restoreState(divisor)
            self.guia.setVisible(self.acc_guia.isChecked())

    def _config_guardada(self) -> Configuracion:
        a = self.ajustes
        try:
            return Configuracion(
                figura=str(a.value("diseno/figura", "hexagono")),
                tamano=int(a.value("diseno/tamano", 21)),
                orientacion=str(a.value("diseno/orientacion", "plano")),
                modo=str(a.value("diseno/modo", "contorno")),
                color=str(a.value("diseno/color", Configuracion().color)),
            ).validada()
        except (ErrorDeTamano, ValueError, TypeError):
            return Configuracion()

    def _tamano_inicial(self) -> None:
        pantalla = QGuiApplication.primaryScreen()
        if pantalla is None:
            self.resize(1360, 860)
            return
        disponible = pantalla.availableGeometry()
        self.resize(min(1440, int(disponible.width() * 0.9)), min(900, int(disponible.height() * 0.9)))
        self.move(disponible.center() - self.rect().center())

    def guardar_ajustes(self) -> None:
        cfg = self.panel.configuracion()
        valida = TAMANO_MINIMO <= cfg.tamano <= TAMANO_MAXIMO
        valores = {
            "diseno/figura": cfg.figura,
            "diseno/tamano": cfg.tamano if valida else 21,
            "diseno/orientacion": cfg.orientacion,
            "diseno/modo": cfg.modo,
            "diseno/color": cfg.color,
            "vista/cuadricula": self.acc_cuadricula.isChecked(),
            "vista/ejes": self.acc_ejes.isChecked(),
            "vista/centro": self.acc_centro.isChecked(),
            "vista/numeros": self.acc_numeros.isChecked(),
            "vista/auto_ajuste": self.acc_auto.isChecked(),
            "vista/guia": self.acc_guia.isChecked(),
            "vista/fondo_claro": self.acc_fondo_claro.isChecked(),
            "vista/tabla": self.guia.tabla_desplegada(),
            "ventana/geometria": self.saveGeometry(),
            "ventana/divisor": self.divisor.saveState(),
        }
        for clave, valor in valores.items():
            self.ajustes.setValue(clave, valor)

    def closeEvent(self, event) -> None:  # noqa: N802
        if not self.confirmar_descarte():
            event.ignore()
            return
        self.guardar_ajustes()
        super().closeEvent(event)


def _distancia(valor: float, positivo: str, negativo: str) -> str:
    if abs(valor) < 1e-9:
        return ""
    return f"{formato_num(abs(valor))} {positivo if valor > 0 else negativo}"


def _booleano(valor) -> bool:
    return valor in (True, "true", "1", 1)
