"""Ventana principal de la aplicación."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QPointF,
    QRectF,
    QSettings,
    QSize,
    Qt,
)
from PySide6.QtGui import (
    QAction,
    QColor,
    QGuiApplication,
    QIcon,
    QImage,
    QKeySequence,
    QPainter,
    QPixmap,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QTableView,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .. import __version__
from ..archivo import ErrorDeArchivo, abrir, guardar
from ..geometria import (
    ORIENTACION_POR_DEFECTO,
    ORIENTACIONES,
    TAMANO_MAXIMO,
    TAMANO_MINIMO,
    Configuracion,
    ErrorDeTamano,
    Figura,
    descripcion,
    generar,
)
from ..guia import filas_guia, formato_num, instrucciones, resumen, texto_tramos_largo
from .lienzo import Lienzo
from .render import OpcionesDibujo, Paleta, dibujar_figura

COLORES = [
    ("Hierba", "#5B8C3A"),
    ("Piedra", "#7F7F7F"),
    ("Madera", "#9C7246"),
    ("Ladrillo", "#9B4A3A"),
    ("Arena", "#D8CB95"),
    ("Agua", "#3F6FD8"),
    ("Oro", "#E3B53A"),
    ("Cuarzo", "#E8E2D6"),
    ("Obsidiana", "#2A2238"),
    ("Lana roja", "#B33A33"),
]

TEXTO_ORIENTACION = {
    "arriba": "Vértice arriba ▲",
    "abajo": "Vértice abajo ▼",
    "izquierda": "Vértice a la izquierda ◀",
    "derecha": "Vértice a la derecha ▶",
    "plano": "Lado plano arriba ⬣",
    "vertice": "Vértice arriba ⬢",
}

ETIQUETA_TAMANO = {
    "circulo": "Diámetro",
    "triangulo": "Ancho de la base",
    "hexagono": "Ancho total",
}

AYUDA_TAMANO = {
    "circulo": "Bloques de lado a lado pasando por el centro.",
    "triangulo": "Bloques que ocupa la base (un lado del triángulo).",
    "hexagono_plano": "Bloques de vértice a vértice (izquierda a derecha).",
    "hexagono_vertice": "Bloques de lado plano a lado plano (izquierda a derecha).",
}


def icono_figura(figura: str, orientacion: str, color: str = "#8CC152", lado: int = 30) -> QIcon:
    """Icono pixelado generado con la propia geometría del programa."""
    tam = {"circulo": 11, "triangulo": 12, "hexagono": 12}[figura]
    fig = generar(Configuracion(figura, tam, orientacion, "relleno", color))
    pix = QPixmap(lado, lado)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    s = min((lado - 2) / fig.ancho, (lado - 2) / fig.alto)
    ox = (lado - fig.ancho * s) / 2
    oy = (lado - fig.alto * s) / 2
    for x, y in fig.celdas:
        p.fillRect(QRectF(ox + x * s, oy + y * s, s, s), QColor(color))
    p.end()
    return QIcon(pix)


class ModeloFilas(QAbstractTableModel):
    CABECERAS = ("Fila", "Bloques", "Tramos (columna inicio–fin)")

    def __init__(self) -> None:
        super().__init__()
        self._filas = []

    def set_figura(self, figura: Figura | None) -> None:
        self.beginResetModel()
        self._filas = filas_guia(figura) if figura else []
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._filas)

    def columnCount(self, parent=QModelIndex()) -> int:  # noqa: N802
        return 3

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        f = self._filas[index.row()]
        col = index.column()
        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0:
                return str(f.fila)
            if col == 1:
                return str(f.bloques)
            if len(f.tramos) <= 1:
                return f.texto_tramos
            return "   |   ".join(f"{a}–{b}" if a != b else f"{a}" for a, b in f.tramos)
        if role == Qt.ItemDataRole.TextAlignmentRole:
            if col < 2:
                return int(Qt.AlignmentFlag.AlignCenter)
            return int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        if role == Qt.ItemDataRole.ToolTipRole:
            partes = [
                f"Tramo {i}: columnas {a} a {b} ({b - a + 1} bloque{'s' if b > a else ''})"
                for i, (a, b) in enumerate(f.tramos, 1)
            ]
            return f"Fila {f.fila}: {f.bloques} bloques\n" + "\n".join(partes)
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):  # noqa: N802
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self.CABECERAS[section]
        return None


class DialogoPNG(QDialog):
    def __init__(self, parent: QWidget, figura: Figura, cuadricula: bool) -> None:
        super().__init__(parent)
        self.setWindowTitle("Exportar imagen PNG")
        self.figura = figura
        lay = QVBoxLayout(self)
        form = QFormLayout()
        self.px = QSpinBox()
        self.px.setRange(2, 64)
        self.px.setValue(20 if max(figura.ancho, figura.alto) <= 200 else 8)
        self.px.setSuffix(" px por bloque")
        form.addRow("Tamaño de cada bloque:", self.px)
        self.cuadricula = QCheckBox("Incluir cuadrícula")
        self.cuadricula.setChecked(cuadricula)
        self.numeros = QCheckBox("Incluir numeración de filas y columnas")
        self.transparente = QCheckBox("Fondo transparente")
        lay.addLayout(form)
        for w in (self.cuadricula, self.numeros, self.transparente):
            lay.addWidget(w)
        self.info = QLabel()
        self.info.setObjectName("aviso")
        lay.addWidget(self.info)
        botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        botones.button(QDialogButtonBox.StandardButton.Save).setText("Guardar PNG…")
        botones.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        lay.addWidget(botones)
        self.px.valueChanged.connect(self._actualizar_info)
        self.numeros.toggled.connect(self._actualizar_info)
        self._actualizar_info()

    def margen(self) -> int:
        return 3 if self.numeros.isChecked() else 1

    def tamano_imagen(self) -> tuple[int, int]:
        m = self.margen()
        s = self.px.value()
        return (self.figura.ancho + 2 * m) * s, (self.figura.alto + 2 * m) * s

    def _actualizar_info(self) -> None:
        w, h = self.tamano_imagen()
        texto = f"Imagen de {w} × {h} píxeles."
        if max(w, h) > 20000:
            texto += " Demasiado grande: reduce los píxeles por bloque."
        self.info.setText(texto)

    def accept(self) -> None:
        if max(self.tamano_imagen()) > 20000:
            QMessageBox.warning(
                self, "Imagen demasiado grande",
                "La imagen superaría los 20 000 píxeles de lado. Reduce los píxeles por bloque.",
            )
            return
        super().accept()


def renderizar_png(
    figura: Figura, px: int, cuadricula: bool, numeros: bool, transparente: bool
) -> QImage:
    """Imagen de la figura, sin ejes, centro ni resaltados (solo bloques)."""
    m = 3 if numeros else 1
    w = (figura.ancho + 2 * m) * px
    h = (figura.alto + 2 * m) * px
    img = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent if transparente else Paleta.fondo)
    p = QPainter(img)
    opciones = OpcionesDibujo(
        cuadricula=cuadricula, ejes=False, centro=False, numeros=numeros, marco=False, fondo=None
    )
    dibujar_figura(p, figura, px, QPointF(m * px, m * px), QRectF(0, 0, w, h), opciones)
    p.end()
    return img


def _seccion(texto: str) -> QLabel:
    l = QLabel(texto.upper())
    l.setObjectName("seccion")
    return l


class VentanaPrincipal(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Figuras con bloques")
        self.resize(1440, 880)
        self.setMinimumSize(980, 620)
        self.ajustes = QSettings("FigurasBloques", "FigurasBloques")
        self.figura: Figura | None = None
        self._sincronizando = False
        self._ruta_actual: Path | None = None

        self.lienzo = Lienzo()
        self.lienzo.mensaje_vacio = "Corrige el tamaño para ver la figura."
        self.modelo = ModeloFilas()

        self._crear_acciones()
        self._crear_menus()
        self._crear_barra()
        panel = self._crear_panel()
        guia = self._crear_guia()

        divisor = QSplitter(Qt.Orientation.Horizontal)
        divisor.addWidget(panel)
        divisor.addWidget(self.lienzo)
        divisor.addWidget(guia)
        divisor.setStretchFactor(0, 0)
        divisor.setStretchFactor(1, 1)
        divisor.setStretchFactor(2, 0)
        divisor.setCollapsible(1, False)
        divisor.setSizes([300, 800, 360])
        self.divisor = divisor
        self.setCentralWidget(divisor)

        self._crear_estado()
        self._conectar()
        self._cargar_ajustes()
        self.regenerar(reajustar=True)

    # ============================================================ construcción
    def _crear_acciones(self) -> None:
        def accion(texto, atajo=None, slot=None, tip=None):
            a = QAction(texto, self)
            if atajo:
                a.setShortcut(QKeySequence(atajo))
            if slot:
                a.triggered.connect(slot)
            if tip:
                a.setStatusTip(tip)
                a.setToolTip(f"{tip} ({QKeySequence(atajo).toString()})" if atajo else tip)
            return a

        self.acc_abrir = accion("Abrir diseño…", "Ctrl+O", self.abrir_diseno, "Abrir un diseño JSON")
        self.acc_guardar = accion("Guardar diseño…", "Ctrl+S", self.guardar_diseno, "Guardar el diseño en JSON")
        self.acc_png = accion("Exportar PNG…", "Ctrl+E", self.exportar_png, "Exportar la figura como imagen PNG")
        self.acc_copiar = accion("Copiar instrucciones", "Ctrl+Shift+C", self.copiar_instrucciones,
                                 "Copiar la guía por filas al portapapeles")
        self.acc_salir = accion("Salir", "Ctrl+Q", self.close)
        self.acc_centrar = accion("Centrar", "C", self.lienzo.centrar, "Centrar la figura sin cambiar el zoom")
        self.acc_ajustar = accion("Ajustar a la ventana", "F", self.lienzo.ajustar,
                                  "Ajustar el zoom para ver la figura completa")
        self.acc_mas = accion("Acercar", "Ctrl++", lambda: self.lienzo.zoom(1.25), "Acercar")
        self.acc_menos = accion("Alejar", "Ctrl+-", lambda: self.lienzo.zoom(1 / 1.25), "Alejar")
        self.acc_ayuda = accion("Cómo se miden las figuras", "F1", self.mostrar_ayuda)
        self.acc_acerca = accion("Acerca de", None, self.acerca_de)

    def _crear_menus(self) -> None:
        mb = self.menuBar()
        m = mb.addMenu("&Archivo")
        m.addActions([self.acc_abrir, self.acc_guardar])
        m.addSeparator()
        m.addActions([self.acc_png, self.acc_copiar])
        m.addSeparator()
        m.addAction(self.acc_salir)
        v = mb.addMenu("&Vista")
        v.addActions([self.acc_centrar, self.acc_ajustar, self.acc_mas, self.acc_menos])
        a = mb.addMenu("A&yuda")
        a.addActions([self.acc_ayuda, self.acc_acerca])

    def _crear_barra(self) -> None:
        tb = QToolBar("Herramientas")
        tb.setMovable(False)
        tb.setIconSize(QSize(18, 18))
        tb.addAction(self.acc_abrir)
        tb.addAction(self.acc_guardar)
        tb.addAction(self.acc_png)
        tb.addSeparator()
        tb.addAction(self.acc_menos)
        self.lbl_zoom = QLabel("100 %")
        self.lbl_zoom.setMinimumWidth(110)
        self.lbl_zoom.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tb.addWidget(self.lbl_zoom)
        tb.addAction(self.acc_mas)
        tb.addAction(self.acc_centrar)
        tb.addAction(self.acc_ajustar)
        tb.addSeparator()
        self.chk_cuadricula = QCheckBox("Cuadrícula")
        self.chk_ejes = QCheckBox("Ejes")
        self.chk_centro = QCheckBox("Centro")
        self.chk_numeros = QCheckBox("Numeración")
        self.chk_auto = QCheckBox("Ajuste automático")
        self.chk_auto.setToolTip("Reajusta el zoom cada vez que cambia el tamaño de la figura")
        for chk in (self.chk_cuadricula, self.chk_ejes, self.chk_centro, self.chk_numeros, self.chk_auto):
            chk.setChecked(True)
            tb.addWidget(chk)
            espacio = QWidget()
            espacio.setFixedWidth(6)
            tb.addWidget(espacio)
        self.addToolBar(tb)

    def _crear_panel(self) -> QWidget:
        contenido = QWidget()
        contenido.setObjectName("panel")
        lay = QVBoxLayout(contenido)
        lay.setContentsMargins(14, 12, 14, 14)
        lay.setSpacing(8)

        titulo = QLabel("Figuras con bloques")
        titulo.setObjectName("titulo")
        sub = QLabel("Plantillas pixeladas para construir")
        sub.setObjectName("subtitulo")
        lay.addWidget(titulo)
        lay.addWidget(sub)

        # --- Figura
        lay.addWidget(_seccion("Figura"))
        fila = QHBoxLayout()
        fila.setSpacing(6)
        self.grupo_figura = QButtonGroup(self)
        self.botones_figura: dict[str, QToolButton] = {}
        for clave, texto, orient in (
            ("hexagono", "Hexágono", "plano"),
            ("circulo", "Círculo", ""),
            ("triangulo", "Triángulo", "arriba"),
        ):
            b = QToolButton()
            b.setObjectName("figura")
            b.setText(texto)
            b.setIcon(icono_figura(clave, orient))
            b.setIconSize(QSize(30, 30))
            b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            b.setCheckable(True)
            b.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self.grupo_figura.addButton(b)
            self.botones_figura[clave] = b
            fila.addWidget(b)
        lay.addLayout(fila)

        # --- Tamaño
        lay.addWidget(_seccion("Tamaño"))
        self.lbl_tamano = QLabel()
        lay.addWidget(self.lbl_tamano)
        self.spin_tamano = QSpinBox()
        self.spin_tamano.setObjectName("tamano")
        # Rango amplio a propósito: los valores fuera de 1–1000 muestran un mensaje.
        self.spin_tamano.setRange(0, 99999)
        self.spin_tamano.setSuffix(" bloques")
        self.spin_tamano.setAccelerated(True)
        lay.addWidget(self.spin_tamano)
        self.lbl_ayuda_tamano = QLabel()
        self.lbl_ayuda_tamano.setObjectName("aviso")
        self.lbl_ayuda_tamano.setWordWrap(True)
        lay.addWidget(self.lbl_ayuda_tamano)
        rapidos = QGridLayout()
        rapidos.setSpacing(4)
        for i, (texto, delta) in enumerate((("−10", -10), ("−1", -1), ("+1", 1), ("+10", 10))):
            b = QPushButton(texto)
            b.setToolTip(f"{'Sumar' if delta > 0 else 'Restar'} {abs(delta)} bloque{'s' if abs(delta) > 1 else ''}")
            b.clicked.connect(lambda _=False, d=delta: self.spin_tamano.setValue(
                max(TAMANO_MINIMO, min(TAMANO_MAXIMO, self.spin_tamano.value() + d))))
            rapidos.addWidget(b, 0, i)
        lay.addLayout(rapidos)
        self.lbl_error = QLabel()
        self.lbl_error.setObjectName("error")
        self.lbl_error.setWordWrap(True)
        self.lbl_error.hide()
        lay.addWidget(self.lbl_error)
        self.lbl_paridad = QLabel()
        self.lbl_paridad.setObjectName("aviso")
        self.lbl_paridad.setWordWrap(True)
        lay.addWidget(self.lbl_paridad)

        # --- Orientación
        self.sec_orientacion = _seccion("Orientación")
        lay.addWidget(self.sec_orientacion)
        self.combo_orient = QComboBox()
        lay.addWidget(self.combo_orient)

        # --- Altura calculada
        lay.addWidget(_seccion("Proporciones"))
        self.lbl_alto_calc = QLabel()
        self.lbl_alto_calc.setWordWrap(True)
        self.lbl_alto_calc.setTextFormat(Qt.TextFormat.RichText)
        lay.addWidget(self.lbl_alto_calc)

        # --- Modo
        lay.addWidget(_seccion("Modo"))
        fila_modo = QHBoxLayout()
        self.grupo_modo = QButtonGroup(self)
        self.btn_contorno = QPushButton("Contorno")
        self.btn_relleno = QPushButton("Relleno")
        for b in (self.btn_contorno, self.btn_relleno):
            b.setCheckable(True)
            self.grupo_modo.addButton(b)
            fila_modo.addWidget(b)
        lay.addLayout(fila_modo)

        # --- Color
        lay.addWidget(_seccion("Color de los bloques"))
        rejilla = QGridLayout()
        rejilla.setSpacing(6)
        self.grupo_color = QButtonGroup(self)
        self.grupo_color.setExclusive(True)
        self.muestras: dict[str, QPushButton] = {}
        for i, (nombre, hexa) in enumerate(COLORES):
            b = QPushButton()
            b.setObjectName("muestra")
            b.setCheckable(True)
            b.setToolTip(f"{nombre} ({hexa})")
            b.setStyleSheet(f"background: {hexa};")
            b.clicked.connect(lambda _=False, h=hexa: self._elegir_color(h))
            self.grupo_color.addButton(b)
            self.muestras[hexa] = b
            rejilla.addWidget(b, i // 5, i % 5)
        lay.addLayout(rejilla)
        self.btn_color = QPushButton("Otro color…")
        self.btn_color.clicked.connect(self._dialogo_color)
        lay.addWidget(self.btn_color)

        lay.addStretch(1)
        nota = QLabel(
            "Rueda: zoom · Arrastrar: mover · Clic: resaltar fila\n"
            "↑/↓: fila anterior/siguiente · Esc: quitar resaltado"
        )
        nota.setObjectName("aviso")
        nota.setWordWrap(True)
        lay.addWidget(nota)

        scroll = QScrollArea()
        scroll.setWidget(contenido)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMinimumWidth(270)
        scroll.setMaximumWidth(420)
        return scroll

    def _crear_guia(self) -> QWidget:
        w = QWidget()
        w.setObjectName("guia")
        w.setMinimumWidth(300)
        lay = QVBoxLayout(w)
        lay.setContentsMargins(14, 12, 14, 14)
        lay.setSpacing(8)

        titulo = QLabel("Guía de construcción")
        titulo.setObjectName("titulo")
        lay.addWidget(titulo)
        self.lbl_desc = QLabel()
        self.lbl_desc.setObjectName("subtitulo")
        self.lbl_desc.setWordWrap(True)
        lay.addWidget(self.lbl_desc)

        total_box = QHBoxLayout()
        etiqueta_total = QLabel("Bloques necesarios")
        etiqueta_total.setObjectName("etiquetaDato")
        self.lbl_total = QLabel("—")
        self.lbl_total.setObjectName("datoGrande")
        total_box.addWidget(etiqueta_total)
        total_box.addStretch(1)
        total_box.addWidget(self.lbl_total)
        lay.addLayout(total_box)

        self.form_datos = QFormLayout()
        self.form_datos.setHorizontalSpacing(12)
        self.form_datos.setVerticalSpacing(4)
        self.datos: dict[str, QLabel] = {}
        for clave in ("Ancho real", "Alto real", "Centro", "Lado"):
            et = QLabel(clave)
            et.setObjectName("etiquetaDato")
            val = QLabel("—")
            val.setObjectName("dato")
            val.setWordWrap(True)
            self.form_datos.addRow(et, val)
            self.datos[clave] = val
            self.datos[clave + "_et"] = et
        lay.addLayout(self.form_datos)

        lay.addWidget(_seccion("Por filas (de arriba abajo)"))
        self.tabla = QTableView()
        self.tabla.setModel(self.modelo)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.verticalHeader().setDefaultSectionSize(26)
        cab = self.tabla.horizontalHeader()
        cab.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        cab.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        cab.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        lay.addWidget(self.tabla, 1)

        nav = QHBoxLayout()
        self.btn_ant = QPushButton("▲ Anterior")
        self.btn_sig = QPushButton("Siguiente ▼")
        self.btn_quitar = QPushButton("Quitar")
        self.btn_ant.setToolTip("Resaltar la fila anterior (↑)")
        self.btn_sig.setToolTip("Resaltar la fila siguiente (↓)")
        self.btn_quitar.setToolTip("Quitar el resaltado (Esc)")
        for b in (self.btn_ant, self.btn_sig, self.btn_quitar):
            nav.addWidget(b)
        lay.addLayout(nav)
        self.lbl_fila = QLabel("Haz clic en una fila de la tabla o del dibujo para seguirla.")
        self.lbl_fila.setObjectName("aviso")
        self.lbl_fila.setWordWrap(True)
        lay.addWidget(self.lbl_fila)

        self.btn_copiar = QPushButton("Copiar instrucciones")
        self.btn_copiar.setObjectName("primario")
        self.btn_copiar.clicked.connect(self.copiar_instrucciones)
        lay.addWidget(self.btn_copiar)
        return w

    def _crear_estado(self) -> None:
        sb = self.statusBar()
        self.lbl_cursor = QLabel("Pasa el ratón por la cuadrícula para ver las coordenadas.")
        sb.addWidget(self.lbl_cursor, 1)
        self.lbl_estado_fig = QLabel()
        sb.addPermanentWidget(self.lbl_estado_fig)

    def _conectar(self) -> None:
        self.grupo_figura.buttonClicked.connect(self._cambio_figura)
        self.spin_tamano.valueChanged.connect(lambda _v: self.regenerar())
        self.combo_orient.currentIndexChanged.connect(lambda _i: self.regenerar())
        self.grupo_modo.buttonClicked.connect(lambda _b: self.regenerar(reajustar=False))
        self.chk_cuadricula.toggled.connect(lambda v: self.lienzo.set_opcion("cuadricula", v))
        self.chk_ejes.toggled.connect(lambda v: self.lienzo.set_opcion("ejes", v))
        self.chk_centro.toggled.connect(lambda v: self.lienzo.set_opcion("centro", v))
        self.chk_numeros.toggled.connect(lambda v: self.lienzo.set_opcion("numeros", v))
        self.chk_auto.toggled.connect(lambda v: v and self.lienzo.ajustar())
        self.lienzo.celdaBajoCursor.connect(self._mostrar_cursor)
        self.lienzo.filaSeleccionada.connect(self._fila_desde_lienzo)
        self.lienzo.zoomCambiado.connect(self._mostrar_zoom)
        self.tabla.selectionModel().currentRowChanged.connect(self._fila_desde_tabla)
        self.btn_ant.clicked.connect(lambda: self.lienzo.mover_fila(-1))
        self.btn_sig.clicked.connect(lambda: self.lienzo.mover_fila(1))
        self.btn_quitar.clicked.connect(lambda: self.lienzo.set_fila(None))

    # =============================================================== estado
    def _figura_actual(self) -> str:
        for clave, b in self.botones_figura.items():
            if b.isChecked():
                return clave
        return "hexagono"

    def _color_actual(self) -> str:
        return getattr(self, "_color", COLORES[0][1])

    def configuracion(self) -> Configuracion:
        figura = self._figura_actual()
        orient = self.combo_orient.currentData() or ORIENTACION_POR_DEFECTO[figura]
        modo = "relleno" if self.btn_relleno.isChecked() else "contorno"
        return Configuracion(figura, self.spin_tamano.value(), orient, modo, self._color_actual())

    def aplicar_configuracion(self, cfg: Configuracion) -> None:
        """Pone los controles en ``cfg`` sin disparar regeneraciones intermedias."""
        self._sincronizando = True
        try:
            self.botones_figura.get(cfg.figura, self.botones_figura["hexagono"]).setChecked(True)
            self._rellenar_orientaciones(cfg.figura, cfg.orientacion)
            self.spin_tamano.setValue(cfg.tamano)
            (self.btn_relleno if cfg.modo == "relleno" else self.btn_contorno).setChecked(True)
            self._color = cfg.color
            self._marcar_muestra()
        finally:
            self._sincronizando = False

    def _rellenar_orientaciones(self, figura: str, actual: str) -> None:
        self.combo_orient.blockSignals(True)
        self.combo_orient.clear()
        for o in ORIENTACIONES[figura]:
            if o:
                self.combo_orient.addItem(TEXTO_ORIENTACION[o], o)
        idx = self.combo_orient.findData(actual)
        self.combo_orient.setCurrentIndex(max(0, idx))
        self.combo_orient.blockSignals(False)
        tiene = figura != "circulo"
        self.combo_orient.setVisible(tiene)
        self.sec_orientacion.setVisible(tiene)

    def _cambio_figura(self, _boton=None) -> None:
        figura = self._figura_actual()
        actual = self.combo_orient.currentData()
        self._rellenar_orientaciones(figura, actual if actual in ORIENTACIONES[figura] else ORIENTACION_POR_DEFECTO[figura])
        self.regenerar(reajustar=True)

    def _elegir_color(self, hexa: str) -> None:
        self._color = hexa.upper()
        self._marcar_muestra()
        if self.figura is not None:
            self.regenerar(reajustar=False)

    def _marcar_muestra(self) -> None:
        color = self._color_actual().upper()
        b = self.muestras.get(color)
        if b is not None:
            b.setChecked(True)
        else:
            self.grupo_color.setExclusive(False)
            for m in self.muestras.values():
                m.setChecked(False)
            self.grupo_color.setExclusive(True)
        texto = "#000" if QColor(color).lightness() > 140 else "#FFF"
        self.btn_color.setText(f"Otro color…   {color}")
        self.btn_color.setStyleSheet(
            f"QPushButton {{ background: {color}; color: {texto}; border-color: #191C1F; }}"
        )

    def _dialogo_color(self) -> None:
        c = QColorDialog.getColor(QColor(self._color_actual()), self, "Color de los bloques")
        if c.isValid():
            self._elegir_color(c.name())

    # ============================================================ regenerar
    def regenerar(self, reajustar: bool | None = None) -> None:
        if self._sincronizando:
            return
        cfg = self.configuracion()
        clave = cfg.figura if cfg.figura != "hexagono" else f"hexagono_{cfg.orientacion}"
        self.lbl_tamano.setText(f"{ETIQUETA_TAMANO[cfg.figura]} (en bloques)")
        self.lbl_ayuda_tamano.setText(AYUDA_TAMANO[clave])
        try:
            figura = generar(cfg)
        except ErrorDeTamano as e:
            self.lbl_error.setText(str(e))
            self.lbl_error.show()
            self._set_figura(None, False)
            return
        self.lbl_error.hide()
        if reajustar is None:
            reajustar = self.chk_auto.isChecked()
        self._set_figura(figura, reajustar)

    def _set_figura(self, figura: Figura | None, reajustar: bool) -> None:
        self.figura = figura
        for a in (self.acc_guardar, self.acc_png, self.acc_copiar):
            a.setEnabled(figura is not None)
        self.btn_copiar.setEnabled(figura is not None)
        fila = self.lienzo.opciones.fila_resaltada
        self.lienzo.set_figura(figura, reajustar)
        self._sincronizando = True
        self.modelo.set_figura(figura)
        self._sincronizando = False
        if figura is None:
            self.lbl_total.setText("—")
            self.lbl_desc.setText("")
            for k in ("Ancho real", "Alto real", "Centro", "Lado"):
                self.datos[k].setText("—")
            self.lbl_alto_calc.setText("")
            self.lbl_paridad.setText("")
            self.lbl_estado_fig.setText("")
            return
        cfg = figura.config
        r = resumen(figura)
        self.lbl_desc.setText(descripcion(cfg))
        self.lbl_total.setText(f"{figura.total:,}".replace(",", "."))
        self.datos["Ancho real"].setText(f"{figura.ancho} bloques")
        self.datos["Alto real"].setText(f"{figura.alto} bloques")
        self.datos["Centro"].setText(r["Centro"])
        lado_clave = next((k for k in ("Lado superior", "Lados verticales") if k in r), None)
        self.datos["Lado_et"].setVisible(lado_clave is not None)
        self.datos["Lado"].setVisible(lado_clave is not None)
        if lado_clave:
            self.datos["Lado_et"].setText(lado_clave)
            self.datos["Lado"].setText(r[lado_clave])

        # Proporciones: medida pedida y dimensión calculada.
        if cfg.figura == "circulo":
            texto = (f"Ancho = alto = <b>{figura.ancho}</b> bloques.")
        else:
            girado = cfg.figura == "triangulo" and cfg.orientacion in ("izquierda", "derecha")
            if girado:
                texto = (f"Ancho calculado: {formato_num(figura.ancho_teorico)} → "
                         f"<b>{figura.ancho} bloques</b><br>Alto (base): <b>{figura.alto}</b> bloques")
            else:
                texto = (f"Alto calculado: {formato_num(figura.alto_teorico)} → "
                         f"<b>{figura.alto} bloques</b><br>Ancho: <b>{figura.ancho}</b> bloques")
        self.lbl_alto_calc.setText(texto)
        par = cfg.tamano % 2 == 0
        if cfg.figura == "triangulo":
            self.lbl_paridad.setText(
                "Base par: el vértice ocupa 2 bloques." if par else "Base impar: el vértice es un solo bloque."
            )
        else:
            self.lbl_paridad.setText(
                "Tamaño par: el centro cae entre dos bloques." if par
                else "Tamaño impar: hay un bloque central."
            )
        self.lbl_estado_fig.setText(f"{figura.ancho} × {figura.alto} · {figura.total} bloques")
        if fila is not None and fila < figura.alto:
            self.lienzo.set_fila(fila, emitir=False)
            self._seleccionar_en_tabla(fila)
            self._describir_fila(fila)

    # ============================================================ filas
    def _seleccionar_en_tabla(self, fila: int | None) -> None:
        self._sincronizando = True
        try:
            if fila is None:
                self.tabla.clearSelection()
                self.tabla.setCurrentIndex(QModelIndex())
            else:
                idx = self.modelo.index(fila, 0)
                self.tabla.setCurrentIndex(idx)
                self.tabla.selectRow(fila)
                self.tabla.scrollTo(idx, QAbstractItemView.ScrollHint.EnsureVisible)
        finally:
            self._sincronizando = False

    def _fila_desde_lienzo(self, fila) -> None:
        self._seleccionar_en_tabla(fila)
        self._describir_fila(fila)

    def _fila_desde_tabla(self, actual: QModelIndex, _anterior: QModelIndex) -> None:
        if self._sincronizando:
            return
        fila = actual.row() if actual.isValid() else None
        self.lienzo.set_fila(fila, emitir=False)
        self._describir_fila(fila)

    def _describir_fila(self, fila: int | None) -> None:
        if fila is None or self.figura is None:
            self.lbl_fila.setText("Haz clic en una fila de la tabla o del dibujo para seguirla.")
            return
        f = filas_guia(self.figura)[fila]
        self.lbl_fila.setText(
            f"<b>Fila {f.fila} de {self.figura.alto}</b>: {f.bloques} bloque{'s' if f.bloques != 1 else ''} — "
            f"{texto_tramos_largo(f.tramos)}"
        )

    # ============================================================ cursor/zoom
    def _mostrar_cursor(self, celda) -> None:
        if celda is None or self.figura is None:
            self.lbl_cursor.setText("Pasa el ratón por la cuadrícula para ver las coordenadas.")
            return
        x, y = celda
        dentro = self.figura.contiene(x, y)
        dx = (x + 0.5) - self.figura.centro[0]
        dy = self.figura.centro[1] - (y + 0.5)

        def rel(v: float, pos: str, neg: str) -> str:
            if abs(v) < 1e-9:
                return ""
            return f"{formato_num(abs(v))} {pos if v > 0 else neg}"

        partes = [p for p in (rel(dx, "a la derecha", "a la izquierda"), rel(dy, "arriba", "abajo")) if p]
        rel_txt = ", ".join(partes) if partes else "en el centro"
        estado = "■ bloque de la figura" if dentro else "□ vacío"
        self.lbl_cursor.setText(
            f"Columna {x + 1} · Fila {y + 1}   —   {estado}   —   desde el centro: {rel_txt}"
        )

    def _mostrar_zoom(self, px_bloque: float) -> None:
        self.lbl_zoom.setText(f"{formato_num(px_bloque, 1)} px/bloque")

    # ============================================================ acciones
    def copiar_instrucciones(self) -> None:
        if self.figura is None:
            return
        QGuiApplication.clipboard().setText(instrucciones(self.figura))
        self.statusBar().showMessage("Instrucciones copiadas al portapapeles.", 4000)

    def _carpeta(self) -> str:
        return str(self.ajustes.value("carpeta", str(Path.home() / "Documents")))

    def _nombre_base(self) -> str:
        cfg = self.figura.config
        partes = [cfg.figura, str(cfg.tamano)]
        if cfg.orientacion:
            partes.append(cfg.orientacion)
        partes.append(cfg.modo)
        return "_".join(partes)

    def guardar_diseno(self) -> None:
        if self.figura is None:
            return
        ruta, _ = QFileDialog.getSaveFileName(
            self, "Guardar diseño", str(Path(self._carpeta()) / f"{self._nombre_base()}.json"),
            "Diseño de figuras (*.json)",
        )
        if not ruta:
            return
        try:
            guardar(self.figura, ruta)
        except OSError as e:
            QMessageBox.critical(self, "No se pudo guardar", f"No se pudo guardar el archivo:\n{e}")
            return
        self.ajustes.setValue("carpeta", str(Path(ruta).parent))
        self.statusBar().showMessage(f"Diseño guardado en {ruta}", 5000)

    def abrir_diseno(self) -> None:
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Abrir diseño", self._carpeta(), "Diseño de figuras (*.json);;Todos los archivos (*)"
        )
        if ruta:
            self.abrir_ruta(ruta)

    def abrir_ruta(self, ruta: str) -> None:
        try:
            cargado = abrir(ruta)
        except ErrorDeArchivo as e:
            QMessageBox.warning(self, "No se pudo abrir el diseño", str(e))
            return
        self.ajustes.setValue("carpeta", str(Path(ruta).parent))
        self.aplicar_configuracion(cargado.figura.config)
        self.lienzo.set_fila(None)
        self.regenerar(reajustar=True)
        self.statusBar().showMessage(f"Diseño abierto: {Path(ruta).name}", 5000)
        if cargado.aviso:
            QMessageBox.information(self, "Aviso", cargado.aviso)

    def exportar_png(self) -> None:
        if self.figura is None:
            return
        dlg = DialogoPNG(self, self.figura, self.chk_cuadricula.isChecked())
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        sufijo = "_cuadricula" if dlg.cuadricula.isChecked() else ""
        ruta, _ = QFileDialog.getSaveFileName(
            self, "Exportar PNG", str(Path(self._carpeta()) / f"{self._nombre_base()}{sufijo}.png"),
            "Imagen PNG (*.png)",
        )
        if not ruta:
            return
        if not ruta.lower().endswith(".png"):
            ruta += ".png"
        img = renderizar_png(
            self.figura, dlg.px.value(), dlg.cuadricula.isChecked(),
            dlg.numeros.isChecked(), dlg.transparente.isChecked(),
        )
        if not img.save(ruta, "PNG"):
            QMessageBox.critical(self, "No se pudo exportar", f"No se pudo escribir la imagen en:\n{ruta}")
            return
        self.ajustes.setValue("carpeta", str(Path(ruta).parent))
        self.statusBar().showMessage(f"Imagen exportada: {ruta} ({img.width()} × {img.height()} px)", 6000)

    def mostrar_ayuda(self) -> None:
        QMessageBox.information(
            self,
            "Cómo se miden las figuras",
            "<p><b>Cada celda es un bloque.</b> Las figuras se construyen solo con bloques completos.</p>"
            "<p><b>Medidas</b><br>"
            "• Círculo: diámetro = ancho = alto en bloques.<br>"
            "• Triángulo: ancho de la base en bloques; la altura se calcula como base × √3/2.<br>"
            "• Hexágono, lado plano arriba: ancho de vértice a vértice; alto = ancho × √3/2.<br>"
            "• Hexágono, vértice arriba: ancho de lado plano a lado plano; alto = ancho × 2/√3.</p>"
            "<p><b>Qué bloques forman la figura</b><br>"
            "Se dibuja la figura geométrica exacta sobre la cuadrícula y se toma cada bloque "
            "cuyo <i>centro</i> queda dentro de ella. El alto calculado se redondea eligiendo la "
            "colocación que más se acerca al valor teórico.</p>"
            "<p><b>Centro</b><br>Con tamaño impar hay una columna central; con tamaño par el centro "
            "cae en la línea entre dos columnas (lo mismo con las filas).</p>"
            "<p><b>Contorno</b><br>Son los bloques de la figura rellena que tocan el exterior por un "
            "lado. En los escalones se unen en diagonal, como en las construcciones habituales.</p>"
            "<p>Los ejes, el centro y el resaltado son solo ayudas visuales: no cuentan como bloques.</p>",
        )

    def acerca_de(self) -> None:
        QMessageBox.about(
            self,
            "Acerca de",
            f"<b>Figuras con bloques</b> {__version__}<br>"
            "Generador de círculos, triángulos y hexágonos pixelados para construir con bloques.<br>"
            "Funciona sin conexión. Las figuras son aproximaciones discretas de formas regulares.",
        )

    # ============================================================ ajustes
    def _cargar_ajustes(self) -> None:
        a = self.ajustes
        try:
            cfg = Configuracion(
                figura=str(a.value("figura", "hexagono")),
                tamano=int(a.value("tamano", 21)),
                orientacion=str(a.value("orientacion", "plano")),
                modo=str(a.value("modo", "contorno")),
                color=str(a.value("color", COLORES[0][1])),
            ).validada()
        except (ErrorDeTamano, ValueError, TypeError):
            cfg = Configuracion()
        self.aplicar_configuracion(cfg)
        for chk, clave in (
            (self.chk_cuadricula, "cuadricula"), (self.chk_ejes, "ejes"), (self.chk_centro, "centro"),
            (self.chk_numeros, "numeros"), (self.chk_auto, "auto"),
        ):
            valor = a.value(clave, True)
            # Las señales «toggled» ya están conectadas y actualizan el lienzo.
            chk.setChecked(valor in (True, "true", "1", 1))
        geo = a.value("geometria")
        if geo is not None:
            self.restoreGeometry(geo)

    def closeEvent(self, event) -> None:  # noqa: N802
        a = self.ajustes
        cfg = self.configuracion()
        a.setValue("figura", cfg.figura)
        a.setValue("tamano", cfg.tamano if TAMANO_MINIMO <= cfg.tamano <= TAMANO_MAXIMO else 21)
        a.setValue("orientacion", cfg.orientacion)
        a.setValue("modo", cfg.modo)
        a.setValue("color", cfg.color)
        a.setValue("cuadricula", self.chk_cuadricula.isChecked())
        a.setValue("ejes", self.chk_ejes.isChecked())
        a.setValue("centro", self.chk_centro.isChecked())
        a.setValue("numeros", self.chk_numeros.isChecked())
        a.setValue("auto", self.chk_auto.isChecked())
        a.setValue("geometria", self.saveGeometry())
        super().closeEvent(event)
