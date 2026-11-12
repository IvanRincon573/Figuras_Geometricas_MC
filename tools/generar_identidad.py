"""Identidad vectorial de Hexabloq. Uso: python tools/generar_identidad.py.

El monograma usa una retícula de 8 unidades: hexágono escalonado y H calada.
Los SVG incluyen la tipografía como trazados y no necesitan fuentes al abrirse.
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import (  # noqa: E402
    QColor, QFont, QGuiApplication, QImage, QLinearGradient, QPainter,
    QPainterPath, QPen,
)
from PySide6.QtSvg import QSvgRenderer  # noqa: E402

from figuras_bloques.ui import tema  # noqa: E402

MARCA = RAIZ / "figuras_bloques" / "recursos" / "marca"
ICONOS = RAIZ / "figuras_bloques" / "recursos" / "iconos"
TAMANOS_ICO = (16, 20, 24, 32, 40, 48, 64, 128, 256)

# Coordenadas compartidas por el logo vectorial y los iconos pequeños.
CONTORNO = (
    (32, 16), (96, 16), (96, 24), (104, 24), (104, 40), (112, 40),
    (112, 56), (120, 56), (120, 72), (112, 72), (112, 88), (104, 88),
    (104, 104), (96, 104), (96, 112), (32, 112), (32, 104), (24, 104),
    (24, 88), (16, 88), (16, 72), (8, 72), (8, 56), (16, 56),
    (16, 40), (24, 40), (24, 24), (32, 24),
)
MONOGRAMA = (
    (32, 40), (48, 40), (48, 56), (80, 56), (80, 40), (96, 40),
    (96, 88), (80, 88), (80, 72), (48, 72), (48, 88), (32, 88),
)


def poligono_svg(puntos: tuple[tuple[int, int], ...]) -> str:
    primero, *resto = puntos
    return f"M{primero[0]} {primero[1]} " + " ".join(f"L{x} {y}" for x, y in resto) + " Z"


TRAZADO_MARCA = poligono_svg(CONTORNO) + " " + poligono_svg(MONOGRAMA)


def definiciones() -> str:
    return """<defs>
    <linearGradient id="jade" x1="0" y1="0" x2="1" y2="1">
      <stop stop-color="#B5FFDE"/>
      <stop offset=".45" stop-color="#57E6B0"/>
      <stop offset="1" stop-color="#1BA979"/>
    </linearGradient>
    <linearGradient id="placa" x1="0" y1="0" x2="1" y2="1">
      <stop stop-color="#203D34"/>
      <stop offset=".55" stop-color="#142922"/>
      <stop offset="1" stop-color="#0D1B18"/>
    </linearGradient>
  </defs>"""


def simbolo_svg(detalles: bool = True) -> str:
    cuerpo = f'<path d="{TRAZADO_MARCA}" fill="url(#jade)" fill-rule="evenodd"/>'
    if detalles:
        # Acentos de bloques en la periferia; el centro queda limpio y legible.
        cuerpo += """
    <path d="M32 16 H96 V24 H32 Z" fill="#FFFFFF" opacity=".16"/>
    <path d="M40 24 H48 V32 H40 Z M32 32 H40 V40 H32 Z"
          fill="#E3FFF2" opacity=".34"/>
    <path d="M80 96 H88 V104 H80 Z M88 88 H96 V96 H88 Z"
          fill="#087853" opacity=".24"/>
    <path d="M48 16 V32 M80 96 V112" fill="none" stroke="#0A6B4A"
          stroke-opacity=".12" stroke-width="1"/>
