"""Panel de construcción: conteo, chunks ocupados y guía por filas en coordenadas globales."""

from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QPushButton,
    QSplitter,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from ..chunks import limites_chunk
from ..construccion import Construccion, FilaGuia, filas_guia, texto_tramos
from . import recursos

DISENO, SELECCION = "diseno", "seleccion"


class ModeloChunks(QAbstractTableModel):
    CABECERAS = ("Chunk", "X", "Z", "Bloques")

    def __init__(self) -> None:
        super().__init__()
        self._filas: list[tuple[tuple[int, int], int]] = []

    def set_construccion(self, c: Construccion) -> None:
        self.beginResetModel()
        self._filas = list(c.por_chunk.items())
        self.endResetModel()

    def chunk(self, fila: int) -> tuple[int, int]:
        return self._filas[fila][0]

    def rowCount(self, parent=QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._filas)

    def columnCount(self, parent=QModelIndex()) -> int:  # noqa: N802
        return len(self.CABECERAS)

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        (cx, cz), bloques = self._filas[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            x0, z0, x1, z1 = limites_chunk(cx, cz)
            return (f"{cx}, {cz}", f"{x0}…{x1}", f"{z0}…{z1}", str(bloques))[index.column()]
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return int(Qt.AlignmentFlag.AlignCenter)
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):  # noqa: N802
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self.CABECERAS[section]
        return None


class ModeloFilas(QAbstractTableModel):
    CABECERAS = ("Z", "Bloques", "Tramos en X (inicio–fin)")

    def __init__(self) -> None:
        super().__init__()
        self._filas: list[FilaGuia] = []
        self._con_color = False

    def set_construccion(self, c: Construccion) -> None:
        self.beginResetModel()
        self._filas = filas_guia(c)
        self._con_color = len(c.por_color) > 1
        self.endResetModel()

    def z(self, fila: int) -> int:
        return self._filas[fila].z

    def guia(self, fila: int) -> FilaGuia:
        return self._filas[fila]

    def fila_de_z(self, z: int) -> int | None:
        return next((i for i, f in enumerate(self._filas) if f.z == z), None)

    def rowCount(self, parent=QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._filas)

    def columnCount(self, parent=QModelIndex()) -> int:  # noqa: N802
        return len(self.CABECERAS)

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        fila = self._filas[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            return (str(fila.z), str(fila.bloques), texto_tramos(fila.tramos, False).replace(", ", "   |   "))[
                index.column()]
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return int(Qt.AlignmentFlag.AlignCenter if index.column() < 2
                       else Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        if role == Qt.ItemDataRole.ToolTipRole:
            return f"Z {fila.z}: {fila.bloques} bloques — X {texto_tramos(fila.tramos, self._con_color)}"
        if role == Qt.ItemDataRole.DecorationRole and index.column() == 2 and self._con_color:
            return QColor(fila.tramos[0][2])
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):  # noqa: N802
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self.CABECERAS[section]
        return None


class _Dato(QFrame):
    def __init__(self, etiqueta: str, acento: bool = False) -> None:
        super().__init__()
        self.setObjectName("tarjeta")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 6, 10, 6)
        lay.setSpacing(0)
        self.lbl_etiqueta = QLabel(etiqueta)
        self.lbl_etiqueta.setObjectName("etiquetaDato")
        self.lbl_valor = QLabel("—")
        self.lbl_valor.setObjectName("valorDatoAcento" if acento else "valorDato")
        lay.addWidget(self.lbl_etiqueta)
        lay.addWidget(self.lbl_valor)

    def mostrar(self, valor: str) -> None:
        self.lbl_valor.setText(valor)


def _tabla(modelo) -> QTableView:
    tabla = QTableView()
    tabla.setModel(modelo)
    tabla.setAlternatingRowColors(True)
    tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    tabla.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    tabla.verticalHeader().setVisible(False)
    tabla.verticalHeader().setDefaultSectionSize(24)
    cabecera = tabla.horizontalHeader()
    for columna in range(modelo.columnCount() - 1):
        cabecera.setSectionResizeMode(columna, QHeaderView.ResizeMode.ResizeToContents)
    cabecera.setSectionResizeMode(modelo.columnCount() - 1, QHeaderView.ResizeMode.Stretch)
    return tabla


