"""Identidad visual de Hexabloq: colores, tipografía, hoja de estilos y paletas del lienzo."""

from __future__ import annotations

from dataclasses import dataclass

NOMBRE_APP = "Hexabloq"
LEMA = "Figuras con bloques, fila a fila"

FUENTE = "Segoe UI"
FUENTE_PT = 10

FONDO = "#121417"
PANEL = "#1A1D21"
SUPERFICIE = "#22262B"
SUPERFICIE_ALTA = "#2B3036"
BORDE = "#33393F"
BORDE_FUERTE = "#4A525B"
TEXTO = "#E8EAED"
TEXTO_SECUNDARIO = "#A3ABB4"
TEXTO_TENUE = "#6F7882"
ACENTO = "#3FC98A"
ACENTO_HOVER = "#5DD9A1"
ACENTO_PULSADO = "#2FA873"
ACENTO_SUAVE = "rgba(63, 201, 138, 0.16)"
SOBRE_ACENTO = "#0B1F15"
AMBAR = "#F5B83D"
ERROR = "#F07171"
ERROR_FONDO = "#3A1E21"

MARCA_FONDO = "#1A1D21"
MARCA_CLARO = "#7BE3B1"
MARCA_BASE = "#2FA873"


@dataclass(frozen=True)
class PaletaLienzo:
    nombre: str
    fondo: str
    marco_relleno: str
    marco_borde: str
    linea_menor: str
    linea_mayor: str
    eje_vertical: str
    eje_horizontal: str
    centro: str
    centro_halo: str
    resaltado_banda: str
    resaltado_borde: str
    cursor: str
    numeros: str
    numeros_resaltado: str


LIENZO_OSCURO = PaletaLienzo(
    nombre="oscuro",
    fondo="#16191C",
    marco_relleno="#1D2125",
    marco_borde="#3A4148",
    linea_menor="#23282D",
    linea_mayor="#323940",
    eje_vertical="#E0605BCC",
    eje_horizontal="#5B9BE0CC",
    centro="#FF7A73",
    centro_halo="#16191C",
    resaltado_banda="#F5B83D2E",
    resaltado_borde=AMBAR,
    cursor="#FFFFFFB0",
    numeros="#7D8791",
    numeros_resaltado=AMBAR,
)

LIENZO_CLARO = PaletaLienzo(
    nombre="claro",
    fondo="#F2EFE6",
    marco_relleno="#0000000C",
    marco_borde="#9C968A",
    linea_menor="#D3CEC2",
    linea_mayor="#A8A194",
    eje_vertical="#D64541C8",
    eje_horizontal="#3478D6C8",
    centro="#D64541",
    centro_halo="#FFFFFF",
    resaltado_banda="#FFC40046",
    resaltado_borde="#E69500",
    cursor="#1E1E1EAA",
    numeros="#5E5A52",
    numeros_resaltado="#B36F00",
)

PALETAS_LIENZO = {p.nombre: p for p in (LIENZO_OSCURO, LIENZO_CLARO)}


def _argb(color: str) -> str:
    """Qt interpreta #RRGGBBAA como #AARRGGBB; las paletas usan #RRGGBBAA."""
    if len(color) == 9:
        return "#" + color[7:9] + color[1:7]
    return color


def color_qt(color: str):
    from PySide6.QtGui import QColor

    return QColor(_argb(color))


