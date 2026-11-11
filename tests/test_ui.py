"""Pruebas de humo de la interfaz (sin ventana visible, plataforma «offscreen»)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QPointF, QSettings  # noqa: E402
from PySide6.QtGui import QColor  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from figuras_bloques.geometria import Configuracion, generar  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def ventana(app, tmp_path):
    # Ajustes en una carpeta temporal para no tocar los del usuario.
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path))
    from figuras_bloques.ui.ventana import VentanaPrincipal

    v = VentanaPrincipal()
    v.resize(1300, 800)
    v.show()
    app.processEvents()
    yield v
    v.close()


def test_zoom_y_desplazamiento_no_cambian_la_figura(ventana):
    ventana.aplicar_configuracion(Configuracion("hexagono", 40, "vertice", "contorno"))
    ventana.regenerar(reajustar=True)
    f = ventana.figura
    total = f.total
    ventana.lienzo.zoom(3.0)
    ventana.lienzo.zoom(0.2)
    ventana.lienzo.centrar()
    ventana.lienzo.ajustar()
    assert ventana.figura is f and ventana.lienzo.figura is f
    assert f.total == total == generar(f.config).total
    assert ventana.modelo.rowCount() == f.alto
    assert ventana.lbl_total.text() == str(total)


def test_cambios_de_parametros_actualizan_todo(ventana):
    ventana.aplicar_configuracion(Configuracion("hexagono", 21, "plano", "relleno"))
    ventana.regenerar()
    for valor in (10, 11, 250):
        ventana.spin_tamano.setValue(valor)
        f = ventana.figura
        assert f.config.tamano == valor and f.ancho == valor
        assert ventana.modelo.rowCount() == f.alto
    ventana.btn_contorno.click()
    assert ventana.figura.config.modo == "contorno"


def test_tamano_no_valido_muestra_mensaje(ventana):
    ventana.spin_tamano.setValue(0)
    assert ventana.figura is None
    assert not ventana.lbl_error.isHidden()
    assert "entre 1 y 1000" in ventana.lbl_error.text()
    assert not ventana.acc_png.isEnabled()
    ventana.spin_tamano.setValue(12)
    assert ventana.figura is not None and ventana.lbl_error.isHidden()


def test_seleccion_de_fila_sincronizada(ventana):
    ventana.aplicar_configuracion(Configuracion("hexagono", 15, "plano", "contorno"))
    ventana.regenerar()
    ventana.lienzo.set_fila(3)
    assert ventana.tabla.currentIndex().row() == 3
    ventana.lienzo.mover_fila(1)
    assert ventana.lienzo.opciones.fila_resaltada == 4
    ventana.tabla.selectRow(7)
    assert ventana.lienzo.opciones.fila_resaltada == 7
    ventana.lienzo.set_fila(None)
    assert ventana.lienzo.opciones.fila_resaltada is None


def test_celda_bajo_cursor(ventana):
    ventana.aplicar_configuracion(Configuracion("circulo", 9, "", "relleno"))
    ventana.regenerar(reajustar=True)
    lz = ventana.lienzo
    d = lz.devicePixelRatioF()
    px = (lz._origen.x() + 4.5 * lz._escala) / d
    py = (lz._origen.y() + 4.5 * lz._escala) / d
    assert lz.celda_en(QPointF(px, py)) == (4, 4)
    ventana._mostrar_cursor((4, 4))
    assert "Columna 5 · Fila 5" in ventana.lbl_cursor.text()
    assert "en el centro" in ventana.lbl_cursor.text()


@pytest.mark.parametrize("cuadricula", [False, True])
def test_png_tiene_los_mismos_bloques(app, cuadricula):
    """Cada bloque del PNG es un cuadrado del color elegido, y solo esos."""
    from figuras_bloques.ui.ventana import renderizar_png

    f = generar(Configuracion("hexagono", 23, "vertice", "contorno", "#FF0000"))
    px = 6
    img = renderizar_png(f, px, cuadricula=cuadricula, numeros=False, transparente=False)
    assert (img.width(), img.height()) == ((f.ancho + 2) * px, (f.alto + 2) * px)
    rojo = QColor("#FF0000")
    encontrados = set()
    for y in range(-1, f.alto + 1):
        for x in range(-1, f.ancho + 1):
            c = img.pixelColor((x + 1) * px + px // 2, (y + 1) * px + px // 2)
            if c == rojo:
                encontrados.add((x, y))
    assert encontrados == f.conjunto


def test_guardar_y_abrir_desde_ventana(ventana, tmp_path):
    from figuras_bloques.archivo import guardar

    f = generar(Configuracion("triangulo", 17, "derecha", "relleno", "#3F6FD8"))
    ruta = tmp_path / "t.json"
    guardar(f, ruta)
    ventana.abrir_ruta(str(ruta))
    assert ventana.figura.config == f.config
    assert ventana.combo_orient.currentData() == "derecha"