class PanelConstruccion(QWidget):
    ambitoCambiado = Signal(str)
    chunkElegido = Signal(object)
    filaElegida = Signal(object)
    copiarPedido = Signal(str)
    exportarPedido = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._completa = None
        self.setObjectName("panelGuia")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._chunk: tuple[int, int] | None = None
        self._sincronizando = False
        self.modelo_chunks = ModeloChunks()
        self.modelo_filas = ModeloFilas()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)
        fila_ambito = QHBoxLayout()
        etiqueta = QLabel("Calcular para:")
        self.combo_ambito = QComboBox()
        self.combo_ambito.addItem("Diseño completo", DISENO)
        self.combo_ambito.addItem("Selección", SELECCION)
        self.combo_ambito.setToolTip("Conteo e instrucciones de todo el diseño visible o solo de lo seleccionado")
        etiqueta.setBuddy(self.combo_ambito)
        self.combo_ambito.currentIndexChanged.connect(lambda _i: self.ambitoCambiado.emit(self.ambito()))
        fila_ambito.addWidget(etiqueta)
        fila_ambito.addWidget(self.combo_ambito, 1)
        lay.addLayout(fila_ambito)
        lay.addLayout(self._crear_datos())
        self.lbl_extension = QLabel()
        self.lbl_extension.setObjectName("infoFila")
        self.lbl_extension.setWordWrap(True)
        lay.addWidget(self.lbl_extension)
        lay.addWidget(self._crear_tablas(), 1)
        self.lbl_fila = QLabel()
        self.lbl_fila.setObjectName("infoFila")
        self.lbl_fila.setWordWrap(True)
        self.lbl_fila.setTextFormat(Qt.TextFormat.RichText)
        lay.addWidget(self.lbl_fila)
        lay.addLayout(self._crear_botones())

    def _crear_datos(self) -> QGridLayout:
        rejilla = QGridLayout()
        rejilla.setSpacing(6)
        self.dato_total = _Dato("Bloques únicos", acento=True)
        self.dato_medidas = _Dato("X × Z")
        self.dato_chunks = _Dato("Chunks")
        rejilla.addWidget(self.dato_total, 0, 0, 1, 2)
        rejilla.addWidget(self.dato_medidas, 1, 0)
        rejilla.addWidget(self.dato_chunks, 1, 1)
        return rejilla

    def _crear_tablas(self) -> QSplitter:
        divisor = QSplitter(Qt.Orientation.Vertical)
        divisor.setChildrenCollapsible(False)
        caja_chunks = QWidget()
        lay = QVBoxLayout(caja_chunks)
        lay.setContentsMargins(0, 0, 0, 0)
        cabecera = QLabel("CHUNKS OCUPADOS")
        cabecera.setObjectName("seccion")
        lay.addWidget(cabecera)
        self.tabla_chunks = _tabla(self.modelo_chunks)
        self.tabla_chunks.setToolTip("Clic: mostrar ese chunk y filtrar la guía por filas")
        self.tabla_chunks.selectionModel().currentRowChanged.connect(self._al_elegir_chunk)
        lay.addWidget(self.tabla_chunks)
        caja_filas = QWidget()
        lay = QVBoxLayout(caja_filas)
        lay.setContentsMargins(0, 0, 0, 0)
        fila = QHBoxLayout()
        self.lbl_filas = QLabel("GUÍA POR FILAS")
        self.lbl_filas.setObjectName("seccion")
        self.btn_todos = QPushButton("Ver todos los chunks")
        self.btn_todos.setToolTip("Quitar el filtro por chunk")
        self.btn_todos.clicked.connect(self._quitar_filtro)
        fila.addWidget(self.lbl_filas, 1)
        fila.addWidget(self.btn_todos)
        lay.addLayout(fila)
        self.tabla_filas = _tabla(self.modelo_filas)
        self.tabla_filas.setToolTip("Clic: resaltar la fila en la cuadrícula. Alt+↑/↓ cambia de fila.")
        self.tabla_filas.selectionModel().currentRowChanged.connect(self._al_elegir_fila)
        lay.addWidget(self.tabla_filas)
        divisor.addWidget(caja_chunks)
        divisor.addWidget(caja_filas)
        divisor.setSizes([140, 300])
        return divisor

    def _crear_botones(self) -> QHBoxLayout:
        fila = QHBoxLayout()
        fila.setSpacing(6)
        self.btn_copiar = QPushButton("Copiar instrucciones")
        self.btn_copiar.setObjectName("primario")
        self.btn_copiar.setIcon(recursos.icono("copiar"))
        self.btn_copiar.setToolTip("Copia la guía completa por filas (Ctrl+Shift+C)")
        self.btn_copiar.clicked.connect(lambda: self.copiarPedido.emit("completa"))
        self.btn_mas = QPushButton("Más")
        self.btn_mas.setIcon(recursos.icono("texto"))
        menu = QMenu(self)
        menu.addAction("Copiar instrucciones completas", lambda: self.copiarPedido.emit("completa"))
        menu.addAction("Copiar instrucciones por chunk", lambda: self.copiarPedido.emit("chunks"))
        menu.addSeparator()
        menu.addAction("Exportar instrucciones a texto…", self.exportarPedido.emit)
        self.btn_mas.setMenu(menu)
        fila.addWidget(self.btn_copiar, 1)
        fila.addWidget(self.btn_mas)
        return fila

    def ambito(self) -> str:
        return self.combo_ambito.currentData()

    def set_ambito(self, ambito: str) -> None:
        self.combo_ambito.setCurrentIndex(self.combo_ambito.findData(ambito))

    def mostrar(self, c: Construccion, hay_seleccion: bool) -> None:
        self._completa = c
        self.combo_ambito.model().item(1).setEnabled(hay_seleccion)
        self.dato_total.mostrar(f"{c.total:,}".replace(",", "."))
        self.dato_medidas.mostrar(f"{c.ancho} × {c.largo}" if not c.vacia else "—")
        self.dato_chunks.mostrar(str(len(c.por_chunk)))
        if c.vacia:
            self.lbl_extension.setText("No hay bloques visibles en este ámbito.")
        else:
            x0, z0, x1, z1 = c.limites
            self.lbl_extension.setText(f"<b>Extensión:</b> X {x0} … {x1} · Z {z0} … {z1}")
        self._sincronizando = True
        self.modelo_chunks.set_construccion(c)
        self._sincronizando = False
        if self._chunk not in c.por_chunk:
            self._chunk = None
        self._filtrar(self._chunk, emitir=False)
        for boton in (self.btn_copiar, self.btn_mas):
            boton.setEnabled(not c.vacia)

    def _filtrar(self, chunk: tuple[int, int] | None, emitir: bool = True) -> None:
        self._chunk = chunk
        c = self._completa
        if c is None:
            return
        if chunk is None:
            self.modelo_filas.set_construccion(c)
            self.lbl_filas.setText("GUÍA POR FILAS")
        else:
            self.modelo_filas.set_construccion(c.recortar(*limites_chunk(*chunk)))
            self.lbl_filas.setText(f"FILAS DEL CHUNK ({chunk[0]}, {chunk[1]})")
        self.btn_todos.setVisible(chunk is not None)
        self.lbl_fila.setText("Clic en una fila para resaltarla en la cuadrícula.")
        if emitir:
            self.chunkElegido.emit(chunk)

    def _quitar_filtro(self) -> None:
        self.tabla_chunks.clearSelection()
        self._filtrar(None)

    def _al_elegir_chunk(self, actual: QModelIndex, _anterior) -> None:
        if not self._sincronizando and actual.isValid():
            self._filtrar(self.modelo_chunks.chunk(actual.row()))

    def _al_elegir_fila(self, actual: QModelIndex, _anterior) -> None:
        if self._sincronizando:
            return
        z = self.modelo_filas.z(actual.row()) if actual.isValid() else None
        self._describir(actual.row() if actual.isValid() else None)
        self.filaElegida.emit(z)

    def _describir(self, fila: int | None) -> None:
        if fila is None:
            self.lbl_fila.setText("Clic en una fila para resaltarla en la cuadrícula.")
            return
        datos = self.modelo_filas.guia(fila)
        self.lbl_fila.setText(f"<b>Z {datos.z}</b>: {datos.bloques} bloques — X {texto_tramos(datos.tramos, False)}")

    def mover_fila(self, delta: int) -> None:
        total = self.modelo_filas.rowCount()
        if not total:
            return
        actual = self.tabla_filas.currentIndex()
        fila = (0 if delta > 0 else total - 1) if not actual.isValid() else max(0, min(total - 1, actual.row() + delta))
        self.tabla_filas.selectRow(fila)
        self.tabla_filas.setCurrentIndex(self.modelo_filas.index(fila, 0))

    def quitar_fila(self) -> None:
        self.tabla_filas.clearSelection()
        self.tabla_filas.setCurrentIndex(QModelIndex())
