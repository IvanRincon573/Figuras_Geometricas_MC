"""Arranque de la aplicación de escritorio."""

from __future__ import annotations

import sys
from pathlib import Path

ID_APLICACION = "FigurasBloques.App"


def ruta_recurso(relativa: str) -> Path:
    """Ruta a un recurso, tanto desde el código como dentro del ejecutable de PyInstaller."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / relativa


def _registrar_id_en_windows() -> None:
    """Sin esto, la barra de tareas muestra el icono de python.exe."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(ID_APLICACION)
    except (AttributeError, OSError):
        pass


def _crear_aplicacion(argv: list[str]):
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication

    from .ui.estilo import hoja_estilo

    app = QApplication(argv)
    app.setApplicationName("Figuras con bloques")
    app.setOrganizationName("FigurasBloques")
    app.setStyle("Fusion")
    check = ruta_recurso("assets/check.svg")
    app.setStyleSheet(hoja_estilo(str(check) if check.exists() else None))
    icono = ruta_recurso("assets/icono.ico")
    if icono.exists():
        app.setWindowIcon(QIcon(str(icono)))
    return app


def _diseno_en_argumentos(argv: list[str]) -> str | None:
    return next((a for a in argv[1:] if a.lower().endswith(".json") and Path(a).is_file()), None)


def main(argv: list[str] | None = None) -> int:
    from .ui.ventana import VentanaPrincipal

    argv = list(sys.argv if argv is None else argv)
    _registrar_id_en_windows()
    app = _crear_aplicacion(argv)
    ventana = VentanaPrincipal()
    ventana.show()
    diseno = _diseno_en_argumentos(argv)
    if diseno:
        ventana.abrir_ruta(diseno)
    return app.exec()
