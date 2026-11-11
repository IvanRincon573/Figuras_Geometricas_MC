"""Panel de información para construir: medidas, total y guía por filas."""

from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableView,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..geometria import Figura, descripcion
from ..guia import FilaGuia, filas_guia, formato_num, resumen, texto_tramos_largo
from . import recursos

AYUDA_FILA = "Haz clic en una fila de la tabla o del dibujo para seguirla. ↑/↓ cambian de fila."


class ModeloFilas(QAbstractTableModel):
    CABECERAS = ("Fila", "Bloques", "Columnas (inicio–fin)")

    def __init__(self) -> None:
        super().__init__()
        self._filas: list[FilaGuia] = []

    def set_figura(self, figura: Figura | None) -> None:
        self.beginResetModel()
        self._filas = filas_guia(figura) if figura else []
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._filas)

    def columnCount(self, parent=QModelIndex()) -> int:  # noqa: N802
        return len(self.CABECERAS)

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        fila = self._filas[index.row()]
        columna = index.column()
        if role == Qt.ItemDataRole.DisplayRole:
            return (str(fila.fila), str(fila.bloques), self._texto_tramos(fila))[columna]
        if role == Qt.ItemDataRole.TextAlignmentRole:
            if columna < 2:
                return int(Qt.AlignmentFlag.AlignCenter)
            return int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        if role == Qt.ItemDataRole.ToolTipRole:
            return f"Fila {fila.fila}: {fila.bloques} bloques — {texto_tramos_largo(fila.tramos)}"
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):  # noqa: N802
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self.CABECERAS[section]
        return None

    @staticmethod
    def _texto_tramos(fila: FilaGuia) -> str:
        if len(fila.tramos) <= 1:
            return fila.texto_tramos
        return "   |   ".join(f"{a}–{b}" if a != b else f"{a}" for a, b in fila.tramos)


class _Dato(QFrame):
    def __init__(self, etiqueta: str, acento: bool = False) -> None:
        super().__init__()
        self.setObjectName("tarjeta")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(0)
        self.lbl_etiqueta = QLabel(etiqueta)
        self.lbl_etiqueta.setObjectName("etiquetaDato")
        self.lbl_valor = QLabel("—")
        self.lbl_valor.setObjectName("valorDatoAcento" if acento else "valorDato")
        self.lbl_detalle = QLabel("")
        self.lbl_detalle.setObjectName("detalleDato")
        for w in (self.lbl_etiqueta, self.lbl_valor, self.lbl_detalle):
            lay.addWidget(w)

    def mostrar(self, valor: str, detalle: str = "") -> None:
        self.lbl_valor.setText(valor)
        self.lbl_detalle.setText(detalle)


