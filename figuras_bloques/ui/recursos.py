"""Carga de logo, iconos e imágenes desde figuras_bloques/recursos."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QByteArray, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from ..geometria import Configuracion, generar
from . import tema

CARPETA = Path(__file__).resolve().parent.parent / "recursos"
MARCA = CARPETA / "marca"
ICONOS = CARPETA / "iconos"

ICONO_APP = MARCA / "icono.ico"
LOGO_SVG = MARCA / "logo.svg"
CHECK_PNG = ICONOS / "check.png"

TAMANOS_ICONO = (16, 18, 20, 24, 32)
BLOQUES_MINIATURA = 16  # con menos bloques el hexágono y el círculo se confunden


def _escala_pantalla() -> float:
    pantalla = QGuiApplication.primaryScreen()
    return max(1.0, pantalla.devicePixelRatio() if pantalla else 1.0)


def _svg_a_pixmap(datos: bytes, lado_logico: QSize) -> QPixmap:
    escala = _escala_pantalla()
    pix = QPixmap(round(lado_logico.width() * escala), round(lado_logico.height() * escala))
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    QSvgRenderer(QByteArray(datos)).render(p, QRectF(0, 0, pix.width(), pix.height()))
    p.end()
    pix.setDevicePixelRatio(escala)
    return pix


def _svg_coloreado(nombre: str, color: str) -> bytes:
    texto = (ICONOS / f"{nombre}.svg").read_text(encoding="utf-8")
    return texto.replace("currentColor", color).encode("utf-8")


@lru_cache(maxsize=None)
def icono(nombre: str) -> QIcon:
    """Icono de trazo con colores para estado normal, activo y desactivado."""
    resultado = QIcon()
    estados = (
        (QIcon.Mode.Normal, QIcon.State.Off, tema.TEXTO),
        (QIcon.Mode.Active, QIcon.State.Off, tema.TEXTO),
        (QIcon.Mode.Normal, QIcon.State.On, tema.ACENTO_HOVER),
        (QIcon.Mode.Active, QIcon.State.On, tema.ACENTO_HOVER),
        (QIcon.Mode.Disabled, QIcon.State.Off, tema.TEXTO_TENUE),
    )
    for modo, estado, color in estados:
        datos = _svg_coloreado(nombre, color)
        for lado in TAMANOS_ICONO:
            resultado.addPixmap(_svg_a_pixmap(datos, QSize(lado, lado)), modo, estado)
    return resultado


def logo(alto_logico: int) -> QPixmap:
    renderer = QSvgRenderer(str(LOGO_SVG))
    tam = renderer.defaultSize()
    ancho = round(alto_logico * tam.width() / tam.height())
    return _svg_a_pixmap(LOGO_SVG.read_bytes(), QSize(ancho, alto_logico))


def icono_app() -> QIcon:
    return QIcon(str(ICONO_APP))


@lru_cache(maxsize=None)
def icono_figura(figura: str, orientacion: str, modo: str = "relleno", lado: int = 32) -> QIcon:
    """Miniatura pixelada generada con la propia geometría de la aplicación."""
    fig = generar(Configuracion(figura, BLOQUES_MINIATURA, orientacion, modo))
    apagado = _pixmap_figura(fig, lado, tema.TEXTO_SECUNDARIO)
    encendido = _pixmap_figura(fig, lado, tema.ACENTO)
    resultado = QIcon()
    for modo_icono in (QIcon.Mode.Normal, QIcon.Mode.Active):
        resultado.addPixmap(apagado, modo_icono, QIcon.State.Off)
        resultado.addPixmap(encendido, modo_icono, QIcon.State.On)
    resultado.addPixmap(_pixmap_figura(fig, lado, tema.TEXTO_TENUE), QIcon.Mode.Disabled)
    return resultado


def _pixmap_figura(fig, lado: int, color: str) -> QPixmap:
    escala = _escala_pantalla()
    pix = QPixmap(round(lado * escala), round(lado * escala))
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    bloque = (pix.width() - 2) / max(fig.ancho, fig.alto)
    ox = (pix.width() - fig.ancho * bloque) / 2
    oy = (pix.height() - fig.alto * bloque) / 2
    for x, y in fig.celdas:
        p.fillRect(QRectF(ox + x * bloque, oy + y * bloque, bloque, bloque), QColor(color))
    p.end()
    pix.setDevicePixelRatio(escala)
    return pix


def comprobar() -> dict[str, bool]:
    """Estado de carga de cada recurso, para diagnosticar instalaciones y ejecutables."""
    estado = {str(r.relative_to(CARPETA)): r.is_file() for r in (ICONO_APP, LOGO_SVG, CHECK_PNG)}
    estado["icono_app_carga"] = not icono_app().isNull()
    estado["logo_carga"] = not logo(32).isNull()
    estado["iconos_svg"] = all(
        not icono(r.stem).pixmap(24, 24).isNull() for r in ICONOS.glob("*.svg")
    ) and any(ICONOS.glob("*.svg"))
    return estado
