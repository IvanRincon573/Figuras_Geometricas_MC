"""Pruebas de la interfaz sin mostrar ventanas (plataforma «offscreen»)."""

from __future__ import annotations

import json
import os
import struct
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QPointF, QSettings  # noqa: E402
from PySide6.QtGui import QColor, QKeySequence  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from figuras_bloques.geometria import TAMANO_MAXIMO, TAMANO_MINIMO, Configuracion, generar  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def app():
    from figuras_bloques.app import _crear_aplicacion

    return QApplication.instance() or _crear_aplicacion(["pruebas"])


@pytest.fixture
def ajustes_temporales(tmp_path):
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path))
    return tmp_path


@pytest.fixture
def decision(monkeypatch):
    from figuras_bloques.ui import dialogos

    respuesta = {"valor": dialogos.Decision.DESCARTAR, "preguntas": 0}

    def falsa(*_args):
        respuesta["preguntas"] += 1
        return respuesta["valor"]

    monkeypatch.setattr(dialogos, "preguntar_cambios", falsa)
    return respuesta


@pytest.fixture
def ventana(app, ajustes_temporales, decision):
    from figuras_bloques.ui.ventana import VentanaPrincipal

    v = VentanaPrincipal()
    v.resize(1300, 820)
    v.show()
    app.processEvents()
    yield v
    v._config_base = v.panel.configuracion()
    v.close()


def configurar(v, cfg: Configuracion) -> None:
    v.panel.set_configuracion(cfg)
    v.regenerar(reajustar=True)


def test_titulo_e_icono(ventana):
    assert "Hexabloq" in ventana.windowTitle()
    assert not QApplication.instance().windowIcon().isNull()


def test_zoom_y_desplazamiento_no_cambian_la_figura(ventana):
    configurar(ventana, Configuracion("hexagono", 40, "vertice", "contorno"))
    f = ventana.figura
    for accion in (lambda: ventana.lienzo.zoom(3.0), lambda: ventana.lienzo.zoom(0.2),
                   ventana.lienzo.centrar, ventana.lienzo.ajustar):
        accion()
    assert ventana.figura is f and ventana.lienzo.figura is f
    assert f.total == generar(f.config).total
    assert ventana.guia.modelo.rowCount() == f.alto
    assert ventana.guia.dato_total.lbl_valor.text() == str(f.total)


def test_color_y_modo_no_reinician_la_vista(ventana):
    configurar(ventana, Configuracion("hexagono", 30, "plano", "contorno"))
    ventana.lienzo.zoom(2.0)
    ventana.lienzo._origen += QPointF(37, -21)
    vista = (ventana.lienzo._escala, QPointF(ventana.lienzo._origen))
    ventana.panel.muestras["#B0503C"].click()
    ventana.panel.btn_relleno.click()
    assert ventana.figura.config.color == "#B0503C"
    assert ventana.figura.config.modo == "relleno"
    assert (ventana.lienzo._escala, ventana.lienzo._origen) == vista


def test_cambios_de_tamano_actualizan_todo(ventana):
    configurar(ventana, Configuracion("hexagono", 21, "plano", "relleno"))
    for valor in (10, 11, 250):
        ventana.panel.spin_tamano.setValue(valor)
        f = ventana.figura
        assert f.config.tamano == valor and f.ancho == valor
        assert ventana.guia.modelo.rowCount() == f.alto


def test_deslizador_sincronizado(ventana):
    from figuras_bloques.ui.panel_config import deslizador_desde_tamano, tamano_desde_deslizador

    assert tamano_desde_deslizador(0) == TAMANO_MINIMO
    assert tamano_desde_deslizador(1000) == TAMANO_MAXIMO
    tamanos = [tamano_desde_deslizador(p) for p in range(1001)]
    assert tamanos == sorted(tamanos)
    for t in (1, 2, 21, 100, 1000):
        assert tamano_desde_deslizador(deslizador_desde_tamano(t)) == t
    # En el extremo alto cada posición avanza ~2 bloques: el campo conserva el valor exacto.
    assert abs(tamano_desde_deslizador(deslizador_desde_tamano(999)) - 999) <= 2
    ventana.panel.spin_tamano.setValue(999)
    assert ventana.panel.spin_tamano.value() == 999 == ventana.figura.config.tamano
    ventana.panel.spin_tamano.setValue(100)
    assert ventana.panel.deslizador.value() == deslizador_desde_tamano(100)
    ventana.panel.deslizador.setValue(300)
    assert ventana.panel.spin_tamano.value() == tamano_desde_deslizador(300)
    assert ventana.figura.config.tamano == tamano_desde_deslizador(300)


