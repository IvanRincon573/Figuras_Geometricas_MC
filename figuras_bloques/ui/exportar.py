"""Exportación de imágenes PNG e instrucciones de texto, independientes de la vista."""

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

from ..construccion import Construccion
from .render import OpcionesDibujo, Vista, alto_regla, dibujar_mundo
from .tema import LIENZO_CLARO, LIENZO_OSCURO

LADO_MAXIMO_PX = 20_000
MARGEN_BLOQUES = 2
FONDOS = (("Claro", "claro"), ("Oscuro", "oscuro"), ("Transparente", "transparente"))
AMBITOS = (("Diseño completo", "diseno"), ("Selección", "seleccion"))


def geometria_png(c: Construccion, px: int, coordenadas: bool) -> tuple[int, int, QPointF]:
    """Tamaño de la imagen y posición en píxeles del punto (0, 0) del mundo."""
    x0, z0, x1, z1 = c.limites
    regla = alto_regla(1.0) if coordenadas else 0
    izquierda = MARGEN_BLOQUES * px + regla * 2.2
    arriba = MARGEN_BLOQUES * px + regla
    ancho = round(izquierda + (x1 - x0 + 1 + MARGEN_BLOQUES) * px)
    alto = round(arriba + (z1 - z0 + 1 + MARGEN_BLOQUES) * px)
    return ancho, alto, QPointF(izquierda - x0 * px, arriba - z0 * px)


def renderizar_png(c: Construccion, px: int, cuadricula: bool = True, chunks: bool = True,
                   coordenadas: bool = False, fondo: str = "claro") -> QImage:
    """Imagen del resultado de construcción, sin selección ni cursor."""
    ancho, alto, origen = geometria_png(c, px, coordenadas)
    imagen = QImage(ancho, alto, QImage.Format.Format_ARGB32_Premultiplied)
    imagen.fill(Qt.GlobalColor.transparent)
    opciones = OpcionesDibujo(
        cuadricula=cuadricula, chunks=chunks, coordenadas=coordenadas, ejes=False,
        paleta=LIENZO_OSCURO if fondo == "oscuro" else LIENZO_CLARO,
        rellenar_fondo=fondo != "transparente",
    )
    p = QPainter(imagen)
    dibujar_mundo(p, c, Vista(px, origen, 1.0), QRectF(0, 0, ancho, alto), opciones)
    p.end()
    return imagen


def _combo(opciones, actual: str) -> QComboBox:
    combo = QComboBox()
    for texto, clave in opciones:
        combo.addItem(texto, clave)
    combo.setCurrentIndex(max(0, combo.findData(actual)))
    return combo


def _botones(dialogo: QDialog, texto: str) -> QDialogButtonBox:
    botones = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
    aceptar = botones.button(QDialogButtonBox.StandardButton.Save)
    aceptar.setText(texto)
    aceptar.setObjectName("primario")
    botones.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
    botones.accepted.connect(dialogo.accept)
    botones.rejected.connect(dialogo.reject)
    return botones


class DialogoPNG(QDialog):
    def __init__(self, parent: QWidget, completa: Construccion, seleccion: Construccion | None,
                 preferencias: dict) -> None:
        super().__init__(parent)
        self.setWindowTitle("Exportar imagen PNG")
        self._completa, self._seleccion = completa, seleccion
        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        formulario = QFormLayout()
        self.ambito = _combo(AMBITOS, "seleccion" if seleccion is not None and not seleccion.vacia else "diseno")
        self.ambito.model().item(1).setEnabled(seleccion is not None and not seleccion.vacia)
        self.px = QSpinBox()
        self.px.setRange(2, 64)
        self.px.setSuffix(" px por bloque")
        self.px.setValue(20 if max(completa.ancho, completa.largo) <= 200 else 6)
        self.fondo = _combo(FONDOS, preferencias.get("fondo", "claro"))
        formulario.addRow("Contenido:", self.ambito)
        formulario.addRow("Tamaño de cada bloque:", self.px)
        formulario.addRow("Fondo:", self.fondo)
        lay.addLayout(formulario)
        self.cuadricula = QCheckBox("Cuadrícula de bloques")
        self.chunks = QCheckBox("Límites de chunks")
        self.coordenadas = QCheckBox("Coordenadas X y Z en los bordes")
        for casilla, clave in ((self.cuadricula, "cuadricula"), (self.chunks, "chunks"),
                               (self.coordenadas, "coordenadas")):
            casilla.setChecked(bool(preferencias.get(clave, True)))
            casilla.toggled.connect(self._actualizar_info)
            lay.addWidget(casilla)
        self.info = QLabel()
        self.info.setObjectName("ayuda")
        self.info.setWordWrap(True)
        lay.addWidget(self.info)
        botones = _botones(self, "Elegir destino…")
        self.btn_guardar = botones.button(QDialogButtonBox.StandardButton.Save)
        lay.addWidget(botones)
        self.px.valueChanged.connect(self._actualizar_info)
        self.ambito.currentIndexChanged.connect(self._actualizar_info)
        self._actualizar_info()

    def construccion(self) -> Construccion:
        return self._seleccion if self.ambito.currentData() == "seleccion" else self._completa

    def _actualizar_info(self) -> None:
        c = self.construccion()
        ancho, alto, _ = geometria_png(c, self.px.value(), self.coordenadas.isChecked())
        valido = max(ancho, alto) <= LADO_MAXIMO_PX
        texto = (f"{c.total} bloques en {len(c.por_chunk)} chunks. "
                 f"La imagen medirá {ancho} × {alto} píxeles, sin importar el zoom de la vista.")
        if not valido:
            texto += f" Supera el máximo de {LADO_MAXIMO_PX:,} px por lado: reduce los píxeles por bloque.".replace(",", ".")
        self.info.setText(texto)
        self.btn_guardar.setEnabled(valido)

    def opciones(self) -> dict:
        return {
            "px": self.px.value(), "cuadricula": self.cuadricula.isChecked(), "chunks": self.chunks.isChecked(),
            "coordenadas": self.coordenadas.isChecked(), "fondo": self.fondo.currentData(),
        }


class DialogoInstrucciones(QDialog):
    def __init__(self, parent: QWidget, hay_seleccion: bool) -> None:
        super().__init__(parent)
        self.setWindowTitle("Exportar instrucciones")
        lay = QVBoxLayout(self)
        formulario = QFormLayout()
        self.ambito = _combo(AMBITOS, "seleccion" if hay_seleccion else "diseno")
        self.ambito.model().item(1).setEnabled(hay_seleccion)
        self.tipo = _combo((("Completas, fila a fila", "completa"), ("Agrupadas por chunk", "chunks")), "completa")
        formulario.addRow("Contenido:", self.ambito)
        formulario.addRow("Formato:", self.tipo)
        lay.addLayout(formulario)
        ayuda = QLabel("Por chunk: cada chunk con sus filas en coordenadas globales y locales (0–15), "
                       "útil para construir chunk a chunk con la pantalla F3.")
        ayuda.setObjectName("ayuda")
        ayuda.setWordWrap(True)
        lay.addWidget(ayuda)
        lay.addWidget(_botones(self, "Elegir destino…"))
