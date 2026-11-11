"""Exportación de la figura a PNG."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..geometria import Figura
from .render import OpcionesDibujo, dibujar_figura
from .tema import LIENZO_CLARO, LIENZO_OSCURO

LADO_MAXIMO_PX = 20_000
FONDOS = (("Claro", "claro"), ("Oscuro", "oscuro"), ("Transparente", "transparente"))


def margen_bloques(numeros: bool) -> int:
    return 3 if numeros else 1


def renderizar_png(figura: Figura, px: int, cuadricula: bool, numeros: bool, fondo: str = "claro") -> QImage:
    """Imagen de la figura sin ejes, centro ni resaltados."""
    m = margen_bloques(numeros)
    ancho, alto = (figura.ancho + 2 * m) * px, (figura.alto + 2 * m) * px
    imagen = QImage(ancho, alto, QImage.Format.Format_ARGB32_Premultiplied)
    imagen.fill(Qt.GlobalColor.transparent)
    opciones = OpcionesDibujo(
        cuadricula=cuadricula,
        ejes=False,
        centro=False,
        numeros=numeros,
        marco=False,
        paleta=LIENZO_OSCURO if fondo == "oscuro" else LIENZO_CLARO,
        rellenar_fondo=fondo != "transparente",
    )
    p = QPainter(imagen)
    dibujar_figura(p, figura, px, QPointF(m * px, m * px), QRectF(0, 0, ancho, alto), opciones)
    p.end()
    return imagen


class DialogoPNG(QDialog):
    def __init__(self, parent: QWidget, figura: Figura, cuadricula: bool, fondo: str) -> None:
        super().__init__(parent)
        self.setWindowTitle("Exportar imagen PNG")
        self.figura = figura
        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        formulario = QFormLayout()
        self.px = QSpinBox()
        self.px.setRange(2, 64)
        self.px.setValue(20 if max(figura.ancho, figura.alto) <= 200 else 8)
        self.px.setSuffix(" px por bloque")
        self.px.setToolTip("Tamaño en píxeles de cada bloque en la imagen")
        formulario.addRow("Tamaño de cada bloque:", self.px)
        self.fondo = QComboBox()
        for texto, clave in FONDOS:
            self.fondo.addItem(texto, clave)
        self.fondo.setCurrentIndex(max(0, self.fondo.findData(fondo)))
        formulario.addRow("Fondo:", self.fondo)
        lay.addLayout(formulario)
        self.cuadricula = QCheckBox("Incluir cuadrícula")
        self.cuadricula.setChecked(cuadricula)
        self.numeros = QCheckBox("Incluir numeración de filas y columnas")
        lay.addWidget(self.cuadricula)
        lay.addWidget(self.numeros)
        self.info = QLabel()
        self.info.setObjectName("ayuda")
        self.info.setWordWrap(True)
        lay.addWidget(self.info)
        botones = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self.btn_guardar = botones.button(QDialogButtonBox.StandardButton.Save)
        self.btn_guardar.setText("Elegir destino…")
        self.btn_guardar.setObjectName("primario")
        botones.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        lay.addWidget(botones)
        self.px.valueChanged.connect(self._actualizar_info)
        self.numeros.toggled.connect(self._actualizar_info)
        self._actualizar_info()

    def tamano_imagen(self) -> tuple[int, int]:
        m = margen_bloques(self.numeros.isChecked())
        s = self.px.value()
        return (self.figura.ancho + 2 * m) * s, (self.figura.alto + 2 * m) * s

    def _actualizar_info(self) -> None:
        ancho, alto = self.tamano_imagen()
        valido = max(ancho, alto) <= LADO_MAXIMO_PX
        texto = f"La imagen medirá {ancho} × {alto} píxeles."
        if not valido:
            texto += f" Supera el máximo de {LADO_MAXIMO_PX:,} px por lado: reduce los píxeles por bloque.".replace(",", ".")
        self.info.setText(texto)
        self.btn_guardar.setEnabled(valido)

    def opciones(self) -> dict:
        return {
            "px": self.px.value(),
            "cuadricula": self.cuadricula.isChecked(),
            "numeros": self.numeros.isChecked(),
            "fondo": self.fondo.currentData(),
        }