def test_solo_parametros_relevantes(ventana):
    panel = ventana.panel
    visibles = lambda: {o for o, b in panel.botones_orientacion.items() if b.isVisibleTo(panel)}  # noqa: E731
    panel.seleccionar_figura("circulo")
    assert not panel.contenedor_orientacion.isVisibleTo(panel)
    panel.seleccionar_figura("triangulo")
    assert visibles() == {"arriba", "abajo", "izquierda", "derecha"}
    panel.seleccionar_figura("hexagono")
    assert visibles() == {"plano", "vertice"}
    assert "Ancho total" in panel.lbl_medida.text()


def test_tamano_no_valido_explica_como_corregirlo(ventana):
    ventana.panel.spin_tamano.setValue(0)
    assert ventana.figura is None
    assert ventana.panel.lbl_error.isVisibleTo(ventana.panel)
    assert "entre 1 y 1000" in ventana.panel.lbl_error.text()
    assert "Escribe un número" in ventana.panel.lbl_error.text()
    assert ventana.panel.spin_tamano.property("error") is True
    assert not ventana.acc_png.isEnabled() and not ventana.acc_guardar.isEnabled()
    ventana.panel.spin_tamano.setValue(12)
    assert ventana.figura is not None and not ventana.panel.lbl_error.isVisibleTo(ventana.panel)


def test_seleccion_de_fila_sincronizada(ventana):
    configurar(ventana, Configuracion("hexagono", 15, "plano", "contorno"))
    ventana.lienzo.set_fila(3)
    assert ventana.guia.tabla.currentIndex().row() == 3
    assert "Fila 4 de" in ventana.guia.lbl_fila.text()
    ventana.lienzo.mover_fila(1)
    assert ventana.guia.tabla.currentIndex().row() == 4
    ventana.guia.tabla.selectRow(7)
    assert ventana.lienzo.opciones.fila_resaltada == 7
    ventana.guia.btn_siguiente.click()
    assert ventana.lienzo.opciones.fila_resaltada == 8
    ventana.guia.btn_quitar.click()
    assert ventana.lienzo.opciones.fila_resaltada is None


def test_celda_bajo_cursor(ventana):
    configurar(ventana, Configuracion("circulo", 9, "", "relleno"))
    lz = ventana.lienzo
    d = lz.devicePixelRatioF()
    px = (lz._origen.x() + 4.5 * lz._escala) / d
    py = (lz._origen.y() + 4.5 * lz._escala) / d
    assert lz.celda_en(QPointF(px, py)) == (4, 4)
    ventana._mostrar_cursor((4, 4))
    assert "Columna 5 · Fila 5" in ventana.lbl_cursor.text()
    assert "en el centro" in ventana.lbl_cursor.text()


def test_zoom_en_barra_de_estado(ventana):
    ventana.lienzo.zoom(2.0)
    assert ventana.lbl_zoom.text().startswith("Zoom:")


