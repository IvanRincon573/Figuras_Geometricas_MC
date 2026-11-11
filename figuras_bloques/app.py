"""Arranque de Hexabloq."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ID_APLICACION = "Hexabloq.Escritorio"
OPCION_COMPROBAR = "--comprobar-recursos"


def _registrar_id_en_windows() -> None:
    """Sin esto, la barra de tareas agrupa la ventana con python.exe y muestra su icono."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(ID_APLICACION)
    except (AttributeError, OSError):
        pass


def _crear_aplicacion(argv: list[str]):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFont, QGuiApplication
    from PySide6.QtWidgets import QApplication

    from .ui import recursos, tema

    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(argv)
    app.setApplicationName(tema.NOMBRE_APP)
    app.setApplicationDisplayName(tema.NOMBRE_APP)
    app.setOrganizationName(tema.NOMBRE_APP)
    app.setStyle("Fusion")
    app.setFont(QFont(tema.FUENTE, tema.FUENTE_PT))
    check = recursos.CHECK_PNG
    app.setStyleSheet(tema.hoja_estilo(str(check) if check.is_file() else None))
    app.setWindowIcon(recursos.icono_app())
    return app


def _comprobar_recursos(argv: list[str]) -> int:
    """Escribe en un JSON si cada recurso visual se carga; útil para validar el ejecutable."""
    from .ui import recursos

    app = _crear_aplicacion(argv[:1])  # noqa: F841
    indice = argv.index(OPCION_COMPROBAR)
    destino = Path(argv[indice + 1]) if len(argv) > indice + 1 else Path("comprobacion_recursos.json")
    estado = recursos.comprobar()
    destino.write_text(json.dumps(estado, indent=2, ensure_ascii=False), encoding="utf-8")
    return 0 if all(estado.values()) else 1


def _diseno_en_argumentos(argv: list[str]) -> str | None:
    return next((a for a in argv[1:] if a.lower().endswith(".json") and Path(a).is_file()), None)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)
    _registrar_id_en_windows()
    if OPCION_COMPROBAR in argv:
        return _comprobar_recursos(argv)
    from .ui.ventana import VentanaPrincipal

    app = _crear_aplicacion(argv)
    ventana = VentanaPrincipal()
    ventana.show()
    diseno = _diseno_en_argumentos(argv)
    if diseno:
        ventana.abrir_ruta(diseno)
    return app.exec()
