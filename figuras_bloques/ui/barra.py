"""Barra de botones que oculta sus textos cuando no caben."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QFrame, QHBoxLayout, QSizePolicy, QToolButton, QWidget


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