def hoja_estilo(ruta_check: str | None) -> str:
    check = f'image: url("{ruta_check.replace(chr(92), "/")}");' if ruta_check else ""
    return f"""
* {{ color: {TEXTO}; }}
QWidget {{ font-family: "{FUENTE}"; font-size: {FUENTE_PT}pt; }}
QMainWindow, QWidget#raiz, QWidget#zonaLienzo {{ background: {FONDO}; }}
QWidget#barraSuperior {{ background: {PANEL}; border-bottom: 1px solid {BORDE}; }}
QWidget#panelLateral, QWidget#panelGuia, QScrollArea#desplazamientoPanel,
QScrollArea#desplazamientoPanel > QWidget > QWidget {{ background: {PANEL}; }}
QScrollArea {{ border: none; }}
QWidget#barraLienzo {{
    background: {SUPERFICIE}; border: 1px solid {BORDE}; border-radius: 8px;
}}
QFrame#separador {{ background: {BORDE}; max-width: 1px; min-width: 1px; }}
QFrame#tarjeta {{ background: {SUPERFICIE}; border: 1px solid {BORDE}; border-radius: 8px; }}

QLabel#nombreApp {{ font-size: 13pt; font-weight: 700; }}
QLabel#nombreArchivo {{ color: {TEXTO_SECUNDARIO}; }}
QLabel#tituloPanel {{ font-size: 12pt; font-weight: 600; }}
QLabel#seccion {{
    color: {TEXTO_SECUNDARIO}; font-size: 8.5pt; font-weight: 700; letter-spacing: 1px;
    padding-top: 6px;
}}
QLabel#ayuda {{ color: {TEXTO_TENUE}; font-size: 9pt; }}
QLabel#valorDato {{ font-size: 16pt; font-weight: 700; }}
QLabel#valorDatoAcento {{ font-size: 16pt; font-weight: 700; color: {ACENTO}; }}
QLabel#etiquetaDato {{ color: {TEXTO_SECUNDARIO}; font-size: 9pt; }}
QLabel#detalleDato {{ color: {TEXTO_TENUE}; font-size: 8.5pt; }}
QLabel#infoFila {{ color: {TEXTO_SECUNDARIO}; }}
QLabel#error {{
    color: #FFD7D7; background: {ERROR_FONDO}; border: 1px solid {ERROR};
    border-radius: 6px; padding: 8px 10px;
}}

QPushButton, QToolButton {{
    background: {SUPERFICIE}; border: 1px solid {BORDE}; border-radius: 6px;
    padding: 6px 12px; color: {TEXTO};
}}
QPushButton:hover, QToolButton:hover {{ background: {SUPERFICIE_ALTA}; border-color: {BORDE_FUERTE}; }}
QPushButton:pressed, QToolButton:pressed {{ background: {BORDE}; }}
QPushButton:checked, QToolButton:checked {{
    background: {ACENTO_SUAVE}; border-color: {ACENTO}; color: {ACENTO_HOVER};
}}
QPushButton:disabled, QToolButton:disabled {{
    background: {PANEL}; border-color: {BORDE}; color: {TEXTO_TENUE};
}}
QPushButton:focus, QToolButton:focus {{ border: 1px solid {ACENTO_HOVER}; }}
QPushButton#primario {{
    background: {ACENTO}; border-color: {ACENTO}; color: {SOBRE_ACENTO}; font-weight: 600;
}}
QPushButton#primario:hover {{ background: {ACENTO_HOVER}; border-color: {ACENTO_HOVER}; }}
QPushButton#primario:pressed {{ background: {ACENTO_PULSADO}; }}
QPushButton#primario:focus {{ border: 2px solid {TEXTO}; }}
QPushButton#primario:disabled {{ background: {SUPERFICIE}; color: {TEXTO_TENUE}; border-color: {BORDE}; }}

QToolButton#accionBarra, QToolButton#herramienta {{
    background: transparent; border: 1px solid transparent; padding: 5px 8px;
}}
QToolButton#accionBarra:hover, QToolButton#herramienta:hover {{
    background: {SUPERFICIE_ALTA}; border-color: {BORDE};
}}
QToolButton#accionBarra:focus, QToolButton#herramienta:focus {{ border-color: {ACENTO_HOVER}; }}
QToolButton#herramienta:checked {{ background: {ACENTO_SUAVE}; border-color: transparent; color: {ACENTO_HOVER}; }}
QToolButton#herramienta:checked:focus {{ border-color: {ACENTO_HOVER}; }}
QToolButton#accionBarra::menu-indicator {{ image: none; width: 0; }}

QToolButton#tarjetaFigura {{
    background: {SUPERFICIE}; border: 1px solid {BORDE}; border-radius: 8px;
    padding: 10px 4px 8px 4px; font-weight: 600;
}}
QToolButton#tarjetaFigura:hover {{ border-color: {BORDE_FUERTE}; background: {SUPERFICIE_ALTA}; }}
QToolButton#tarjetaFigura:checked {{
    background: {ACENTO_SUAVE}; border: 2px solid {ACENTO}; color: {TEXTO};
}}
QToolButton#tarjetaFigura:focus {{ border: 2px solid {ACENTO_HOVER}; }}

QToolButton#segmento {{ padding: 6px 8px; }}
QToolButton#muestra {{
    min-width: 24px; max-width: 24px; min-height: 24px; max-height: 24px;
    padding: 0; border-radius: 5px; border: 2px solid {FONDO};
}}
QToolButton#muestra:hover {{ border-color: {BORDE_FUERTE}; }}
QToolButton#muestra:checked {{ border: 2px solid {TEXTO}; }}
QToolButton#muestra:focus {{ border: 2px solid {ACENTO_HOVER}; }}

QSpinBox, QComboBox, QLineEdit {{
    background: {FONDO}; border: 1px solid {BORDE}; border-radius: 6px;
    padding: 5px 8px; selection-background-color: {ACENTO_PULSADO}; selection-color: {SOBRE_ACENTO};
}}
QSpinBox:hover, QComboBox:hover {{ border-color: {BORDE_FUERTE}; }}
QSpinBox:focus, QComboBox:focus, QLineEdit:focus {{ border-color: {ACENTO}; }}
QSpinBox[error="true"] {{ border-color: {ERROR}; }}
QSpinBox#tamano {{ font-size: 14pt; font-weight: 700; padding: 4px 8px; }}
QSpinBox::up-button, QSpinBox::down-button {{ width: 20px; border: none; }}
QComboBox QAbstractItemView {{
    background: {SUPERFICIE}; border: 1px solid {BORDE}; selection-background-color: {ACENTO_PULSADO};
}}

QSlider::groove:horizontal {{ height: 4px; background: {BORDE}; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {ACENTO_PULSADO}; border-radius: 2px; }}
QSlider::handle:horizontal {{
    background: {ACENTO}; width: 16px; height: 16px; margin: -6px 0; border-radius: 8px;
    border: 2px solid {PANEL};
}}
QSlider::handle:horizontal:hover {{ background: {ACENTO_HOVER}; }}
QSlider:focus {{ outline: none; }}
QSlider::handle:horizontal:focus {{ border: 2px solid {TEXTO}; }}

QCheckBox {{ spacing: 8px; padding: 2px 0; }}
QCheckBox::indicator {{
    width: 16px; height: 16px; border: 1px solid {BORDE_FUERTE}; background: {FONDO}; border-radius: 4px;
}}
QCheckBox::indicator:checked {{ background: {ACENTO}; border-color: {ACENTO}; {check} }}
QCheckBox:focus {{ color: {ACENTO_HOVER}; }}

QTableView {{
    background: {FONDO}; alternate-background-color: #171A1D; gridline-color: {BORDE};
    border: 1px solid {BORDE}; border-radius: 6px;
    selection-background-color: #5A4415; selection-color: #FFFFFF;
}}
QTableView:focus {{ border-color: {ACENTO}; }}
QHeaderView::section {{
    background: {SUPERFICIE}; color: {TEXTO_SECUNDARIO}; border: none;
    border-right: 1px solid {BORDE}; border-bottom: 1px solid {BORDE}; padding: 6px; font-weight: 600;
}}
QTableCornerButton::section {{ background: {SUPERFICIE}; border: none; }}

QSplitter::handle {{ background: {BORDE}; }}
QSplitter::handle:horizontal {{ width: 1px; }}
QSplitter::handle:hover {{ background: {ACENTO}; }}
QStatusBar {{ background: {PANEL}; border-top: 1px solid {BORDE}; color: {TEXTO_SECUNDARIO}; }}
QStatusBar QLabel {{ color: {TEXTO_SECUNDARIO}; padding: 0 10px; }}
QStatusBar::item {{ border: none; }}
QMenu {{ background: {SUPERFICIE}; border: 1px solid {BORDE}; padding: 4px; }}
QMenu::item {{ padding: 6px 28px 6px 12px; border-radius: 4px; }}
QMenu::item:selected {{ background: {ACENTO_SUAVE}; color: {TEXTO}; }}
QMenu::item:disabled {{ color: {TEXTO_TENUE}; }}
QMenu::separator {{ height: 1px; background: {BORDE}; margin: 4px 8px; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {BORDE_FUERTE}; min-height: 24px; border-radius: 4px; margin: 2px; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 0; }}
QScrollBar::handle:horizontal {{ background: {BORDE_FUERTE}; min-width: 24px; border-radius: 4px; margin: 2px; }}
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{
    width: 0; height: 0; background: none;
}}
QDialog, QMessageBox {{ background: {PANEL}; }}
QToolTip {{
    background: {SUPERFICIE_ALTA}; color: {TEXTO}; border: 1px solid {BORDE_FUERTE};
    padding: 5px 7px; border-radius: 4px;
}}
"""