"""
    return cuerpo


def documento_svg(cuerpo: str, ancho: int, alto: int, titulo: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ancho} {alto}" '
        f'width="{ancho * 4}" height="{alto * 4}" role="img">\n'
        f"  <title>{titulo}</title>\n"
        "  <desc>Hexágono de bloques con una H en espacio negativo. Identidad de Hexabloq.</desc>\n"
        f"  {definiciones()}\n  {cuerpo}\n</svg>\n"
    )


def svg_logo() -> str:
    return documento_svg(simbolo_svg(), 128, 128, "Hexabloq · símbolo")


def fuente(tamano: int, peso: QFont.Weight = QFont.Weight.DemiBold) -> QFont:
    resultado = QFont("Segoe UI")
    resultado.setPixelSize(tamano)
    resultado.setWeight(peso)
    return resultado


def texto_vectorial(texto: str, tipografia: QFont, x: float, y: float, color: str) -> str:
    """Convierte las letras en curvas; conserva los huecos con la regla par-impar."""
    camino = QPainterPath()
    camino.addText(QPointF(x, y), tipografia, texto)
    partes: list[str] = []
    i = 0
    while i < camino.elementCount():
        e = camino.elementAt(i)
        if e.isMoveTo():
            partes.append(f"M{e.x:.3f} {e.y:.3f}")
        elif e.isLineTo():
            partes.append(f"L{e.x:.3f} {e.y:.3f}")
        elif e.type == QPainterPath.ElementType.CurveToElement:
            control = camino.elementAt(i + 1)
            final = camino.elementAt(i + 2)
            partes.append(f"C{e.x:.3f} {e.y:.3f} {control.x:.3f} {control.y:.3f} {final.x:.3f} {final.y:.3f}")
            i += 2
        i += 1
    return f'<path d="{" ".join(partes)}" fill="{color}" fill-rule="evenodd"/>'


def svg_logo_con_nombre(claro: bool = False) -> str:
    tipografia = fuente(68, QFont.Weight.Bold)
    tipografia.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, -2)
    palabra = texto_vectorial("Hexabloq", tipografia, 194, 114, "#172B24" if claro else "#EEF9F3")
    subtitulo_fuente = fuente(13, QFont.Weight.Medium)
    subtitulo_fuente.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2.1)
    subtitulo = texto_vectorial(
        "FIGURAS. BLOQUE A BLOQUE.", subtitulo_fuente, 199, 148,
        "#4E7263" if claro else "#96B9AA",
    )
    cuerpo = f'<g transform="translate(16 16) scale(1.25)">{simbolo_svg()}</g>\n{palabra}\n{subtitulo}'
    return documento_svg(cuerpo, 520, 192, "Hexabloq · logo con nombre")


def svg_icono() -> str:
    placa = (
        '<rect x="1" y="1" width="126" height="126" rx="28" '
        'fill="url(#placa)" stroke="#426454" stroke-opacity=".65"/>'
    )
    return documento_svg(placa + simbolo_svg(), 128, 128, "Hexabloq · icono de aplicación")


def renderizar_svg(svg: str, ancho: int, alto: int) -> QImage:
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    if not renderer.isValid():
        raise ValueError("SVG de identidad no válido")
    imagen = QImage(ancho, alto, QImage.Format.Format_ARGB32_Premultiplied)
    imagen.fill(Qt.GlobalColor.transparent)
    p = QPainter(imagen)
    p.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing)
    renderer.render(p, QRectF(0, 0, ancho, alto))
    p.end()
    return imagen


def dibujar_icono(lado: int) -> QImage:
    if lado >= 64:
        return renderizar_svg(svg_icono(), lado, lado)
    # Ajuste óptico: vértices en píxeles enteros, sin detalles ni bordes borrosos.
    imagen = QImage(lado, lado, QImage.Format.Format_ARGB32_Premultiplied)
    imagen.fill(Qt.GlobalColor.transparent)
    p = QPainter(imagen)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#142922"))
    p.drawRoundedRect(QRectF(0, 0, lado, lado), lado * .22, lado * .22)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
    camino = QPainterPath()
    camino.setFillRule(Qt.FillRule.OddEvenFill)
    for puntos in (CONTORNO, MONOGRAMA):
        for i, (x, y) in enumerate(puntos):
            punto = QPointF(round(x * lado / 128), round(y * lado / 128))
            (camino.moveTo if i == 0 else camino.lineTo)(punto)
        camino.closeSubpath()
    gradiente = QLinearGradient(0, 0, lado, lado)
    gradiente.setColorAt(0, QColor("#B5FFDE"))
    gradiente.setColorAt(1, QColor("#27BE89"))
    p.fillPath(camino, gradiente)
    p.end()
    return imagen


def png_bytes(imagen: QImage) -> bytes:
    datos = QByteArray()
    buffer = QBuffer(datos)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    if not imagen.save(buffer, "PNG"):
        raise OSError("No se pudo codificar el PNG")
    return bytes(datos)


def escribir_ico(ruta: Path, imagenes: list[QImage]) -> None:
    """ICO de 32 bits con una entrada PNG independiente por resolución."""
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


def guardar_png(imagen: QImage, nombre: str) -> None:
    if not imagen.save(str(MARCA / nombre)):
        raise OSError(f"No se pudo guardar {nombre}")


def vista_previa() -> QImage:
    """Lámina de revisión, con fondos claro/oscuro e iconos a tamaño real."""
    imagen = QImage(1440, 960, QImage.Format.Format_ARGB32_Premultiplied)
    imagen.fill(QColor("#0E1714"))
    p = QPainter(imagen)
    p.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)

    def texto(x: int, y: int, contenido: str, tamano: int, color: str) -> None:
        p.setFont(fuente(tamano, QFont.Weight.Medium))
        p.setPen(QColor(color))
        p.drawText(x, y, contenido)

    texto(64, 62, "HEXABLOQ / IDENTIDAD VISUAL", 14, "#8CA99B")
    texto(64, 100, "Geometría con identidad propia.", 26, "#EEF9F3")
    p.drawImage(QRectF(130, 140, 1110, 410), renderizar_svg(svg_logo_con_nombre(), 1560, 576))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#EAF3ED"))
    p.drawRoundedRect(QRectF(64, 582, 760, 244), 22, 22)
    p.drawImage(QRectF(105, 590, 650, 240), renderizar_svg(svg_logo_con_nombre(True), 1040, 384))
    p.setBrush(QColor("#182820"))
    p.drawRoundedRect(QRectF(852, 582, 524, 244), 22, 22)
    p.drawImage(QRectF(886, 620, 128, 128), dibujar_icono(128))
    texto(1042, 626, "ICONO DE ESCRITORIO", 13, "#96B9AA")
    x = 1042
    for lado in (16, 24, 32, 48, 64):
        p.drawImage(x, 705 - lado, dibujar_icono(lado))
        texto(x, 733, str(lado), 12, "#96B9AA")
        x += lado + 17
    texto(886, 789, "16–256 px · ajustado por resolución", 14, "#96B9AA")
    texto(64, 890, "HEXÁGONO ESCALONADO   /   MONOGRAMA H   /   ESMERALDA Y MENTA", 14, "#8CA99B")
    p.end()
    return imagen


def main() -> None:
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)  # noqa: F841
    MARCA.mkdir(parents=True, exist_ok=True)
    recursos = (
        ("logo", svg_logo(), 512, 512),
        ("logo_nombre", svg_logo_con_nombre(), 1560, 576),
        ("logo_nombre_claro", svg_logo_con_nombre(True), 1560, 576),
        ("icono", svg_icono(), 512, 512),
    )
    for nombre, svg, ancho, alto in recursos:
        (MARCA / f"{nombre}.svg").write_text(svg, encoding="utf-8")
        guardar_png(renderizar_svg(svg, ancho, alto), f"{nombre}.png")
    iconos = [dibujar_icono(lado) for lado in TAMANOS_ICO]
    escribir_ico(MARCA / "icono.ico", iconos)
    guardar_png(iconos[-1], "icono_256.png")
    guardar_png(vista_previa(), "vista_previa.png")
    if not dibujar_check(32).save(str(ICONOS / "check.png")):
        raise OSError("No se pudo guardar la marca de las casillas")
    print("Identidad generada en", MARCA)


if __name__ == "__main__":
    main()
