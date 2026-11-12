"""Diálogos de ayuda, atajos, información, fusión y confirmación."""

from __future__ import annotations

from enum import Enum

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QRadioButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .. import __version__
from ..documento import FUSION_BLOQUES, FUSION_SILUETA
from . import recursos, tema

ATAJOS = (
    ("Archivo", "Ctrl+N / Ctrl+O / Ctrl+S", "Nuevo / abrir / guardar"),
    ("Archivo", "Ctrl+Shift+S", "Guardar como"),
    ("Archivo", "Ctrl+E · Ctrl+Shift+E", "Exportar PNG · exportar instrucciones"),
    ("Archivo", "Ctrl+Shift+C", "Copiar instrucciones"),
    ("Edición", "Ctrl+Z · Ctrl+Y", "Deshacer · rehacer"),
    ("Edición", "Ctrl+A · Esc", "Seleccionar todo · quitar selección"),
    ("Edición", "Insert", "Añadir la figura de la plantilla en el centro de la vista"),
    ("Edición", "Ctrl+D · Supr", "Duplicar · eliminar"),
    ("Edición", "Ctrl+G · Ctrl+Shift+G", "Agrupar · desagrupar"),
    ("Edición", "Ctrl+M · Ctrl+Shift+M", "Fusionar · separar figura compuesta"),
    ("Edición", "Ctrl+] · Ctrl+[", "Subir · bajar en el orden de apilado"),
    ("Edición", "Flechas · Mayús+flechas", "Mover la selección 1 bloque · 16 bloques (un chunk)"),
    ("Herramientas", "V / H / A", "Seleccionar / mover vista / añadir figura"),
    ("Herramientas", "Espacio + arrastrar", "Mover la vista con cualquier herramienta"),
    ("Figura", "Ctrl+1 / Ctrl+2 / Ctrl+3", "Hexágono / círculo / triángulo"),
    ("Figura", "Ctrl+L · Ctrl+T", "Ir al tamaño · alternar contorno y relleno"),
    ("Vista", "Ctrl++ / Ctrl+- / Ctrl+0", "Acercar / alejar / ajustar al diseño"),
    ("Vista", "C", "Centrar en la selección (o en el origen)"),
    ("Vista", "G / K / N / X", "Cuadrícula / chunks / coordenadas / ejes y origen"),
    ("Vista", "Ctrl+B", "Mostrar u ocultar el panel derecho"),
    ("Guía", "Alt+↑ / Alt+↓", "Fila anterior / siguiente de la guía"),
    ("Ayuda", "F1 · Ctrl+/", "Ayuda · esta lista de atajos"),
)

TEXTO_AYUDA = """
<h3>Mundo y chunks</h3>
<p>Cada celda es un bloque. La vista es desde arriba: <b>X</b> crece hacia el este (derecha) y
<b>Z</b> hacia el sur (abajo). Los chunks miden 16 × 16 bloques y están anclados al mundo: el
chunk (0, 0) contiene X 0…15 y Z 0…15, y el bloque X −1 pertenece al chunk −1 con posición
local 15.</p>
<h3>Cómo se miden las figuras</h3>
<ul>
<li><b>Círculo:</b> diámetro = ancho = largo.</li>
<li><b>Triángulo:</b> ancho de la base; la altura es base × √3/2.</li>
<li><b>Hexágono, lado plano arriba:</b> ancho de vértice a vértice; largo = ancho × √3/2.</li>
<li><b>Hexágono, vértice arriba:</b> ancho de lado plano a lado plano; largo = ancho × 2/√3.</li>
</ul>
<p>Un bloque forma parte de una figura si el <i>centro</i> de su celda queda dentro de la figura
geométrica exacta.</p>
<h3>Varias figuras</h3>
<p><b>Agrupar</b> mantiene las figuras independientes y las mueve juntas. <b>Fusionar</b> crea una
figura compuesta: <i>conservar los bloques</i> une exactamente los bloques actuales;
<i>silueta conjunta</i> une las áreas rellenas y genera un único contorno (sin líneas internas)
o relleno. Los huecos que deja la unión siguen vacíos y su borde forma parte del contorno. Las
figuras separadas no se conectan. La compuesta guarda sus figuras de origen y se puede separar.</p>
<p>Un bloque compartido cuenta una sola vez. Su color es el del objeto que está más arriba en
la lista de objetos. Las figuras ocultas no cuentan ni se exportan; las bloqueadas sí cuentan.</p>
<p>La selección, el cursor, los ejes y el resaltado de fila son ayudas visuales: no son bloques
y no aparecen al exportar.</p>
"""


