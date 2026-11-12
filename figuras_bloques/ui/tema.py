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
    linea_bloque: str
    linea_chunk: str
    eje_x: str
    eje_z: str
    origen: str
    resaltado_banda: str
    resaltado_borde: str
    cursor: str
    seleccion: str
    seleccion_grupo: str
    seleccion_oculta: str
    banda_seleccion: str
    centro_objeto: str
    regla_fondo: str
    regla_texto: str
    regla_chunk: str
    etiqueta_chunk: str


LIENZO_OSCURO = PaletaLienzo(
    nombre="oscuro",
    fondo="#16191C",
    linea_bloque="#22272C",
    linea_chunk="#3E4852",
    eje_x="#E0605BD0",
    eje_z="#5B9BE0D0",
    origen="#FFFFFF",
    resaltado_banda="#F5B83D2E",
    resaltado_borde=AMBAR,
    cursor="#FFFFFFB0",
    seleccion="#3FDDF0",
    seleccion_grupo="#3FDDF080",
    seleccion_oculta="#8A939C",
    banda_seleccion="#3FDDF026",
    centro_objeto="#3FDDF0",
    regla_fondo="#1C2024E8",
    regla_texto="#8A949E",
    regla_chunk="#C9D1D9",
    etiqueta_chunk="#55606B",
)

LIENZO_CLARO = PaletaLienzo(
    nombre="claro",
    fondo="#F2EFE6",
    linea_bloque="#DDD8CC",
    linea_chunk="#9F988A",
    eje_x="#D64541D0",
    eje_z="#3478D6D0",
    origen="#1E1E1E",
    resaltado_banda="#FFC40046",
    resaltado_borde="#E69500",
    cursor="#1E1E1EAA",
    seleccion="#0A8FC4",
    seleccion_grupo="#0A8FC480",
    seleccion_oculta="#8A8478",
    banda_seleccion="#0A8FC422",
    centro_objeto="#0A8FC4",
    regla_fondo="#E8E4D8EE",
    regla_texto="#6B665C",
    regla_chunk="#2E2B26",
    etiqueta_chunk="#A39D90",
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
QTreeView {{
    background: {FONDO}; alternate-background-color: #171A1D; border: 1px solid {BORDE};
    border-radius: 6px; show-decoration-selected: 1; outline: none;
}}
QTreeView::item {{ padding: 3px 2px; color: {TEXTO}; }}
QTreeView::item:selected {{ background: {ACENTO_SUAVE}; color: {TEXTO}; }}
QTreeView::item:hover {{ background: {SUPERFICIE_ALTA}; }}
QTreeView:focus {{ border-color: {ACENTO}; }}
QTreeView::branch {{ background: {FONDO}; }}
QTreeView::branch:selected {{ background: {ACENTO_SUAVE}; }}
QTabWidget::pane {{ border: none; background: {PANEL}; top: -1px; }}
QTabWidget > QWidget {{ background: {PANEL}; }}
QTabBar {{ background: {PANEL}; }}
QTabBar::tab {{
    background: {PANEL}; color: {TEXTO_SECUNDARIO}; padding: 9px 16px; border: none;
    border-bottom: 2px solid {BORDE};
}}
QTabBar::tab:selected {{ color: {TEXTO}; border-bottom: 2px solid {ACENTO}; }}
QTabBar::tab:hover {{ color: {TEXTO}; background: {SUPERFICIE}; }}
QTabBar::tab:focus {{ color: {ACENTO_HOVER}; }}
QRadioButton {{ spacing: 8px; padding: 2px 0; }}
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
