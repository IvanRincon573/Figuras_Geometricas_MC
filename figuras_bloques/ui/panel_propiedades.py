"""Panel de propiedades: plantilla de figura nueva o edición de la selección."""

from __future__ import annotations

import math

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..chunks import chunk_de, local_de
from ..documento import (
    COLOR_POR_DEFECTO,
    FUSION_BLOQUES,
    FUSION_SILUETA,
    NOMBRES_FUSION,
    Documento,
    Objeto,
    limites_de,
)
from ..geometria import (
    ORIENTACION_POR_DEFECTO,
    ORIENTACIONES,
    TAMANO_MAXIMO,
    TAMANO_MINIMO,
    Configuracion,
    ErrorDeTamano,
    generar,
)
from ..guia import formato_num
from . import recursos

PLANTILLA, SIMPLE, COMPUESTA, VARIOS = "plantilla", "simple", "compuesta", "varios"
LIMITE_MUNDO = 30_000_000

FIGURAS_UI = (
    ("hexagono", "Hexágono", "plano", "Hexágono regular (Ctrl+1)"),
    ("circulo", "Círculo", "", "Círculo (Ctrl+2)"),
    ("triangulo", "Triángulo", "arriba", "Triángulo equilátero (Ctrl+3)"),
)
ORIENTACIONES_UI = {
    "plano": ("Lado plano arriba", "Los lados planos quedan arriba y abajo; los vértices, a los lados."),
    "vertice": ("Vértice arriba", "Los vértices quedan arriba y abajo; los lados planos, a los lados."),
    "arriba": ("Arriba", "Vértice hacia el norte (arriba), base abajo."),
    "abajo": ("Abajo", "Vértice hacia el sur (abajo), base arriba."),
    "izquierda": ("Izquierda", "Vértice hacia el oeste, base vertical al este."),
    "derecha": ("Derecha", "Vértice hacia el este, base vertical al oeste."),
}
MEDIDAS_UI = {
    "circulo": ("Diámetro", "Bloques de lado a lado pasando por el centro."),
    "triangulo": ("Ancho de la base", "Bloques que ocupa la base (un lado del triángulo)."),
    "hexagono_plano": ("Ancho total", "Bloques de vértice a vértice, de oeste a este."),
    "hexagono_vertice": ("Ancho total", "Bloques de lado plano a lado plano, de oeste a este."),
}
COLORES = (
    ("Hierba", "#5B8C3A"), ("Esmeralda", "#3FC98A"), ("Piedra", "#8A8F96"), ("Madera", "#9C7246"),
    ("Ladrillo", "#B0503C"), ("Arena", "#D8CB95"), ("Agua", "#3F7FE0"), ("Oro", "#E3B53A"),
    ("Cuarzo", "#ECE6DA"), ("Amatista", "#9061C9"),
)
ALINEACIONES_UI = (
    ("izquierda", "Alinear bordes oeste"), ("centro_x", "Centrar en X"), ("derecha", "Alinear bordes este"),
    ("arriba", "Alinear bordes norte"), ("centro_z", "Centrar en Z"), ("abajo", "Alinear bordes sur"),
)
POSICIONES_DESLIZADOR = 1000


def tamano_desde_deslizador(posicion: int) -> int:
    """Escala cuadrática: más precisión en tamaños pequeños, alcance hasta el máximo."""
    fraccion = posicion / POSICIONES_DESLIZADOR
    return round(TAMANO_MINIMO + (TAMANO_MAXIMO - TAMANO_MINIMO) * fraccion**2)


def deslizador_desde_tamano(tamano: int) -> int:
    limitado = max(TAMANO_MINIMO, min(TAMANO_MAXIMO, tamano))
    return round(math.sqrt((limitado - TAMANO_MINIMO) / (TAMANO_MAXIMO - TAMANO_MINIMO)) * POSICIONES_DESLIZADOR)


def _seccion(texto: str) -> QLabel:
    etiqueta = QLabel(texto.upper())
    etiqueta.setObjectName("seccion")
    return etiqueta


def _ayuda(texto: str = "") -> QLabel:
    etiqueta = QLabel(texto)
    etiqueta.setObjectName("ayuda")
    etiqueta.setWordWrap(True)
    return etiqueta