class Decision(Enum):
    GUARDAR = "guardar"
    DESCARTAR = "descartar"
    CANCELAR = "cancelar"


def preguntar_cambios(padre: QWidget, nombre: str, puede_guardar: bool) -> Decision:
    caja = QMessageBox(padre)
    caja.setIcon(QMessageBox.Icon.Warning)
    caja.setWindowTitle("Cambios sin guardar")
    caja.setText(f"«{nombre}» tiene cambios sin guardar.")
    if puede_guardar:
        caja.setInformativeText("¿Quieres guardarlos antes de continuar?")
    else:
        caja.setInformativeText(
            "No se puede guardar porque el tamaño no es válido. Puedes descartar los cambios o "
            "cancelar y corregir el tamaño."
        )
    guardar = caja.addButton("Guardar", QMessageBox.ButtonRole.AcceptRole) if puede_guardar else None
    descartar = caja.addButton("Descartar cambios", QMessageBox.ButtonRole.DestructiveRole)
    cancelar = caja.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
    caja.setDefaultButton(guardar or cancelar)
    caja.setEscapeButton(cancelar)
    caja.exec()
    pulsado = caja.clickedButton()
    if guardar is not None and pulsado is guardar:
        return Decision.GUARDAR
    if pulsado is descartar:
        return Decision.DESCARTAR
    return Decision.CANCELAR


def mostrar_ayuda(padre: QWidget) -> None:
    caja = QMessageBox(padre)
    caja.setWindowTitle(f"Ayuda de {tema.NOMBRE_APP}")
    caja.setTextFormat(Qt.TextFormat.RichText)
    caja.setText(TEXTO_AYUDA)
    caja.exec()


def mostrar_acerca_de(padre: QWidget) -> None:
    dialogo = QDialog(padre)
    dialogo.setWindowTitle(f"Acerca de {tema.NOMBRE_APP}")
    lay = QVBoxLayout(dialogo)
    lay.setContentsMargins(24, 20, 24, 16)
    lay.setSpacing(12)
    cabecera = QHBoxLayout()
    logo = QLabel()
    logo.setPixmap(recursos.logo(72))
    nombre = QLabel(
        f"<span style='font-size:20pt; font-weight:700'>{tema.NOMBRE_APP}</span><br>"
        f"<span style='color:{tema.TEXTO_SECUNDARIO}'>{tema.LEMA} · versión {__version__}</span>"
    )
    cabecera.addWidget(logo)
    cabecera.addSpacing(12)
    cabecera.addWidget(nombre, 1)
    lay.addLayout(cabecera)
    texto = QLabel(
        "Genera círculos, triángulos equiláteros y hexágonos regulares hechos con bloques "
        "cuadrados, con una guía fila a fila para construirlos.<br><br>"
        "Funciona sin conexión. Las figuras son aproximaciones discretas de formas regulares."
    )
    texto.setWordWrap(True)
    lay.addWidget(texto)
    botones = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
    botones.button(QDialogButtonBox.StandardButton.Close).setText("Cerrar")
    botones.rejected.connect(dialogo.reject)
    lay.addWidget(botones)
    dialogo.setMinimumWidth(460)
    dialogo.exec()


