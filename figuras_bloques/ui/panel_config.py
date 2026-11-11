"""Panel lateral con los parámetros de la figura."""

from __future__ import annotations

import math

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QButtonGroup,
    QColorDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..geometria import (
    ORIENTACION_POR_DEFECTO,
    ORIENTACIONES,
    TAMANO_MAXIMO,
    TAMANO_MINIMO,
    Configuracion,
    Figura,
)
from ..guia import formato_num
from . import recursos

FIGURAS_UI = (
    ("hexagono", "Hexágono", "plano", "Hexágono regular (Ctrl+1)"),
    ("circulo", "Círculo", "", "Círculo (Ctrl+2)"),
    ("triangulo", "Triángulo", "arriba", "Triángulo equilátero (Ctrl+3)"),
)

ORIENTACIONES_UI = {
    "plano": ("Lado plano arriba", "Los lados planos quedan arriba y abajo; los vértices, a los lados."),
    "vertice": ("Vértice arriba", "Los vértices quedan arriba y abajo; los lados planos, a los lados."),
    "arriba": ("Arriba", "Vértice hacia arriba, base abajo."),
    "abajo": ("Abajo", "Vértice hacia abajo, base arriba."),
    "izquierda": ("Izquierda", "Vértice hacia la izquierda, base vertical a la derecha."),
    "derecha": ("Derecha", "Vértice hacia la derecha, base vertical a la izquierda."),
}

MEDIDAS_UI = {
    "circulo": ("Diámetro", "Bloques de lado a lado pasando por el centro."),
    "triangulo": ("Ancho de la base", "Bloques que ocupa la base (un lado del triángulo)."),
    "hexagono_plano": ("Ancho total", "Bloques de vértice a vértice, de izquierda a derecha."),
    "hexagono_vertice": ("Ancho total", "Bloques de lado plano a lado plano, de izquierda a derecha."),
}

COLORES = (
    ("Hierba", "#5B8C3A"),
    ("Esmeralda", "#3FC98A"),
    ("Piedra", "#8A8F96"),
    ("Madera", "#9C7246"),
    ("Ladrillo", "#B0503C"),
    ("Arena", "#D8CB95"),
    ("Agua", "#3F7FE0"),
    ("Oro", "#E3B53A"),
    ("Cuarzo", "#ECE6DA"),
    ("Amatista", "#9061C9"),
)

POSICIONES_DESLIZADOR = 1000


def tamano_desde_deslizador(posicion: int) -> int:
    """Escala cuadrática: más precisión en tamaños pequeños, alcance hasta el máximo."""
    fraccion = posicion / POSICIONES_DESLIZADOR
    return round(TAMANO_MINIMO + (TAMANO_MAXIMO - TAMANO_MINIMO) * fraccion**2)


def deslizador_desde_tamano(tamano: int) -> int:
    limitado = max(TAMANO_MINIMO, min(TAMANO_MAXIMO, tamano))
    fraccion = math.sqrt((limitado - TAMANO_MINIMO) / (TAMANO_MAXIMO - TAMANO_MINIMO))
    return round(fraccion * POSICIONES_DESLIZADOR)


def _seccion(texto: str) -> QLabel:
    etiqueta = QLabel(texto.upper())
    etiqueta.setObjectName("seccion")
    return etiqueta


def _ayuda(texto: str = "") -> QLabel:
    etiqueta = QLabel(texto)
    etiqueta.setObjectName("ayuda")
    etiqueta.setWordWrap(True)
    return etiqueta


def _boton_segmento(texto: str, consejo: str) -> QToolButton:
    boton = QToolButton()
    boton.setObjectName("segmento")
    boton.setText(texto)
    boton.setToolTip(consejo)
    boton.setCheckable(True)
    boton.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
    boton.setIconSize(QSize(18, 18))
    boton.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    return boton


