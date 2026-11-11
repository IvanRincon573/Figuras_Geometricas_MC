"""Arranque de la aplicación de escritorio."""

from __future__ import annotations

import sys
from pathlib import Path


def ruta_recurso(relativa: str) -> Path:
    """Ruta a un recurso tanto en desarrollo como dentro del ejecutable de PyInstaller."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / relativa


def main(argv: list[str] | None = None) -> int:
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication

    from .ui.estilo import hoja_estilo
    from .ui.ventana import VentanaPrincipal

    argv = list(sys.argv if argv is None else argv)
    if sys.platform == "win32":
        try:  # Icono propio en la barra de tareas (no el de python.exe).
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("FigurasBloques.App")
        except Exception:
            pass

    app = QApplication(argv)
    app.setApplicationName("Figuras con bloques")
    app.setOrganizationName("FigurasBloques")
    app.setStyle("Fusion")
    check = ruta_recurso("assets/check.svg")
    app.setStyleSheet(hoja_estilo(str(check) if check.exists() else None))
    icono = ruta_recurso("assets/icono.ico")
    if icono.exists():
        app.setWindowIcon(QIcon(str(icono)))

    ventana = VentanaPrincipal()
    ventana.show()
    # Permite abrir un diseño pasándolo como argumento (p. ej. arrastrándolo sobre el .exe).
    for arg in argv[1:]:
        if arg.lower().endswith(".json") and Path(arg).is_file():
            ventana.abrir_ruta(arg)
            break
    return app.exec()