@pytest.mark.parametrize("fondo", ["claro", "oscuro", "transparente"])
@pytest.mark.parametrize("cuadricula", [False, True])
def test_png_tiene_los_mismos_bloques(app, cuadricula, fondo):
    from figuras_bloques.ui.exportar import renderizar_png

    f = generar(Configuracion("hexagono", 23, "vertice", "contorno", "#FF0000"))
    px = 6
    img = renderizar_png(f, px, cuadricula=cuadricula, numeros=False, fondo=fondo)
    assert (img.width(), img.height()) == ((f.ancho + 2) * px, (f.alto + 2) * px)
    rojo = QColor("#FF0000")
    encontrados = {
        (x, y)
        for y in range(-1, f.alto + 1)
        for x in range(-1, f.ancho + 1)
        if img.pixelColor((x + 1) * px + px // 2, (y + 1) * px + px // 2) == rojo
    }
    assert encontrados == f.conjunto


def test_guardar_abrir_y_cambios_pendientes(ventana, tmp_path):
    configurar(ventana, Configuracion("triangulo", 17, "derecha", "relleno", "#3F7FE0"))
    assert ventana.hay_cambios() and ventana.isWindowModified()
    ruta = tmp_path / "t.json"
    assert ventana._escribir(ruta)
    assert not ventana.hay_cambios() and not ventana.isWindowModified()
    assert "t.json" in ventana.windowTitle()
    ventana.panel.spin_tamano.setValue(18)
    assert ventana.hay_cambios()
    assert ventana.abrir_ruta(str(ruta))
    assert ventana.figura.config == Configuracion("triangulo", 17, "derecha", "relleno", "#3F7FE0")
    assert ventana.panel.botones_orientacion["derecha"].isChecked()
    assert not ventana.hay_cambios()


def test_confirmacion_antes_de_descartar(ventana, decision):
    from figuras_bloques.ui import dialogos

    ventana.panel.spin_tamano.setValue(33)
    decision["valor"] = dialogos.Decision.CANCELAR
    assert not ventana.close()
    assert ventana.isVisible() and decision["preguntas"] == 1
    ventana.nuevo()
    assert ventana.figura.config.tamano == 33
    decision["valor"] = dialogos.Decision.DESCARTAR
    ventana.nuevo()
    assert ventana.figura.config.tamano == Configuracion().tamano
    assert not ventana.hay_cambios()


def test_preferencias_persisten(app, ajustes_temporales, decision):
    from figuras_bloques.ui.ventana import VentanaPrincipal

    v = VentanaPrincipal()
    v.show()
    v.acc_cuadricula.setChecked(False)
    v.acc_fondo_claro.setChecked(True)
    v.acc_guia.setChecked(False)
    configurar(v, Configuracion("circulo", 31, "", "relleno", "#E3B53A"))
    v.resize(1111, 777)
    app.processEvents()
    v._config_base = v.panel.configuracion()
    v.close()
    nueva = VentanaPrincipal()
    nueva.show()
    app.processEvents()
    assert not nueva.acc_cuadricula.isChecked()
    assert nueva.acc_fondo_claro.isChecked()
    assert nueva.lienzo.opciones.paleta.nombre == "claro"
    assert not nueva.acc_guia.isChecked()
    assert nueva.figura.config == Configuracion("circulo", 31, "", "relleno", "#E3B53A")
    # La pantalla virtual de las pruebas recorta la ventana; se comprueba que la geometría se guarda y se aplica.
    guardada = nueva.ajustes.value("ventana/geometria")
    assert guardada is not None and nueva.restoreGeometry(guardada)
    assert nueva.ajustes.value("ventana/divisor") is not None
    nueva.close()


def test_atajos_principales(ventana):
    esperados = {
        ventana.acc_nuevo: "Ctrl+N", ventana.acc_abrir: "Ctrl+O", ventana.acc_guardar: "Ctrl+S",
        ventana.acc_png: "Ctrl+E", ventana.acc_copiar: "Ctrl+Shift+C", ventana.acc_ajustar: "Ctrl+0",
        ventana.acc_ayuda: "F1", ventana.acc_cuadricula: "G",
    }
    for accion, tecla in esperados.items():
        assert QKeySequence(tecla) in accion.shortcuts()


def test_recursos_de_marca(app):
    from figuras_bloques.ui import recursos

    assert all(recursos.comprobar().values())
    for nombre in ("logo.svg", "logo.png", "logo_nombre.svg", "logo_nombre.png", "icono.svg", "icono.ico"):
        assert (recursos.MARCA / nombre).is_file()
    datos = recursos.ICONO_APP.read_bytes()
    _, tipo, cantidad = struct.unpack("<HHH", datos[:6])
    lados = {struct.unpack("<B", datos[6 + 16 * i : 7 + 16 * i])[0] or 256 for i in range(cantidad)}
    assert tipo == 1 and {16, 24, 32, 48, 256} <= lados


def test_recursos_desde_otro_directorio(tmp_path):
    salida = tmp_path / "estado.json"
    entorno = dict(os.environ, PYTHONPATH=str(RAIZ), QT_QPA_PLATFORM="offscreen")
    codigo = "import sys; from figuras_bloques.app import main; sys.exit(main())"
    resultado = subprocess.run(
        [sys.executable, "-c", codigo, "--comprobar-recursos", str(salida)],
        cwd=tmp_path, env=entorno, capture_output=True, timeout=120,
    )
    assert resultado.returncode == 0, resultado.stderr.decode(errors="replace")
    assert all(json.loads(salida.read_text(encoding="utf-8")).values())