def mostrar_atajos(padre: QWidget) -> None:
    dialogo = QDialog(padre)
    dialogo.setWindowTitle("Atajos de teclado")
    lay = QVBoxLayout(dialogo)
    tabla = QTableWidget(len(ATAJOS), 3)
    tabla.setHorizontalHeaderLabels(("Grupo", "Teclas", "Acción"))
    tabla.verticalHeader().setVisible(False)
    tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    tabla.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
    tabla.setAlternatingRowColors(True)
    for fila, valores in enumerate(ATAJOS):
        for columna, valor in enumerate(valores):
            tabla.setItem(fila, columna, QTableWidgetItem(valor))
    cabecera = tabla.horizontalHeader()
    cabecera.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
    cabecera.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
    cabecera.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
    lay.addWidget(tabla)
    botones = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
    botones.button(QDialogButtonBox.StandardButton.Close).setText("Cerrar")
    botones.rejected.connect(dialogo.reject)
    lay.addWidget(botones)
    dialogo.resize(640, 560)
    dialogo.exec()


class DialogoFusion(QDialog):
    """Pide cómo combinar la selección en una figura compuesta."""

    def __init__(self, padre: QWidget, cantidad: int, nombre_sugerido: str) -> None:
        super().__init__(padre)
        self.setWindowTitle("Fusionar figuras")
        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        lay.addWidget(QLabel(f"Se combinarán <b>{cantidad} figuras</b> en una figura compuesta. "
                             "Las originales se conservan dentro de ella y se pueden recuperar con "
                             "«Separar»."))
        self.opcion_bloques = QRadioButton("Conservar los bloques")
        self.opcion_silueta = QRadioButton("Crear silueta conjunta")
        grupo = QButtonGroup(self)
        for opcion in (self.opcion_silueta, self.opcion_bloques):
            grupo.addButton(opcion)
        self.opcion_silueta.setChecked(True)
        lay.addWidget(self.opcion_silueta)
        lay.addWidget(_explicacion("Une las áreas rellenas de las figuras. En contorno queda un solo borde, "
                                   "sin las líneas internas donde se solapan. Los huecos que deje la unión "
                                   "siguen vacíos y conservan su borde."))
        fila = QHBoxLayout()
        fila.addSpacing(24)
        fila.addWidget(QLabel("Resultado:"))
        self.modo = QComboBox()
        self.modo.addItem("Contorno", "contorno")
        self.modo.addItem("Relleno", "relleno")
        fila.addWidget(self.modo, 1)
        lay.addLayout(fila)
        lay.addWidget(self.opcion_bloques)
        lay.addWidget(_explicacion("Unión exacta de los bloques que ocupan ahora las figuras, tal como se "
                                   "ven (contornos internos incluidos)."))
        lay.addWidget(_explicacion("En ambos casos, las figuras separadas no se conectan y cada bloque "
                                   "compartido cuenta una sola vez."))
        self.opcion_silueta.toggled.connect(self.modo.setEnabled)
        formulario = QFormLayout()
        self.nombre = QLineEdit(nombre_sugerido)
        formulario.addRow("Nombre:", self.nombre)
        lay.addLayout(formulario)
        botones = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        aceptar = botones.button(QDialogButtonBox.StandardButton.Ok)
        aceptar.setText("Fusionar")
        aceptar.setObjectName("primario")
        botones.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        lay.addWidget(botones)
        self.setMinimumWidth(480)

    def resultado(self) -> tuple[str, str, str]:
        fusion = FUSION_SILUETA if self.opcion_silueta.isChecked() else FUSION_BLOQUES
        return fusion, self.modo.currentData(), self.nombre.text().strip()


def _explicacion(texto: str) -> QLabel:
    etiqueta = QLabel(texto)
    etiqueta.setObjectName("ayuda")
    etiqueta.setWordWrap(True)
    etiqueta.setContentsMargins(24, 0, 0, 0)
    return etiqueta
