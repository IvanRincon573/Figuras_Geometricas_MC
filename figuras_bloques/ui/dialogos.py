"""Diálogos de ayuda, atajos, información y confirmación."""

from __future__ import annotations

from enum import Enum

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .. import __version__
from . import recursos, tema

ATAJOS = (
    ("Archivo", "Ctrl+N", "Nuevo diseño"),
    ("Archivo", "Ctrl+O", "Abrir diseño"),
    ("Archivo", "Ctrl+S", "Guardar"),
    ("Archivo", "Ctrl+Shift+S", "Guardar como"),
    ("Archivo", "Ctrl+E", "Exportar PNG"),
    ("Archivo", "Ctrl+Shift+C", "Copiar instrucciones"),
    ("Figura", "Ctrl+1 / Ctrl+2 / Ctrl+3", "Hexágono / círculo / triángulo"),
    ("Figura", "Ctrl+L", "Ir al campo de tamaño"),
    ("Figura", "Ctrl+T", "Alternar contorno y relleno"),
    ("Vista", "Ctrl++ / Ctrl+-", "Acercar / alejar"),
    ("Vista", "Ctrl+0", "Ajustar a la ventana"),
    ("Vista", "Ctrl+B", "Mostrar u ocultar la guía de construcción"),
    ("Cuadrícula", "F / C", "Ajustar / centrar (con la cuadrícula activa)"),
    ("Cuadrícula", "G / X / M / N", "Cuadrícula / ejes / marca del centro / numeración"),
    ("Cuadrícula", "↑ / ↓ · Esc", "Fila anterior o siguiente · quitar resaltado"),
    ("Cuadrícula", "Rueda · arrastrar", "Zoom · mover la vista"),
    ("Ayuda", "F1", "Cómo se miden las figuras"),
    ("Ayuda", "Ctrl+/", "Esta lista de atajos"),
)

TEXTO_AYUDA = """
<h3>Cómo se miden las figuras</h3>
<p><b>Cada celda es un bloque.</b> Las figuras se forman solo con bloques completos.</p>
<ul>
<li><b>Círculo:</b> diámetro = ancho = alto.</li>
<li><b>Triángulo:</b> ancho de la base; la altura es base × √3/2.</li>
<li><b>Hexágono, lado plano arriba:</b> ancho de vértice a vértice; alto = ancho × √3/2.</li>
<li><b>Hexágono, vértice arriba:</b> ancho de lado plano a lado plano; alto = ancho × 2/√3.</li>
</ul>
<p><b>Qué bloques forman la figura:</b> se coloca la figura geométrica exacta sobre la
cuadrícula y se toma cada bloque cuyo <i>centro</i> queda dentro. El alto se redondea
eligiendo la colocación que más se acerca al valor teórico.</p>
<p><b>Centro:</b> con tamaño impar hay una columna central; con tamaño par el centro cae en
la línea entre dos columnas (igual con las filas).</p>
<p><b>Contorno:</b> son los bloques de la figura rellena que tocan el exterior por un lado;
en los escalones se unen en diagonal.</p>
<p>Los ejes, la marca del centro y el resaltado de fila son ayudas visuales: no cuentan
como bloques.</p>
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
