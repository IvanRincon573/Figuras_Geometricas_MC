"""Dibujo de una figura en bloques con QPainter.

Lo usan tanto el lienzo interactivo como la exportación a PNG, de modo que la
imagen exportada es exactamente lo que se ve (sin las ayudas visuales que no
se hayan pedido). Todas las medidas están en píxeles físicos.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from PySide6.QtCore import QLineF, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPen

from ..geometria import Figura


@dataclass
class OpcionesDibujo:
    cuadricula: bool = True
    ejes: bool = True
    centro: bool = True
    numeros: bool = True
    marco: bool = True  # recuadro del ancho × alto de la figura
    fila_resaltada: int | None = None  # base 0
    celda_cursor: tuple[int, int] | None = None
    fondo: QColor | None = None  # None = transparente


class Paleta:
    fondo = QColor("#F2EFE6")
    marco_relleno = QColor(0, 0, 0, 12)
    marco_borde = QColor("#9C968A")
    linea_menor = QColor("#D3CEC2")
    linea_mayor = QColor("#A8A194")
    eje_vertical = QColor(214, 69, 65, 200)
    eje_horizontal = QColor(52, 120, 214, 200)
    centro = QColor("#D64541")
    resaltado_banda = QColor(255, 196, 0, 70)
    resaltado_borde = QColor("#E69500")
    cursor = QColor(30, 30, 30, 170)
    numeros = QColor("#5E5A52")
    numeros_resaltado = QColor("#B36F00")


def _mas_oscuro(color: QColor, factor: int = 135) -> QColor:
    return color.darker(factor)


def _mas_claro(color: QColor, factor: int = 125) -> QColor:
    return color.lighter(factor)


def paso_etiquetas(escala: float, ancho_texto: float) -> int:
    """Cada cuántas filas/columnas cabe una etiqueta numérica."""
    for paso in (1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000):
        if paso * escala >= ancho_texto:
            return paso
    return 1000


def dibujar_figura(
    p: QPainter,
    figura: Figura,
    escala: float,
    origen: QPointF,
    visible: QRectF,
    opciones: OpcionesDibujo,
    color: QColor | None = None,
) -> None:
    """Dibuja la figura con la celda (0, 0) en ``origen`` y ``escala`` px por bloque.

    ``visible`` es el rectángulo (en píxeles) que hay que pintar; se usa para
    no dibujar nada fuera de pantalla.
    """
    s = escala
    ox, oy = origen.x(), origen.y()
    color = QColor(color or figura.config.color)

    if opciones.fondo is not None:
        p.fillRect(visible, opciones.fondo)

    # Rango de celdas visibles (con un margen de una celda).
    cx0 = math.floor((visible.left() - ox) / s) - 1
    cx1 = math.ceil((visible.right() - ox) / s) + 1
    cy0 = math.floor((visible.top() - oy) / s) - 1
    cy1 = math.ceil((visible.bottom() - oy) / s) + 1

    p.setRenderHint(QPainter.RenderHint.Antialiasing, False)

    # Recuadro con el ancho × alto de la figura.
    caja = QRectF(ox, oy, figura.ancho * s, figura.alto * s)
    if opciones.marco:
        p.fillRect(caja, Paleta.marco_relleno)

    # --- Cuadrícula ----------------------------------------------------------
    if opciones.cuadricula:
        menores: list[QLineF] = []
        mayores: list[QLineF] = []
        dibujar_menores = s >= 4
        paso_mayor = 5 if s * 5 >= 6 else (10 if s * 10 >= 6 else 50)
        top, bottom = visible.top(), visible.bottom()
        left, right = visible.left(), visible.right()
        for x in range(cx0, cx1 + 1):
            px = ox + x * s
            if x % paso_mayor == 0:
                mayores.append(QLineF(px, top, px, bottom))
            elif dibujar_menores:
                menores.append(QLineF(px, top, px, bottom))
        for y in range(cy0, cy1 + 1):
            py = oy + y * s
            if y % paso_mayor == 0:
                mayores.append(QLineF(left, py, right, py))
            elif dibujar_menores:
                menores.append(QLineF(left, py, right, py))
        if menores:
            p.setPen(QPen(Paleta.linea_menor, 1))
            p.drawLines(menores)
        p.setPen(QPen(Paleta.linea_mayor, 1))
        p.drawLines(mayores)

    # Banda de la fila resaltada (por debajo de los bloques).
    fila = opciones.fila_resaltada
    if fila is not None and 0 <= fila < figura.alto:
        banda = QRectF(visible.left(), oy + fila * s, visible.width(), s)
        p.fillRect(banda, Paleta.resaltado_banda)

    # --- Bloques -----------------------------------------------------------
    y_ini = max(0, cy0)
    y_fin = min(figura.alto - 1, cy1)
    rects: list[QRectF] = []
    celdas_visibles = 0
    for y in range(y_ini, y_fin + 1):
        for x0, x1 in figura.filas[y]:
            a, b = max(x0, cx0), min(x1, cx1)
            if a > b:
                continue
            rects.append(QRectF(ox + a * s, oy + y * s, (b - a + 1) * s, s))
            celdas_visibles += b - a + 1
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(color)
    if rects:
        p.drawRects(rects)

    # Separación entre bloques y relieve (solo si los bloques se ven grandes).
    if s >= 5 and celdas_visibles <= 80_000:
        lineas_osc: list[QLineF] = []
        lineas_cla: list[QLineF] = []
        relieve = s >= 12
        for y in range(y_ini, y_fin + 1):
            top = oy + y * s
            bot = top + s
            for x0, x1 in figura.filas[y]:
                a, b = max(x0, cx0), min(x1, cx1)
                if a > b:
                    continue
                left = ox + a * s
                right = ox + (b + 1) * s
                lineas_osc.append(QLineF(left, top, right, top))
                lineas_osc.append(QLineF(left, bot - 1, right, bot - 1))
                for x in range(a, b + 2):
                    px = ox + x * s
                    lineas_osc.append(QLineF(px, top, px, bot))
                    if relieve and x <= b:
                        # Luz arriba-izquierda dentro de cada bloque.
                        lineas_cla.append(QLineF(px + 1, top + 1, px + s - 2, top + 1))
                        lineas_cla.append(QLineF(px + 1, top + 1, px + 1, bot - 2))
        if relieve:
            p.setPen(QPen(_mas_claro(color, 125), 1))
            p.drawLines(lineas_cla)
        p.setPen(QPen(_mas_oscuro(color, 150), 1))
        p.drawLines(lineas_osc)

    if opciones.marco:
        p.setPen(QPen(Paleta.marco_borde, 1, Qt.PenStyle.DashLine))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(caja)

    # --- Fila resaltada: borde de sus bloques --------------------------------
    if fila is not None and 0 <= fila < figura.alto:
        grosor = max(2.0, min(4.0, s / 6))
        p.setPen(QPen(Paleta.resaltado_borde, grosor))
        p.setBrush(Qt.BrushStyle.NoBrush)
        for x0, x1 in figura.filas[fila]:
            p.drawRect(QRectF(ox + x0 * s, oy + fila * s, (x1 - x0 + 1) * s, s))

    # --- Ejes y centro -------------------------------------------------------
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    ccx = ox + figura.centro[0] * s
    ccy = oy + figura.centro[1] * s
    if opciones.ejes:
        grosor = max(1.5, min(3.0, s / 8))
        pen_v = QPen(Paleta.eje_vertical, grosor, Qt.PenStyle.DashLine)
        p.setPen(pen_v)
        p.drawLine(QLineF(ccx, visible.top(), ccx, visible.bottom()))
        pen_h = QPen(Paleta.eje_horizontal, grosor, Qt.PenStyle.DashLine)
        p.setPen(pen_h)
        p.drawLine(QLineF(visible.left(), ccy, visible.right(), ccy))
    if opciones.centro:
        r = max(4.0, min(10.0, s * 0.35))
        p.setPen(QPen(QColor("white"), 3))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(ccx, ccy), r, r)
        p.setPen(QPen(Paleta.centro, 2))
        p.drawEllipse(QPointF(ccx, ccy), r, r)
        p.drawLine(QLineF(ccx - r * 1.6, ccy, ccx + r * 1.6, ccy))
        p.drawLine(QLineF(ccx, ccy - r * 1.6, ccx, ccy + r * 1.6))

    # --- Celda bajo el cursor --------------------------------------------------
    if opciones.celda_cursor is not None and s >= 3:
        x, y = opciones.celda_cursor
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        p.setPen(QPen(Paleta.cursor, 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(QRectF(ox + x * s, oy + y * s, s, s))

    # --- Numeración de filas y columnas -------------------------------------
    if opciones.numeros and s >= 2:
        _dibujar_numeros(p, figura, s, ox, oy, visible, cx0, cx1, cy0, cy1, fila)


def _dibujar_numeros(p, figura, s, ox, oy, visible, cx0, cx1, cy0, cy1, fila) -> None:
    tam = max(7.0, min(13.0, s * 0.55))
    fuente = QFont("Segoe UI")
    fuente.setPixelSize(int(round(tam * 1.0)))
    p.setFont(fuente)
    fm = QFontMetricsF(fuente)
    ancho_txt = fm.horizontalAdvance(str(max(figura.ancho, figura.alto))) + 6
    alto_txt = fm.height()

    # Columnas, encima del recuadro (pegadas al borde superior visible si hace falta).
    paso = paso_etiquetas(s, ancho_txt)
    y_txt = max(visible.top() + 2, oy - alto_txt - 3)
    for x in range(max(0, cx0), min(figura.ancho - 1, cx1) + 1):
        n = x + 1
        if n != 1 and n % paso != 0 and n != figura.ancho:
            continue
        if n == figura.ancho and paso > 1 and n % paso != 0 and (n % paso) * s < ancho_txt:
            continue
        rect = QRectF(ox + x * s + s / 2 - ancho_txt / 2, y_txt, ancho_txt, alto_txt)
        p.setPen(Paleta.numeros)
        p.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(n))

    # Filas, a la izquierda del recuadro.
    paso_f = paso_etiquetas(s, alto_txt + 2)
    x_txt = max(visible.left() + 2, ox - ancho_txt - 4)
    for y in range(max(0, cy0), min(figura.alto - 1, cy1) + 1):
        n = y + 1
        es_fila = fila == y
        if not es_fila and n != 1 and n % paso_f != 0 and n != figura.alto:
            continue
        if not es_fila and n == figura.alto and paso_f > 1 and (n % paso_f) * s < alto_txt + 2:
            continue
        rect = QRectF(x_txt, oy + y * s + s / 2 - alto_txt / 2, ancho_txt, alto_txt)
        if es_fila:
            fuente_b = QFont(fuente)
            fuente_b.setBold(True)
            p.setFont(fuente_b)
            p.setPen(Paleta.numeros_resaltado)
            p.drawText(rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, str(n))
            p.setFont(fuente)
        else:
            p.setPen(Paleta.numeros)
            p.drawText(rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, str(n))
