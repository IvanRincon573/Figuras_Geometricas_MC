"""Genera assets/icono.ico y assets/icono.png con un hexágono de bloques.

Uso: python tools/generar_icono.py
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from PySide6.QtCore import QRectF, Qt  # noqa: E402
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter  # noqa: E402

from figuras_bloques.geometria import Configuracion, generar  # noqa: E402


def dibujar(lado: int) -> QImage:
    img = QImage(lado, lado, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#23272B"))
    r = lado * 0.18
    p.drawRoundedRect(QRectF(0, 0, lado, lado), r, r)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
    n = 13 if lado >= 48 else 9
    fig = generar(Configuracion("hexagono", n, "plano", "contorno"))
    relleno = generar(Configuracion("hexagono", n, "plano", "relleno"))
    margen = lado * 0.14
    s = (lado - 2 * margen) / max(fig.ancho, fig.alto)
    ox = (lado - fig.ancho * s) / 2
    oy = (lado - fig.alto * s) / 2
    for x, y in relleno.celdas:
        color = QColor("#6BAA3F") if fig.contiene(x, y) else QColor("#3A5A26")
        p.fillRect(QRectF(ox + x * s, oy + y * s, s, s), color)
        if s >= 6:
            p.setPen(QColor(0, 0, 0, 90))
            p.drawRect(QRectF(ox + x * s, oy + y * s, s - 1, s - 1))
            p.setPen(Qt.PenStyle.NoPen)
    p.end()
    return img


def main() -> None:
    app = QGuiApplication(sys.argv)  # noqa: F841
    destino = RAIZ / "assets"
    destino.mkdir(exist_ok=True)
    dibujar(256).save(str(destino / "icono.png"))
    # Qt guarda ICO de un solo tamaño; Windows lo escala bien desde 256 px.
    dibujar(256).save(str(destino / "icono.ico"), "ICO")
    print("Icono generado en", destino)


if __name__ == "__main__":
    main()