def _boton(texto: str, consejo: str, icono: str | None = None, marcable: bool = False) -> QToolButton:
    boton = QToolButton()
    boton.setObjectName("segmento")
    boton.setText(texto)
    boton.setToolTip(consejo)
    boton.setCheckable(marcable)
    if icono:
        boton.setIcon(recursos.icono(icono))
    boton.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon if texto
                             else Qt.ToolButtonStyle.ToolButtonIconOnly)
    boton.setIconSize(QSize(18, 18))
    boton.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    return boton


def _contenedor() -> tuple[QWidget, QVBoxLayout]:
    widget = QWidget()
    lay = QVBoxLayout(widget)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(8)
    return widget, lay


class PanelPropiedades(QScrollArea):
    """Señales: ``plantillaCambiada``; ``cambio(cambios, clave)`` sobre la selección;
    ``posicionPedida(x, z)`` para su esquina; ``accion(nombre)`` para el resto."""

    plantillaCambiada = Signal()
    cambio = Signal(dict, str)
    posicionPedida = Signal(int, int)
    accion = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("desplazamientoPanel")
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setMinimumWidth(280)
        self.modo = PLANTILLA
        self._sincronizando = False
        self._plantilla = Objeto("", "", "hexagono", color=COLOR_POR_DEFECTO)
        self._orientaciones = dict(ORIENTACION_POR_DEFECTO)
        self._color = COLOR_POR_DEFECTO
        self._seleccion: tuple[Objeto, ...] = ()

        contenido = QWidget()
        contenido.setObjectName("panelLateral")
        self._lay = QVBoxLayout(contenido)
        self._lay.setContentsMargins(16, 14, 16, 16)
        self._lay.setSpacing(8)
        for crear in (self._crear_encabezado, self._crear_figura, self._crear_tamano, self._crear_orientacion,
                      self._crear_proporciones, self._crear_compuesta, self._crear_modo, self._crear_color,
                      self._crear_posicion, self._crear_estado, self._crear_alineacion, self._crear_acciones):
            crear()
        self._lay.addStretch(1)
        self.setWidget(contenido)
        self._aplicar_modo()

    # ------------------------------------------------------------ construcción
    def _crear_encabezado(self) -> None:
        self.lbl_titulo = QLabel()
        self.lbl_titulo.setObjectName("tituloPanel")
        self.lbl_titulo.setWordWrap(True)
        self.campo_nombre = QLineEdit()
        self.campo_nombre.setPlaceholderText("Nombre del objeto")
        self.campo_nombre.setToolTip("Nombre que aparece en el panel de objetos")
        self.campo_nombre.editingFinished.connect(self._al_cambiar_nombre)
        self.lbl_aviso = _ayuda()
        self._lay.addWidget(self.lbl_titulo)
        self._lay.addWidget(self.campo_nombre)
        self._lay.addWidget(self.lbl_aviso)

    def _crear_figura(self) -> None:
        self.seccion_figura, lay = _contenedor()
        lay.addWidget(_seccion("Figura"))
        fila = QHBoxLayout()
        fila.setSpacing(8)
        self.grupo_figura = QButtonGroup(self)
        self.botones_figura: dict[str, QToolButton] = {}
        for clave, texto, orientacion, consejo in FIGURAS_UI:
            boton = QToolButton()
            boton.setObjectName("tarjetaFigura")
            boton.setText(texto)
            boton.setToolTip(consejo)
            boton.setIcon(recursos.icono_figura(clave, orientacion, lado=34))
            boton.setIconSize(QSize(34, 34))
            boton.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            boton.setCheckable(True)
            boton.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self.grupo_figura.addButton(boton)
            self.botones_figura[clave] = boton
            fila.addWidget(boton)
        self.grupo_figura.buttonClicked.connect(lambda _b: self._al_cambiar_tipo())
        lay.addLayout(fila)
        self._lay.addWidget(self.seccion_figura)

    def _crear_tamano(self) -> None:
        self.seccion_tamano, lay = _contenedor()
        lay.addWidget(_seccion("Tamaño"))
        self.lbl_medida = QLabel()
        lay.addWidget(self.lbl_medida)
        self.spin_tamano = QSpinBox()
        self.spin_tamano.setObjectName("tamano")
        # Admite valores fuera de 1-1000 para poder explicar por qué no son válidos.
        self.spin_tamano.setRange(0, 99999)
        self.spin_tamano.setSuffix(" bloques")
        self.spin_tamano.setAccelerated(True)
        self.spin_tamano.setToolTip("Tamaño en bloques (1 a 1000). Re Pág / Av Pág: ±10 · Ctrl+L para ir aquí.")
        self.lbl_medida.setBuddy(self.spin_tamano)
        lay.addWidget(self.spin_tamano)
        self.deslizador = QSlider(Qt.Orientation.Horizontal)
        self.deslizador.setRange(0, POSICIONES_DESLIZADOR)
        self.deslizador.setPageStep(50)
        self.deslizador.setToolTip("Arrastra para cambiar el tamaño; el campo de arriba permite el valor exacto.")
        lay.addWidget(self.deslizador)
        self.lbl_ayuda_medida = _ayuda()
        lay.addWidget(self.lbl_ayuda_medida)
        self.lbl_error = QLabel()
        self.lbl_error.setObjectName("error")
        self.lbl_error.setWordWrap(True)
        self.lbl_error.hide()
        lay.addWidget(self.lbl_error)
        self.spin_tamano.valueChanged.connect(self._al_cambiar_spin)
        self.deslizador.valueChanged.connect(self._al_mover_deslizador)
        self._lay.addWidget(self.seccion_tamano)

    def _crear_orientacion(self) -> None:
        self.seccion_orientacion, lay = _contenedor()
        lay.addWidget(_seccion("Orientación"))
        self.grupo_orientacion = QButtonGroup(self)
        self.botones_orientacion: dict[str, QToolButton] = {}
        self._rejilla_orientacion = QGridLayout()
        self._rejilla_orientacion.setSpacing(6)
        lay.addLayout(self._rejilla_orientacion)
        for figura in ("hexagono", "triangulo"):
            for orientacion in ORIENTACIONES[figura]:
                texto, consejo = ORIENTACIONES_UI[orientacion]
                boton = _boton(texto, consejo, marcable=True)
                boton.setIcon(recursos.icono_figura(figura, orientacion, lado=20))
                self.grupo_orientacion.addButton(boton)
                self.botones_orientacion[orientacion] = boton
        self.grupo_orientacion.buttonClicked.connect(lambda _b: self._al_cambiar_orientacion())
        self._lay.addWidget(self.seccion_orientacion)

    def _crear_proporciones(self) -> None:
        self.seccion_proporciones, lay = _contenedor()
        lay.addWidget(_seccion("Proporciones"))
        self.lbl_proporciones = QLabel()
        self.lbl_proporciones.setTextFormat(Qt.TextFormat.RichText)
        self.lbl_proporciones.setWordWrap(True)
        self.lbl_paridad = _ayuda()
        lay.addWidget(self.lbl_proporciones)
        lay.addWidget(self.lbl_paridad)
        self._lay.addWidget(self.seccion_proporciones)

    def _crear_compuesta(self) -> None:
        self.seccion_compuesta, lay = _contenedor()
        lay.addWidget(_seccion("Figura compuesta"))
        self.combo_fusion = QComboBox()
        self.combo_fusion.addItem("Conservar los bloques", FUSION_BLOQUES)
        self.combo_fusion.addItem("Silueta conjunta", FUSION_SILUETA)
        self.combo_fusion.setToolTip(
            "Conservar los bloques: unión exacta de los bloques de las figuras originales.\n"
            "Silueta conjunta: une sus áreas y genera un único contorno o relleno."
        )
        self.combo_fusion.currentIndexChanged.connect(
            lambda _i: self._emitir({"fusion": self.combo_fusion.currentData()}, "fusion"))
        self.lbl_origenes = _ayuda()
        self.btn_separar = _boton("Separar en figuras originales", "Recupera las figuras de origen (Ctrl+Shift+M)",
                                  "separar")
        self.btn_separar.clicked.connect(lambda: self.accion.emit("separar"))
        for w in (self.combo_fusion, self.lbl_origenes, self.btn_separar):
            lay.addWidget(w)
        self._lay.addWidget(self.seccion_compuesta)

    def _crear_modo(self) -> None:
        self.seccion_modo, lay = _contenedor()
        lay.addWidget(_seccion("Modo"))
        fila = QHBoxLayout()
        fila.setSpacing(6)
        self.grupo_modo = QButtonGroup(self)
        self.btn_contorno = _boton("Contorno", "Solo el borde, de un bloque de grosor (Ctrl+T alterna).",
                                   marcable=True)
        self.btn_relleno = _boton("Relleno", "La figura completa (Ctrl+T alterna).", marcable=True)
        self.btn_contorno.setIcon(recursos.icono_figura("hexagono", "plano", "contorno", lado=20))
        self.btn_relleno.setIcon(recursos.icono_figura("hexagono", "plano", "relleno", lado=20))
        for boton in (self.btn_contorno, self.btn_relleno):
            self.grupo_modo.addButton(boton)
            fila.addWidget(boton)
        self.grupo_modo.buttonClicked.connect(lambda _b: self._al_cambiar_modo())
        lay.addLayout(fila)
        self.lbl_modo = _ayuda()
        lay.addWidget(self.lbl_modo)
        self._lay.addWidget(self.seccion_modo)

    def _crear_color(self) -> None:
        self.seccion_color, lay = _contenedor()
        lay.addWidget(_seccion("Color de los bloques"))
        rejilla = QGridLayout()
        rejilla.setSpacing(6)
        self.grupo_color = QButtonGroup(self)
        self.muestras: dict[str, QToolButton] = {}
        for i, (nombre, hexa) in enumerate(COLORES):
            boton = QToolButton()
            boton.setObjectName("muestra")
            boton.setCheckable(True)
            boton.setToolTip(f"{nombre} ({hexa})")
            boton.setAccessibleName(f"Color {nombre}")
            boton.setStyleSheet(f"QToolButton#muestra {{ background: {hexa}; }}")
            boton.clicked.connect(lambda _=False, h=hexa: self._elegir_color(h))
            self.grupo_color.addButton(boton)
            self.muestras[hexa] = boton
            rejilla.addWidget(boton, i // 5, i % 5)
        lay.addLayout(rejilla)
        self.btn_color = _boton("Color personalizado…", "Elegir cualquier color para los bloques", "color")
        self.btn_color.clicked.connect(self._dialogo_color)
        self.lbl_color = _ayuda()
        lay.addWidget(self.btn_color)
        lay.addWidget(self.lbl_color)
        self._lay.addWidget(self.seccion_color)

    def _crear_posicion(self) -> None:
        self.seccion_posicion, lay = _contenedor()
        lay.addWidget(_seccion("Posición (esquina norte-oeste)"))
        fila = QGridLayout()
        fila.setHorizontalSpacing(8)
        self.spin_x = self._spin_coordenada("X (este)")
        self.spin_z = self._spin_coordenada("Z (sur)")
        for i, (texto, spin) in enumerate((("X", self.spin_x), ("Z", self.spin_z))):
            etiqueta = QLabel(texto)
            etiqueta.setBuddy(spin)
            fila.addWidget(etiqueta, 0, 2 * i)
            fila.addWidget(spin, 0, 2 * i + 1)
        lay.addLayout(fila)
        self.lbl_medidas = _ayuda()
        lay.addWidget(self.lbl_medidas)
        self._lay.addWidget(self.seccion_posicion)

    def _spin_coordenada(self, consejo: str) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(-LIMITE_MUNDO, LIMITE_MUNDO)
        spin.setKeyboardTracking(False)
        spin.setAccelerated(True)
        spin.setToolTip(f"Coordenada {consejo} en bloques. Las flechas del teclado en la cuadrícula "
                        "mueven 1 bloque; con Mayús, 16 (un chunk).")
        spin.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        spin.setMinimumWidth(70)  # sin esto reserva espacio para ±30 000 000
        spin.valueChanged.connect(lambda _v: self._al_cambiar_posicion())
        return spin

    def _crear_estado(self) -> None:
        self.seccion_estado, lay = _contenedor()
        lay.addWidget(_seccion("Estado"))
        self.chk_visible = QCheckBox("Visible (cuenta en la construcción)")
        self.chk_bloqueado = QCheckBox("Bloqueado (no se puede mover ni editar)")
        self.chk_visible.toggled.connect(lambda v: self._emitir({"visible": v}, "visible"))
        self.chk_bloqueado.toggled.connect(lambda v: self._emitir({"bloqueado": v}, "bloqueado"))
        lay.addWidget(self.chk_visible)
        lay.addWidget(self.chk_bloqueado)
        self._lay.addWidget(self.seccion_estado)

    def _crear_alineacion(self) -> None:
        self.seccion_alinear, lay = _contenedor()
        lay.addWidget(_seccion("Alinear"))
        rejilla = QGridLayout()
        rejilla.setSpacing(6)
        for i, (clave, consejo) in enumerate(ALINEACIONES_UI):
            boton = _boton("", consejo, f"alinear_{clave}")
            boton.setAccessibleName(consejo)
            boton.clicked.connect(lambda _=False, c=clave: self.accion.emit(f"alinear:{c}"))
            rejilla.addWidget(boton, i // 3, i % 3)
        lay.addLayout(rejilla)
        lay.addWidget(_ayuda("Alinea bordes o centros con la caja de toda la selección."))
        self._lay.addWidget(self.seccion_alinear)

    def _crear_acciones(self) -> None:
        self.seccion_acciones, lay = _contenedor()
        self.btn_anadir = QPushButton("Añadir figura")
        self.btn_anadir.setObjectName("primario")
        self.btn_anadir.setIcon(recursos.icono("anadir"))
        self.btn_anadir.setToolTip("Añade la figura en el centro de la vista (Insert). "
                                   "También puedes usar la herramienta Añadir y hacer clic en la cuadrícula.")
        self.btn_anadir.clicked.connect(lambda: self.accion.emit("anadir"))
        fila = QHBoxLayout()
        fila.setSpacing(6)
        self.btn_agrupar = _boton("Agrupar", "Mueve las figuras juntas sin unirlas (Ctrl+G)", "agrupar")
        self.btn_fusionar = _boton("Fusionar…", "Crea una figura compuesta (Ctrl+M)", "fusionar")
        self.btn_agrupar.clicked.connect(lambda: self.accion.emit("agrupar"))
        self.btn_fusionar.clicked.connect(lambda: self.accion.emit("fusionar"))
        fila.addWidget(self.btn_agrupar)
        fila.addWidget(self.btn_fusionar)
        self.lbl_ayuda_accion = _ayuda()
        lay.addWidget(self.btn_anadir)
        lay.addLayout(fila)
        lay.addWidget(self.lbl_ayuda_accion)
        self._lay.addWidget(self.seccion_acciones)
        self._fila_acciones = (self.btn_agrupar, self.btn_fusionar)

    # ------------------------------------------------------------ estado público
    def plantilla(self) -> Objeto:
        return self._plantilla

    def set_plantilla(self, objeto: Objeto) -> None:
        self._plantilla = objeto
        self._orientaciones[objeto.tipo] = objeto.orientacion
        if self.modo == PLANTILLA:
            self.mostrar(Documento(), ())

    def mostrar(self, doc: Documento, seleccion) -> None:
        self._seleccion = doc.seleccionados(seleccion)
        if not self._seleccion:
            self.modo = PLANTILLA
        elif len(self._seleccion) > 1:
            self.modo = VARIOS
        else:
            self.modo = COMPUESTA if self._seleccion[0].es_compuesta else SIMPLE
        self._sincronizando = True
        try:
            self._cargar_valores(doc)
            self._aplicar_modo()
        finally:
            self._sincronizando = False

    def seleccionar_tipo(self, tipo: str) -> None:
        if self.modo in (PLANTILLA, SIMPLE):
            self.botones_figura[tipo].setChecked(True)
            self._al_cambiar_tipo()

    def alternar_modo(self) -> None:
        (self.btn_contorno if self.btn_relleno.isChecked() else self.btn_relleno).setChecked(True)
        self._al_cambiar_modo()

    def enfocar_tamano(self) -> None:
        if self.seccion_tamano.isVisible():
            self.spin_tamano.setFocus(Qt.FocusReason.ShortcutFocusReason)
            self.spin_tamano.selectAll()

    def mostrar_error(self, mensaje: str | None) -> None:
        self.lbl_error.setVisible(bool(mensaje))
        self.lbl_error.setText(mensaje or "")
        self.spin_tamano.setProperty("error", bool(mensaje))
        self.spin_tamano.style().unpolish(self.spin_tamano)
        self.spin_tamano.style().polish(self.spin_tamano)

    # ------------------------------------------------------------ carga de valores
    def _objeto_base(self) -> Objeto:
        return self._seleccion[0] if self._seleccion else self._plantilla

    def _cargar_valores(self, doc: Documento) -> None:
        base = self._objeto_base()
        if self.modo == PLANTILLA:
            self.lbl_titulo.setText("Nueva figura")
        elif self.modo == VARIOS:
            self.lbl_titulo.setText(f"{len(self._seleccion)} objetos seleccionados")
        else:
            self.lbl_titulo.setText("Figura compuesta" if self.modo == COMPUESTA else "Figura")
            self.campo_nombre.setText(base.nombre)
        if not base.es_compuesta:
            self.botones_figura[base.tipo].setChecked(True)
            self._orientaciones[base.tipo] = base.orientacion
            self.spin_tamano.setValue(base.tamano)
            self._actualizar_controles_tipo(base.tipo)
            self.mostrar_error(None)
        (self.btn_relleno if base.modo == "relleno" else self.btn_contorno).setChecked(True)
        self._marcar_color(base.color)
        self._actualizar_proporciones(base)
        if self.modo == COMPUESTA:
            self.combo_fusion.setCurrentIndex(self.combo_fusion.findData(base.fusion))
            nombres = ", ".join(o.nombre for o in base.origenes)
            self.lbl_origenes.setText(f"{NOMBRES_FUSION[base.fusion].capitalize()} de "
                                      f"{len(base.origenes)} figuras: {nombres}.")
        if self.modo != PLANTILLA:
            self._cargar_posicion()
            self.chk_visible.setChecked(base.visible)
            self.chk_bloqueado.setChecked(base.bloqueado)
        bloqueados = [o for o in self._seleccion if o.bloqueado]
        if bloqueados and len(bloqueados) == len(self._seleccion):
            self.lbl_aviso.setText("Bloqueado: desbloquéalo para moverlo o editarlo.")
        elif bloqueados:
            self.lbl_aviso.setText(f"{len(bloqueados)} objetos bloqueados no se modificarán.")
        else:
            self.lbl_aviso.setText("")

    def _cargar_posicion(self) -> None:
        x0, z0, x1, z1 = limites_de(self._seleccion)
        self.spin_x.setValue(x0)
        self.spin_z.setValue(z0)
        cx, cz = chunk_de(x0, z0)
        lx, lz = local_de(x0, z0)
        self.lbl_medidas.setText(
            f"Ocupa {x1 - x0 + 1} × {z1 - z0 + 1} bloques (X × Z): X {x0}…{x1}, Z {z0}…{z1}.<br>"
            f"Esquina en el chunk ({cx}, {cz}), posición local ({lx}, {lz})."
        )
        self.lbl_medidas.setTextFormat(Qt.TextFormat.RichText)

    def _actualizar_proporciones(self, base: Objeto) -> None:
        if base.es_compuesta:
            return
        try:
            figura = generar(base.configuracion())
        except ErrorDeTamano:
            self.lbl_proporciones.setText("—")
            self.lbl_paridad.setText("")
            return
        self.lbl_proporciones.setText(_texto_proporciones(figura))
        self.lbl_paridad.setText(_texto_paridad(figura.config))

    def _aplicar_modo(self) -> None:
        modo = self.modo
        bloqueado = bool(self._seleccion) and all(o.bloqueado for o in self._seleccion)
        compuesta = modo == COMPUESTA
        silueta = compuesta and self._seleccion[0].fusion == FUSION_SILUETA
        circulo = self.botones_figura["circulo"].isChecked()
        visibles = {
            self.campo_nombre: modo in (SIMPLE, COMPUESTA),
            self.seccion_figura: modo in (PLANTILLA, SIMPLE),
            self.seccion_tamano: modo in (PLANTILLA, SIMPLE),
            self.seccion_orientacion: modo in (PLANTILLA, SIMPLE) and not circulo,
            self.seccion_proporciones: modo in (PLANTILLA, SIMPLE),
            self.seccion_compuesta: compuesta,
            self.seccion_modo: modo != COMPUESTA or silueta,
            self.seccion_posicion: modo != PLANTILLA,
            self.seccion_estado: modo in (SIMPLE, COMPUESTA),
            self.seccion_alinear: modo == VARIOS,
            self.btn_anadir: modo == PLANTILLA,
            self.btn_agrupar: modo == VARIOS,
            self.btn_fusionar: modo == VARIOS,
        }
        for widget, visible in visibles.items():
            widget.setVisible(visible)
        for seccion in (self.seccion_figura, self.seccion_tamano, self.seccion_orientacion, self.seccion_compuesta,
                        self.seccion_modo, self.seccion_color, self.seccion_posicion, self.seccion_alinear):
            seccion.setEnabled(not bloqueado)
        self.btn_separar.setEnabled(not bloqueado)
        self.lbl_modo.setText("En la silueta conjunta, el contorno elimina las líneas internas."
                              if silueta else "")
        self.lbl_ayuda_accion.setText(
            "Agrupar mantiene las figuras independientes. Fusionar crea una figura compuesta."
            if modo == VARIOS else "")

    def _actualizar_controles_tipo(self, tipo: str) -> None:
        orientacion = self._orientaciones[tipo]
        clave = f"{tipo}_{orientacion}" if tipo == "hexagono" else tipo
        medida, ayuda = MEDIDAS_UI[clave]
        self.lbl_medida.setText(f"{medida} (en bloques)")
        self.lbl_ayuda_medida.setText(ayuda)
        for boton in self.botones_orientacion.values():
            self._rejilla_orientacion.removeWidget(boton)
            boton.hide()
        columnas = 1 if tipo == "hexagono" else 2
        for i, nombre in enumerate(o for o in ORIENTACIONES.get(tipo, ()) if o):
            boton = self.botones_orientacion[nombre]
            self._rejilla_orientacion.addWidget(boton, i // columnas, i % columnas)
            boton.show()
            boton.setChecked(nombre == orientacion)
        self.seccion_orientacion.setVisible(tipo != "circulo" and self.modo in (PLANTILLA, SIMPLE))
        self.deslizador.blockSignals(True)
        self.deslizador.setValue(deslizador_desde_tamano(self.spin_tamano.value()))
        self.deslizador.blockSignals(False)

    # ------------------------------------------------------------ cambios del usuario
    def _tipo_marcado(self) -> str:
        boton = self.grupo_figura.checkedButton()
        return next((k for k, b in self.botones_figura.items() if b is boton), "hexagono")

    def _emitir(self, cambios: dict, clave: str) -> None:
        if self._sincronizando:
            return
        if self.modo == PLANTILLA:
            self._actualizar_plantilla(cambios)
            return
        self.cambio.emit(cambios, clave)

    def _actualizar_plantilla(self, cambios: dict) -> None:
        candidata = Objeto("", "", **{**_atributos(self._plantilla), **cambios})
        try:
            candidata.forma()
        except ErrorDeTamano as e:
            self.mostrar_error(f"{e} Escribe un número entre {TAMANO_MINIMO} y {TAMANO_MAXIMO} o usa el deslizador.")
            return
        self.mostrar_error(None)
        self._plantilla = candidata
        self._actualizar_proporciones(candidata)
        self.plantillaCambiada.emit()

    def _al_cambiar_tipo(self) -> None:
        tipo = self._tipo_marcado()
        self._actualizar_controles_tipo(tipo)
        self._emitir({"tipo": tipo, "orientacion": self._orientaciones[tipo]}, "tipo")

    def _al_cambiar_orientacion(self) -> None:
        boton = self.grupo_orientacion.checkedButton()
        orientacion = next(o for o, b in self.botones_orientacion.items() if b is boton)
        tipo = self._tipo_marcado()
        self._orientaciones[tipo] = orientacion
        self._actualizar_controles_tipo(tipo)
        self._emitir({"orientacion": orientacion}, "orientacion")

    def _al_cambiar_spin(self, valor: int) -> None:
        if not self.deslizador.isSliderDown():
            self.deslizador.blockSignals(True)
            self.deslizador.setValue(deslizador_desde_tamano(valor))
            self.deslizador.blockSignals(False)
        self._cambiar_tamano(valor)

    def _al_mover_deslizador(self, posicion: int) -> None:
        valor = tamano_desde_deslizador(posicion)
        self.spin_tamano.blockSignals(True)
        self.spin_tamano.setValue(valor)
        self.spin_tamano.blockSignals(False)
        self._cambiar_tamano(valor)

    def _cambiar_tamano(self, valor: int) -> None:
        if self._sincronizando:
            return
        if not TAMANO_MINIMO <= valor <= TAMANO_MAXIMO:
            medida = self.lbl_medida.text().split(" (")[0].lower()
            self.mostrar_error(f"El {medida} debe estar entre {TAMANO_MINIMO} y {TAMANO_MAXIMO} bloques "
                               f"(has puesto {valor}). Escribe un número dentro de ese rango o usa el deslizador.")
            return
        self.mostrar_error(None)
        self._emitir({"tamano": valor}, "tamano")

    def _al_cambiar_modo(self) -> None:
        self._emitir({"modo": "relleno" if self.btn_relleno.isChecked() else "contorno"}, "modo")

    def _elegir_color(self, color: str) -> None:
        self._marcar_color(color)
        self._emitir({"color": self._color}, "color")

    def _marcar_color(self, color: str) -> None:
        self._color = QColor(color).name().upper()
        boton = self.muestras.get(self._color)
        self.grupo_color.setExclusive(boton is not None)
        for hexa, muestra in self.muestras.items():
            muestra.setChecked(hexa == self._color)
        nombre = next((n for n, h in COLORES if h == self._color), "personalizado")
        self.lbl_color.setText(f"Color actual: {nombre} ({self._color})")

    def _dialogo_color(self) -> None:
        color = QColorDialog.getColor(QColor(self._color), self, "Color de los bloques")
        if color.isValid():
            self._elegir_color(color.name())

    def _al_cambiar_nombre(self) -> None:
        nombre = self.campo_nombre.text().strip()
        if nombre and self._seleccion and nombre != self._seleccion[0].nombre:
            self._emitir({"nombre": nombre}, "nombre")

    def _al_cambiar_posicion(self) -> None:
        if not self._sincronizando:
            self.posicionPedida.emit(self.spin_x.value(), self.spin_z.value())


def _atributos(objeto: Objeto) -> dict:
    return {"tipo": objeto.tipo, "tamano": objeto.tamano, "orientacion": objeto.orientacion,
            "modo": objeto.modo, "color": objeto.color}


def _texto_proporciones(figura) -> str:
    cfg = figura.config
    if cfg.figura == "circulo":
        return f"Ancho = largo = <b>{figura.ancho}</b> bloques"
    if cfg.figura == "triangulo" and cfg.orientacion in ("izquierda", "derecha"):
        return (f"Ancho calculado: {formato_num(figura.ancho_teorico)} → <b>{figura.ancho} bloques</b>"
                f"<br>Largo (base): <b>{figura.alto}</b> bloques")
    return (f"Largo calculado: {formato_num(figura.alto_teorico)} → <b>{figura.alto} bloques</b>"
            f"<br>Ancho: <b>{figura.ancho}</b> bloques")


def _texto_paridad(cfg: Configuracion) -> str:
    par = cfg.tamano % 2 == 0
    if cfg.figura == "triangulo":
        return "Base par: el vértice ocupa 2 bloques." if par else "Base impar: el vértice es un solo bloque."
    return "Tamaño par: el centro cae entre dos bloques." if par else "Tamaño impar: hay un bloque central."
