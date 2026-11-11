"""Genera la identidad visual de Hexabloq en figuras_bloques/recursos/marca.

El logo es un hexágono construido con la propia geometría de la aplicación.
Uso: python tools/generar_identidad.py
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QRectF, Qt  # noqa: E402
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter, QPainterPath, QPen  # noqa: E402
from PySide6.QtSvg import QSvgRenderer  # noqa: E402

from figuras_bloques.geometria import Configuracion, Figura, generar  # noqa: E402
from figuras_bloques.ui import tema  # noqa: E402

MARCA = RAIZ / "figuras_bloques" / "recursos" / "marca"
ICONOS = RAIZ / "figuras_bloques" / "recursos" / "iconos"
TAMANOS_ICO = (16, 20, 24, 32, 40, 48, 64, 128, 256)
BLOQUE_SVG = 10
LOGO_ANCHO = 15


def hexagono(ancho: int) -> Figura:
    return generar(Configuracion("hexagono", ancho, "plano", "relleno"))


def color_bloque(figura: Figura, x: int, y: int) -> str:
    return tema.MARCA_BASE if (x, y) in hexagono_interior(figura) else tema.MARCA_CLARO


def hexagono_interior(figura: Figura) -> set[tuple[int, int]]:
    celdas = figura.conjunto
    return {
        (x, y) for x, y in celdas
        if all(v in celdas for v in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
    }


def svg_bloques(figura: Figura, x0: float, y0: float) -> list[str]:
    b = BLOQUE_SVG
    partes = []
    for x, y in figura.celdas:
        px, py = x0 + x * b, y0 + y * b
        base = QColor(color_bloque(figura, x, y))
        luz, sombra = base.lighter(125).name(), base.darker(150).name()
        partes += [
            f'<rect x="{px}" y="{py}" width="{b}" height="{b}" fill="{base.name()}"/>',
            f'<rect x="{px}" y="{py}" width="{b}" height="1.5" fill="{luz}"/>',
            f'<rect x="{px}" y="{py}" width="1.5" height="{b}" fill="{luz}"/>',
            f'<rect x="{px}" y="{py + b - 1.5}" width="{b}" height="1.5" fill="{sombra}"/>',
            f'<rect x="{px + b - 1.5}" y="{py}" width="1.5" height="{b}" fill="{sombra}"/>',
        ]
    return partes


def svg_logo() -> str:
    figura = hexagono(LOGO_ANCHO)
    ancho, alto = figura.ancho * BLOQUE_SVG, figura.alto * BLOQUE_SVG
    cuerpo = "\n  ".join(svg_bloques(figura, 0, 0))
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ancho} {alto}" '
        f'width="{ancho * 4}" height="{alto * 4}" shape-rendering="crispEdges">\n'
        f"  <title>Hexabloq</title>\n  {cuerpo}\n</svg>\n"
    )


def svg_logo_con_nombre() -> str:
    figura = hexagono(LOGO_ANCHO)
    alto = figura.alto * BLOQUE_SVG
    ancho = figura.ancho * BLOQUE_SVG + 300
    cuerpo = "\n  ".join(svg_bloques(figura, 0, 0))
    texto_y = alto / 2 + 15
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ancho} {alto}" '
        f'width="{ancho * 3}" height="{alto * 3}">\n'
        f"  <title>Hexabloq</title>\n  <g shape-rendering=\"crispEdges\">\n  {cuerpo}\n  </g>\n"
        f'  <text x="{figura.ancho * BLOQUE_SVG + 18}" y="{texto_y}" '
        f'font-family="Segoe UI, Arial, sans-serif" font-size="44" font-weight="700" '
        f'letter-spacing="0.5"><tspan fill="{tema.TEXTO}">Hexa</tspan>'
        f'<tspan fill="{tema.ACENTO}">bloq</tspan></text>\n</svg>\n'
    )


def svg_icono() -> str:
    figura = hexagono(9)
    lado = 64
    bloque = 6
    x0 = (lado - figura.ancho * bloque) / 2
    y0 = (lado - figura.alto * bloque) / 2
    rects = [
        f'<rect x="{x0 + x * bloque}" y="{y0 + y * bloque}" width="{bloque}" height="{bloque}" '
        f'fill="{color_bloque(figura, x, y)}"/>'
        for x, y in figura.celdas
    ]
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {lado} {lado}" width="256" height="256">\n'
        f"  <title>Hexabloq</title>\n"
        f'  <rect width="{lado}" height="{lado}" rx="13" fill="{tema.MARCA_FONDO}"/>\n'
        f'  <g shape-rendering="crispEdges">\n    ' + "\n    ".join(rects) + "\n  </g>\n</svg>\n"
    )


def renderizar_svg(svg: str, ancho: int, alto: int) -> QImage:
    imagen = QImage(ancho, alto, QImage.Format.Format_ARGB32_Premultiplied)
    imagen.fill(Qt.GlobalColor.transparent)
    p = QPainter(imagen)
    QSvgRenderer(QByteArray(svg.encode("utf-8"))).render(p, QRectF(0, 0, ancho, alto))
    p.end()
    return imagen


def parametros_icono(lado: int) -> tuple[int, int, bool]:
    """(ancho del hexágono en bloques, píxeles por bloque, relieve) para cada tamaño."""
    if lado < 32:
        return 7, max(1, (lado - 2) // 7), False
    if lado < 64:
        return 9, (lado - 4) // 9, False
    return 15, (lado - lado // 5) // 15, lado >= 128


def dibujar_icono(lado: int) -> QImage:
    ancho_hex, bloque, relieve = parametros_icono(lado)
    figura = hexagono(ancho_hex)
    imagen = QImage(lado, lado, QImage.Format.Format_ARGB32_Premultiplied)
    imagen.fill(Qt.GlobalColor.transparent)
    p = QPainter(imagen)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    fondo = QPainterPath()
    radio = max(2.0, lado * 0.2)
    fondo.addRoundedRect(QRectF(0, 0, lado, lado), radio, radio)
    p.fillPath(fondo, QColor(tema.MARCA_FONDO))
    p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
    x0 = (lado - figura.ancho * bloque) // 2
    y0 = (lado - figura.alto * bloque) // 2
    for x, y in figura.celdas:
        base = QColor(color_bloque(figura, x, y))
        rect = QRectF(x0 + x * bloque, y0 + y * bloque, bloque, bloque)
        p.fillRect(rect, base)
        if relieve:
            grosor = max(1, bloque // 7)
            p.fillRect(QRectF(rect.x(), rect.y(), bloque, grosor), base.lighter(125))
            p.fillRect(QRectF(rect.x(), rect.y(), grosor, bloque), base.lighter(125))
            p.fillRect(QRectF(rect.x(), rect.bottom() - grosor, bloque, grosor), base.darker(150))
            p.fillRect(QRectF(rect.right() - grosor, rect.y(), grosor, bloque), base.darker(150))
    p.end()
    return imagen


def png_bytes(imagen: QImage) -> bytes:
    datos = QByteArray()
    buffer = QBuffer(datos)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    imagen.save(buffer, "PNG")
    return bytes(datos)


def escribir_ico(ruta: Path, imagenes: list[QImage]) -> None:
    """ICO con una entrada PNG por resolución (formato admitido desde Windows Vista)."""
    pngs = [png_bytes(img) for img in imagenes]
    cabecera = struct.pack("<HHH", 0, 1, len(pngs))
    desplazamiento = 6 + 16 * len(pngs)
    entradas = b""
    for img, png in zip(imagenes, pngs):
        lado = img.width() if img.width() < 256 else 0
        entradas += struct.pack("<BBBBHHII", lado, lado, 0, 0, 1, 32, len(png), desplazamiento)
        desplazamiento += len(png)
    ruta.write_bytes(cabecera + entradas + b"".join(pngs))


def dibujar_check(lado: int) -> QImage:
    imagen = QImage(lado, lado, QImage.Format.Format_ARGB32_Premultiplied)
    imagen.fill(Qt.GlobalColor.transparent)
    p = QPainter(imagen)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setPen(QPen(QColor(tema.SOBRE_ACENTO), lado * 0.14, Qt.PenStyle.SolidLine,
                  Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    trazo = QPainterPath()
    trazo.moveTo(lado * 0.22, lado * 0.53)
    trazo.lineTo(lado * 0.42, lado * 0.72)
    trazo.lineTo(lado * 0.78, lado * 0.3)
    p.drawPath(trazo)
    p.end()
    return imagen


def main() -> None:
    app = QGuiApplication(sys.argv)  # noqa: F841
    MARCA.mkdir(parents=True, exist_ok=True)
    logo = svg_logo()
    (MARCA / "logo.svg").write_text(logo, encoding="utf-8")
    renderizar_svg(logo, 600, 520).save(str(MARCA / "logo.png"))
    logo_nombre = svg_logo_con_nombre()
    (MARCA / "logo_nombre.svg").write_text(logo_nombre, encoding="utf-8")
    renderizar_svg(logo_nombre, 1350, 390).save(str(MARCA / "logo_nombre.png"))
    (MARCA / "icono.svg").write_text(svg_icono(), encoding="utf-8")
    iconos = [dibujar_icono(lado) for lado in TAMANOS_ICO]
    escribir_ico(MARCA / "icono.ico", iconos)
    iconos[-1].save(str(MARCA / "icono_256.png"))
    dibujar_check(32).save(str(ICONOS / "check.png"))
    print("Identidad generada en", MARCA)


if __name__ == "__main__":
    main()