class PanelConfiguracion(QScrollArea):
    """Emite ``cambiado(afecta_geometria)`` cada vez que el usuario modifica un parámetro."""

    cambiado = Signal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("desplazamientoPanel")
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setMinimumWidth(270)
        self._color = COLORES[0][1]
        self._sincronizando = False
        self._orientacion_actual: dict[str, str] = dict(ORIENTACION_POR_DEFECTO)

        contenido = QWidget()
        contenido.setObjectName("panelLateral")
        self._lay = QVBoxLayout(contenido)
        self._lay.setContentsMargins(16, 14, 16, 16)
        self._lay.setSpacing(8)
        self._crear_figura()
        self._crear_tamano()
        self._crear_orientacion()
        self._crear_proporciones()
        self._crear_modo()
        self._crear_color()
        self._lay.addStretch(1)
        self.setWidget(contenido)

    def _crear_figura(self) -> None:
        self._lay.addWidget(_seccion("Figura"))
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
        self.grupo_figura.buttonClicked.connect(lambda _b: self._al_cambiar_figura())
        self._lay.addLayout(fila)

    def _crear_tamano(self) -> None:
        self._lay.addWidget(_seccion("Tamaño"))
        self.lbl_medida = QLabel()
        self._lay.addWidget(self.lbl_medida)
        self.spin_tamano = QSpinBox()
        self.spin_tamano.setObjectName("tamano")
        # Admite valores fuera de 1-1000 para poder explicar por qué no son válidos.
        self.spin_tamano.setRange(0, 99999)
        self.spin_tamano.setSuffix(" bloques")
        self.spin_tamano.setAccelerated(True)
        self.spin_tamano.setToolTip(
            "Tamaño en bloques (1 a 1000). Flechas: ±1 · Re Pág / Av Pág: ±10 · Ctrl+L para ir aquí."
        )
        self.lbl_medida.setBuddy(self.spin_tamano)
        self._lay.addWidget(self.spin_tamano)
        self.deslizador = QSlider(Qt.Orientation.Horizontal)
        self.deslizador.setRange(0, POSICIONES_DESLIZADOR)
        self.deslizador.setPageStep(50)
        self.deslizador.setToolTip("Arrastra para cambiar el tamaño; el campo de arriba permite el valor exacto.")
        self._lay.addWidget(self.deslizador)
        self.lbl_ayuda_medida = _ayuda()
        self._lay.addWidget(self.lbl_ayuda_medida)
        self.lbl_error = QLabel()
        self.lbl_error.setObjectName("error")
        self.lbl_error.setWordWrap(True)
        self.lbl_error.hide()
        self._lay.addWidget(self.lbl_error)
        self.spin_tamano.valueChanged.connect(self._al_cambiar_spin)
        self.deslizador.valueChanged.connect(self._al_mover_deslizador)

    def _crear_orientacion(self) -> None:
        self.contenedor_orientacion = QWidget()
        lay = QVBoxLayout(self.contenedor_orientacion)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        lay.addWidget(_seccion("Orientación"))
        self.grupo_orientacion = QButtonGroup(self)
        self.botones_orientacion: dict[str, QToolButton] = {}
        self._rejilla_orientacion = QGridLayout()
        self._rejilla_orientacion.setSpacing(6)
        lay.addLayout(self._rejilla_orientacion)
        for figura in ("hexagono", "triangulo"):
            for orientacion in ORIENTACIONES[figura]:
                texto, consejo = ORIENTACIONES_UI[orientacion]
                boton = _boton_segmento(texto, consejo)
                boton.setIcon(recursos.icono_figura(figura, orientacion, lado=20))
                self.grupo_orientacion.addButton(boton)
                self.botones_orientacion[orientacion] = boton
        self.grupo_orientacion.buttonClicked.connect(lambda _b: self._al_cambiar_orientacion())
        self._lay.addWidget(self.contenedor_orientacion)

    def _crear_proporciones(self) -> None:
        self._lay.addWidget(_seccion("Proporciones"))
        self.lbl_proporciones = QLabel()
        self.lbl_proporciones.setTextFormat(Qt.TextFormat.RichText)
        self.lbl_proporciones.setWordWrap(True)
        self.lbl_proporciones.setToolTip(
            "La medida que eliges se respeta exactamente; la otra se calcula con la "
            "proporción de la figura regular y se redondea a bloques."
        )
        self._lay.addWidget(self.lbl_proporciones)
        self.lbl_paridad = _ayuda()
        self._lay.addWidget(self.lbl_paridad)

    def _crear_modo(self) -> None:
        self._lay.addWidget(_seccion("Modo"))
        fila = QHBoxLayout()
        fila.setSpacing(6)
        self.grupo_modo = QButtonGroup(self)
        self.btn_contorno = _boton_segmento("Contorno", "Solo el borde, de un bloque de grosor (Ctrl+T alterna).")
        self.btn_relleno = _boton_segmento("Relleno", "La figura completa (Ctrl+T alterna).")
        self.btn_contorno.setIcon(recursos.icono_figura("hexagono", "plano", "contorno", lado=20))
        self.btn_relleno.setIcon(recursos.icono_figura("hexagono", "plano", "relleno", lado=20))
        for boton in (self.btn_contorno, self.btn_relleno):
            self.grupo_modo.addButton(boton)
            fila.addWidget(boton)
        self.grupo_modo.buttonClicked.connect(lambda _b: self._emitir(False))
        self._lay.addLayout(fila)

    def _crear_color(self) -> None:
        self._lay.addWidget(_seccion("Color de los bloques"))
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
            boton.clicked.connect(lambda _=False, h=hexa: self.set_color(h, emitir=True))
            self.grupo_color.addButton(boton)
            self.muestras[hexa] = boton
            rejilla.addWidget(boton, i // 5, i % 5)
        self._lay.addLayout(rejilla)
        self.btn_color = QToolButton()
        self.btn_color.setText("Color personalizado…")
        self.btn_color.setIcon(recursos.icono("color"))
        self.btn_color.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_color.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.btn_color.setToolTip("Elegir cualquier color para los bloques")
        self.btn_color.clicked.connect(self._dialogo_color)
        self._lay.addWidget(self.btn_color)
        self.lbl_color = _ayuda()
        self._lay.addWidget(self.lbl_color)

    def figura_actual(self) -> str:
        boton = self.grupo_figura.checkedButton()
        return next((k for k, b in self.botones_figura.items() if b is boton), "hexagono")

    def configuracion(self) -> Configuracion:
        figura = self.figura_actual()
        modo = "relleno" if self.btn_relleno.isChecked() else "contorno"
        return Configuracion(
            figura, self.spin_tamano.value(), self._orientacion_actual[figura], modo, self._color
        )

    def set_configuracion(self, cfg: Configuracion) -> None:
        self._sincronizando = True
        try:
            self.botones_figura.get(cfg.figura, self.botones_figura["hexagono"]).setChecked(True)
            if cfg.orientacion in ORIENTACIONES.get(cfg.figura, ()):
                self._orientacion_actual[cfg.figura] = cfg.orientacion
            self.spin_tamano.setValue(cfg.tamano)
            (self.btn_relleno if cfg.modo == "relleno" else self.btn_contorno).setChecked(True)
            self.set_color(cfg.color, emitir=False)
            self._actualizar_controles_figura()
        finally:
            self._sincronizando = False

    def seleccionar_figura(self, clave: str) -> None:
        self.botones_figura[clave].setChecked(True)
        self._al_cambiar_figura()

    def alternar_modo(self) -> None:
        (self.btn_contorno if self.btn_relleno.isChecked() else self.btn_relleno).setChecked(True)
        self._emitir(False)

    def enfocar_tamano(self) -> None:
        self.spin_tamano.setFocus(Qt.FocusReason.ShortcutFocusReason)
        self.spin_tamano.selectAll()

    def set_color(self, color: str, emitir: bool) -> None:
        self._color = QColor(color).name().upper()
        boton = self.muestras.get(self._color)
        self.grupo_color.setExclusive(boton is not None)
        if boton is not None:
            boton.setChecked(True)
        else:
            for muestra in self.muestras.values():
                muestra.setChecked(False)
        nombre = next((n for n, h in COLORES if h == self._color), "personalizado")
        self.lbl_color.setText(f"Color actual: {nombre} ({self._color})")
        if emitir:
            self._emitir(False)

    def mostrar_error(self, mensaje: str | None) -> None:
        self.lbl_error.setVisible(bool(mensaje))
        self.lbl_error.setText(mensaje or "")
        self.spin_tamano.setProperty("error", bool(mensaje))
        self.spin_tamano.style().unpolish(self.spin_tamano)
        self.spin_tamano.style().polish(self.spin_tamano)

    def mostrar_figura(self, figura: Figura | None) -> None:
        if figura is None:
            self.lbl_proporciones.setText("—")
            self.lbl_paridad.setText("")
            return
        self.lbl_proporciones.setText(_texto_proporciones(figura))
        self.lbl_paridad.setText(_texto_paridad(figura.config))

    def _actualizar_controles_figura(self) -> None:
        figura = self.figura_actual()
        orientacion = self._orientacion_actual[figura]
        clave = f"{figura}_{orientacion}" if figura == "hexagono" else figura
        medida, ayuda = MEDIDAS_UI[clave]
        self.lbl_medida.setText(f"{medida} (en bloques)")
        self.lbl_ayuda_medida.setText(ayuda)
        self.contenedor_orientacion.setVisible(figura != "circulo")
        self._colocar_orientaciones(figura)
        boton = self.botones_orientacion.get(orientacion)
        if boton is not None:
            boton.setChecked(True)
        self._sincronizar_deslizador()

    def _colocar_orientaciones(self, figura: str) -> None:
        for boton in self.botones_orientacion.values():
            self._rejilla_orientacion.removeWidget(boton)
            boton.hide()
        columnas = 1 if figura == "hexagono" else 2
        for i, orientacion in enumerate(ORIENTACIONES.get(figura, ())):
            if not orientacion:
                continue
            boton = self.botones_orientacion[orientacion]
            self._rejilla_orientacion.addWidget(boton, i // columnas, i % columnas)
            boton.show()

    def _sincronizar_deslizador(self) -> None:
        self.deslizador.blockSignals(True)
        self.deslizador.setValue(deslizador_desde_tamano(self.spin_tamano.value()))
        self.deslizador.blockSignals(False)

    def _al_cambiar_spin(self, _valor: int) -> None:
        if not self.deslizador.isSliderDown():
            self._sincronizar_deslizador()
        self._emitir(True)

    def _al_mover_deslizador(self, posicion: int) -> None:
        self.spin_tamano.blockSignals(True)
        self.spin_tamano.setValue(tamano_desde_deslizador(posicion))
        self.spin_tamano.blockSignals(False)
        self._emitir(True)

    def _al_cambiar_figura(self) -> None:
        self._actualizar_controles_figura()
        self._emitir(True)

    def _al_cambiar_orientacion(self) -> None:
        boton = self.grupo_orientacion.checkedButton()
        orientacion = next(o for o, b in self.botones_orientacion.items() if b is boton)
        self._orientacion_actual[self.figura_actual()] = orientacion
        self._actualizar_controles_figura()
        self._emitir(True)

    def _dialogo_color(self) -> None:
        color = QColorDialog.getColor(QColor(self._color), self, "Color de los bloques")
        if color.isValid():
            self.set_color(color.name(), emitir=True)

    def _emitir(self, afecta_geometria: bool) -> None:
        if not self._sincronizando:
            self.cambiado.emit(afecta_geometria)


def _texto_proporciones(figura: Figura) -> str:
    cfg = figura.config
    if cfg.figura == "circulo":
        return f"Ancho = alto = <b>{figura.ancho}</b> bloques"
    if cfg.figura == "triangulo" and cfg.orientacion in ("izquierda", "derecha"):
        return (
            f"Ancho calculado: {formato_num(figura.ancho_teorico)} → <b>{figura.ancho} bloques</b>"
            f"<br>Alto (base): <b>{figura.alto}</b> bloques"
        )
    return (
        f"Alto calculado: {formato_num(figura.alto_teorico)} → <b>{figura.alto} bloques</b>"
        f"<br>Ancho: <b>{figura.ancho}</b> bloques"
    )


def _texto_paridad(cfg: Configuracion) -> str:
    par = cfg.tamano % 2 == 0
    if cfg.figura == "triangulo":
        return "Base par: el vértice ocupa 2 bloques." if par else "Base impar: el vértice es un solo bloque."
    return "Tamaño par: el centro cae entre dos bloques." if par else "Tamaño impar: hay un bloque central."
