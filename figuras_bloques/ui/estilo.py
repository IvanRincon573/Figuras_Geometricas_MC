"""Hoja de estilos: tema oscuro con acentos inspirados en herramientas de construcción."""

ACENTO = "#6BAA3F"
ACENTO_OSCURO = "#4C7D2B"

QSS = f"""
* {{
    font-family: "Segoe UI", "Arial";
    font-size: 10pt;
    color: #E6E3DC;
}}
QMainWindow, QWidget#raiz {{ background: #1B1E21; }}
QWidget#panel, QWidget#guia {{ background: #23272B; }}
QScrollArea {{ border: none; background: #23272B; }}
QScrollArea > QWidget > QWidget {{ background: #23272B; }}

QLabel#titulo {{
    font-size: 14pt; font-weight: 700; color: #F2EFE6; padding: 2px 0 0 0;
}}
QLabel#subtitulo {{ color: #9EA3A8; font-size: 9pt; }}
QLabel#seccion {{
    color: {ACENTO}; font-weight: 700; font-size: 8.5pt;
    letter-spacing: 1px; padding-top: 10px; border-bottom: 2px solid #34393E;
    padding-bottom: 3px;
}}
QLabel#dato {{ color: #F2EFE6; font-weight: 600; }}
QLabel#datoGrande {{ color: #F2EFE6; font-weight: 700; font-size: 18pt; }}
QLabel#etiquetaDato {{ color: #9EA3A8; }}
QLabel#error {{
    color: #FFD9D6; background: #5A2420; border: 1px solid #A2453C;
    border-radius: 4px; padding: 6px 8px;
}}
QLabel#aviso {{ color: #9EA3A8; font-size: 9pt; }}

QPushButton, QToolButton {{
    background: #33383D; border: 1px solid #454B51; border-bottom: 3px solid #191C1F;
    border-radius: 4px; padding: 6px 10px; color: #E6E3DC;
}}
QPushButton:hover, QToolButton:hover {{ background: #3D4349; border-color: #59616A; }}
QPushButton:pressed, QToolButton:pressed {{ border-bottom-width: 1px; padding-top: 8px; }}
QPushButton:checked, QToolButton:checked {{
    background: {ACENTO_OSCURO}; border-color: {ACENTO}; border-bottom-color: #2E4D1A;
    color: #FFFFFF; font-weight: 600;
}}
QPushButton#primario {{
    background: {ACENTO_OSCURO}; border-color: {ACENTO}; border-bottom-color: #2E4D1A;
    font-weight: 600; color: white;
}}
QPushButton#primario:hover {{ background: {ACENTO}; }}
QToolButton#figura {{ padding: 8px 4px; min-width: 70px; }}
QPushButton#muestra {{
    min-width: 22px; max-width: 22px; min-height: 22px; max-height: 22px;
    padding: 0; border-radius: 3px; border: 2px solid #191C1F;
}}
QPushButton#muestra:checked {{ border: 2px solid #FFFFFF; }}

QSpinBox, QComboBox, QLineEdit {{
    background: #15181A; border: 1px solid #454B51; border-radius: 4px;
    padding: 5px 6px; selection-background-color: {ACENTO_OSCURO};
}}
QSpinBox:focus, QComboBox:focus, QLineEdit:focus {{ border-color: {ACENTO}; }}
QSpinBox#tamano {{ font-size: 15pt; font-weight: 700; padding: 4px 8px; }}
QSpinBox::up-button, QSpinBox::down-button {{ width: 22px; }}
QComboBox QAbstractItemView {{
    background: #23272B; border: 1px solid #454B51; selection-background-color: {ACENTO_OSCURO};
}}
QCheckBox {{ spacing: 8px; padding: 2px 0; }}
QCheckBox::indicator {{
    width: 16px; height: 16px; border: 1px solid #5A6168; background: #15181A; border-radius: 3px;
}}
QCheckBox::indicator:checked {{ background: {ACENTO}; border-color: {ACENTO}; image: url("@CHECK@"); }}

QTableView {{
    background: #1B1E21; alternate-background-color: #212528; gridline-color: #2E3337;
    border: 1px solid #34393E; border-radius: 4px; selection-background-color: #8A6A12;
    selection-color: #FFFFFF;
}}
QHeaderView::section {{
    background: #2B3034; color: #B9BEC3; border: none; border-right: 1px solid #34393E;
    border-bottom: 1px solid #34393E; padding: 5px; font-weight: 600;
}}
QTableCornerButton::section {{ background: #2B3034; border: none; }}

QSplitter::handle {{ background: #15181A; }}
QSplitter::handle:horizontal {{ width: 4px; }}
QStatusBar {{ background: #15181A; color: #B9BEC3; }}
QStatusBar QLabel {{ color: #B9BEC3; padding: 0 8px; }}
QMenuBar {{ background: #15181A; }}
QMenuBar::item {{ padding: 5px 10px; background: transparent; }}
QMenuBar::item:selected {{ background: #33383D; }}
QMenu {{ background: #23272B; border: 1px solid #454B51; }}
QMenu::item {{ padding: 6px 24px; }}
QMenu::item:selected {{ background: {ACENTO_OSCURO}; }}
QMenu::separator {{ height: 1px; background: #3A3F44; margin: 4px 8px; }}
QToolBar {{ background: #1F2326; border: none; border-bottom: 1px solid #15181A; spacing: 4px; padding: 4px; }}
QToolBar QToolButton {{ padding: 4px 10px; }}
QScrollBar:vertical {{ background: #1B1E21; width: 12px; margin: 0; }}
QScrollBar::handle:vertical {{ background: #3D4349; min-height: 24px; border-radius: 4px; margin: 2px; }}
QScrollBar:horizontal {{ background: #1B1E21; height: 12px; margin: 0; }}
QScrollBar::handle:horizontal {{ background: #3D4349; min-width: 24px; border-radius: 4px; margin: 2px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QDialog {{ background: #23272B; }}
QToolTip {{ background: #2B3034; color: #E6E3DC; border: 1px solid #454B51; padding: 4px; }}
"""


def hoja_estilo(ruta_check: str | None = None) -> str:
    """QSS final; ``ruta_check`` es el SVG de la marca de las casillas."""
    if ruta_check:
        return QSS.replace("@CHECK@", ruta_check.replace("\\", "/"))
    return QSS.replace('image: url("@CHECK@");', '')