class PanelGuia(QWidget):
    filaElegida = Signal(object)
    copiarPedido = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("panelGuia")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumWidth(290)
        self._figura: Figura | None = None
        self._sincronizando = False
        self.modelo = ModeloFilas()

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 16)
        lay.setSpacing(10)
        titulo = QLabel("Construcción")
        titulo.setObjectName("tituloPanel")
        self.lbl_descripcion = QLabel()
        self.lbl_descripcion.setObjectName("ayuda")
        self.lbl_descripcion.setWordWrap(True)
        lay.addWidget(titulo)
        lay.addWidget(self.lbl_descripcion)
        lay.addLayout(self._crear_datos())
        lay.addWidget(self._crear_detalles())
        lay.addWidget(self._crear_tabla(), 1)
        lay.addLayout(self._crear_navegacion())
        self.lbl_fila = QLabel(AYUDA_FILA)
        self.lbl_fila.setObjectName("infoFila")
        self.lbl_fila.setWordWrap(True)
        self.lbl_fila.setTextFormat(Qt.TextFormat.RichText)
        lay.addWidget(self.lbl_fila)
        self.btn_copiar = QPushButton("Copiar instrucciones")
        self.btn_copiar.setObjectName("primario")
        self.btn_copiar.setIcon(recursos.icono("copiar"))
        self.btn_copiar.setToolTip("Copia al portapapeles la guía completa por filas (Ctrl+Shift+C)")
        self.btn_copiar.clicked.connect(self.copiarPedido)
        lay.addWidget(self.btn_copiar)

    def _crear_datos(self) -> QGridLayout:
        rejilla = QGridLayout()
        rejilla.setSpacing(8)
        self.dato_ancho = _Dato("Ancho")
        self.dato_alto = _Dato("Alto")
        self.dato_total = _Dato("Bloques necesarios", acento=True)
        rejilla.addWidget(self.dato_ancho, 0, 0)
        rejilla.addWidget(self.dato_alto, 0, 1)
        rejilla.addWidget(self.dato_total, 1, 0, 1, 2)
        return rejilla

    def _crear_detalles(self) -> QLabel:
        self.lbl_detalles = QLabel()
        self.lbl_detalles.setObjectName("infoFila")
        self.lbl_detalles.setWordWrap(True)
        self.lbl_detalles.setTextFormat(Qt.TextFormat.RichText)
        return self.lbl_detalles

    def _crear_tabla(self) -> QWidget:
        contenedor = QWidget()
        lay = QVBoxLayout(contenedor)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        cabecera = QHBoxLayout()
        seccion = QLabel("GUÍA POR FILAS")
        seccion.setObjectName("seccion")
        self.btn_plegar = QToolButton()
        self.btn_plegar.setObjectName("herramienta")
        self.btn_plegar.setCheckable(True)
        self.btn_plegar.setChecked(True)
        self.btn_plegar.setIcon(recursos.icono("arriba"))
        self.btn_plegar.setToolTip("Plegar o desplegar la tabla de filas")
        self.btn_plegar.toggled.connect(self._plegar_tabla)
        cabecera.addWidget(seccion)
        cabecera.addStretch(1)
        cabecera.addWidget(self.btn_plegar)
        lay.addLayout(cabecera)
        self.tabla = QTableView()
        self.tabla.setModel(self.modelo)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        cabecera_tabla = self.tabla.horizontalHeader()
        cabecera_tabla.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        cabecera_tabla.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        cabecera_tabla.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.tabla.selectionModel().currentRowChanged.connect(self._al_elegir_en_tabla)
        lay.addWidget(self.tabla, 1)
        return contenedor

    def _crear_navegacion(self) -> QHBoxLayout:
        fila = QHBoxLayout()
        fila.setSpacing(6)
        self.btn_anterior = self._boton_nav("Anterior", "arriba", "Resaltar la fila anterior (↑)", -1)
        self.btn_siguiente = self._boton_nav("Siguiente", "abajo", "Resaltar la fila siguiente (↓)", 1)
        self.btn_quitar = self._boton_nav("", "quitar", "Quitar el resaltado (Esc)", None)
        self.btn_quitar.setAccessibleName("Quitar resaltado")
        fila.addWidget(self.btn_anterior, 1)
        fila.addWidget(self.btn_siguiente, 1)
        fila.addWidget(self.btn_quitar)
        return fila

    def _boton_nav(self, texto: str, icono: str, consejo: str, delta: int | None) -> QPushButton:
        boton = QPushButton(texto)
        boton.setIcon(recursos.icono(icono))
        boton.setToolTip(consejo)
        boton.clicked.connect(lambda: self._navegar(delta))
        return boton

    def set_figura(self, figura: Figura | None) -> None:
        self._figura = figura
        self._sincronizando = True
        self.modelo.set_figura(figura)
        self._sincronizando = False
        for w in (self.btn_copiar, self.btn_anterior, self.btn_siguiente, self.btn_quitar):
            w.setEnabled(figura is not None)
        if figura is None:
            for dato in (self.dato_ancho, self.dato_alto, self.dato_total):
                dato.mostrar("—")
            self.lbl_descripcion.setText("Sin figura: corrige el tamaño.")
            self.lbl_detalles.setText("")
            self.lbl_fila.setText(AYUDA_FILA)
            return
        datos = resumen(figura)
        self.lbl_descripcion.setText(descripcion(figura.config))
        self.dato_ancho.mostrar(f"{figura.ancho}", f"teórico {formato_num(figura.ancho_teorico)}")
        self.dato_alto.mostrar(f"{figura.alto}", f"teórico {formato_num(figura.alto_teorico)}")
        self.dato_total.mostrar(f"{figura.total:,}".replace(",", "."), "bloques en este modo")
        detalles = [f"<b>Centro:</b> {datos['Centro']}"]
        for clave in ("Lado superior", "Lados verticales"):
            if clave in datos:
                detalles.append(f"<b>{clave}:</b> {datos[clave]}")
        self.lbl_detalles.setText("<br>".join(detalles))

    def seleccionar_fila(self, fila: int | None) -> None:
        self._sincronizando = True
        try:
            if fila is None:
                self.tabla.clearSelection()
                self.tabla.setCurrentIndex(QModelIndex())
            else:
                indice = self.modelo.index(fila, 0)
                self.tabla.setCurrentIndex(indice)
                self.tabla.selectRow(fila)
                self.tabla.scrollTo(indice, QAbstractItemView.ScrollHint.EnsureVisible)
        finally:
            self._sincronizando = False
        self._describir_fila(fila)

    def _describir_fila(self, fila: int | None) -> None:
        if fila is None or self._figura is None:
            self.lbl_fila.setText(AYUDA_FILA)
            return
        guia = filas_guia(self._figura)[fila]
        plural = "s" if guia.bloques != 1 else ""
        self.lbl_fila.setText(
            f"<b>Fila {guia.fila} de {self._figura.alto}</b>: {guia.bloques} bloque{plural} — "
            f"{texto_tramos_largo(guia.tramos)}"
        )

    def _al_elegir_en_tabla(self, actual: QModelIndex, _anterior: QModelIndex) -> None:
        if self._sincronizando:
            return
        fila = actual.row() if actual.isValid() else None
        self._describir_fila(fila)
        self.filaElegida.emit(fila)

    def _navegar(self, delta: int | None) -> None:
        if self._figura is None:
            return
        if delta is None:
            self.seleccionar_fila(None)
            self.filaElegida.emit(None)
            return
        actual = self.tabla.currentIndex().row() if self.tabla.currentIndex().isValid() else None
        if actual is None:
            nueva = 0 if delta > 0 else self._figura.alto - 1
        else:
            nueva = max(0, min(self._figura.alto - 1, actual + delta))
        self.seleccionar_fila(nueva)
        self.filaElegida.emit(nueva)

    def _plegar_tabla(self, desplegada: bool) -> None:
        self.tabla.setVisible(desplegada)
        self.btn_plegar.setIcon(recursos.icono("arriba" if desplegada else "abajo"))

    def tabla_desplegada(self) -> bool:
        return self.btn_plegar.isChecked()
