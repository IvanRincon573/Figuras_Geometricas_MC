"""Pruebas del editor sin mostrar ventanas (plataforma «offscreen»)."""

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

from figuras_bloques import operaciones as op  # noqa: E402
from figuras_bloques.construccion import construir  # noqa: E402
from figuras_bloques.documento import FUSION_SILUETA, Documento, Objeto  # noqa: E402

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
    monkeypatch.setattr("PySide6.QtWidgets.QMessageBox.information", lambda *a, **k: None)
    return respuesta


@pytest.fixture
def ventana(app, ajustes_temporales, decision):
    from figuras_bloques.ui.ventana import VentanaPrincipal

    v = VentanaPrincipal()
    v.resize(1500, 900)
    v.show()
    app.processEvents()
    yield v
    v._guardado = v.documento
    v.close()


def hexagono(id_, x, z, **extra):
    extra.setdefault("tamano", 21)
    return Objeto(id_, f"Hexágono {id_}", "hexagono", x=x, z=z, **extra)


def con_documento(v, doc: Documento):
    v._empezar(doc, None)
    return v


def test_titulo_e_icono(ventana):
    assert "Hexabloq" in ventana.windowTitle()
    assert not QApplication.instance().windowIcon().isNull()
    assert len(ventana.documento.objetos) == 1


def test_anadir_no_reemplaza(ventana):
    total = len(ventana.documento.objetos)
    ventana._colocar(40, 10)
    ventana._colocar(-40, 10)
    assert len(ventana.documento.objetos) == total + 2
    assert ventana.seleccion == (ventana.documento.objetos[-1].id,)
    nuevo = ventana.documento.objetos[-1]
    x0, z0, x1, z1 = nuevo.limites()
    assert x0 <= -40 <= x1 and z0 <= 10 <= z1


def test_vista_no_cambia_el_diseno(ventana):
    doc = ventana.documento
    total = ventana.construccion.total
    ventana.lienzo.zoom(3.0)
    ventana.lienzo.zoom(0.1)
    ventana.ajustar_vista()
    ventana.centrar_vista()
    assert ventana.documento is doc and ventana.construccion.total == total


def test_seleccion_desde_lienzo_y_panel(ventana):
    con_documento(ventana, Documento((hexagono("o1", 0, 0), hexagono("o2", 40, 0))))
    lz = ventana.lienzo
    assert lz.objeto_en(10, 9).id == "o1"
    ventana._pedir_seleccion(("o1",), "reemplazar")
    ventana._pedir_seleccion(("o2",), "sumar")
    assert ventana.seleccion == ("o1", "o2")
    ventana._pedir_seleccion(("o1",), "alternar")
    assert ventana.seleccion == ("o2",)
    assert ventana.panel_objetos.seleccion_actual() == ("o2",)
    ventana.panel_objetos.arbol.topLevelItem(1).setSelected(True)
    assert set(ventana.seleccion) == {"o1", "o2"}


def test_arrastre_y_teclado_mueven_con_deshacer(ventana):
    con_documento(ventana, Documento((hexagono("o1", 0, 0), hexagono("o2", 40, 0))))
    ventana.set_seleccion(("o1",))
    ventana._arrastre_previo(3, 2)
    assert ventana.documento.buscar("o1").x == 0, "la vista previa no entra en el historial"
    assert ventana.lienzo.documento.buscar("o1").x == 3
    ventana._arrastre_final(5, 2)
    assert (ventana.documento.buscar("o1").x, ventana.documento.buscar("o1").z) == (5, 2)
    ventana.mover_seleccion(16, 0)
    ventana.mover_seleccion(1, 0)
    assert ventana.documento.buscar("o1").x == 22
    ventana.deshacer()
    assert ventana.documento.buscar("o1").x == 5, "los movimientos de teclado seguidos se deshacen juntos"
    ventana.deshacer()
    assert ventana.documento.buscar("o1").x == 0
    ventana.rehacer()
    assert ventana.documento.buscar("o1").x == 5


def test_teclas_flecha_en_lienzo(ventana, app):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    con_documento(ventana, Documento((hexagono("o1", 0, 0),)))
    ventana.set_seleccion(("o1",))
    ventana.lienzo.setFocus()
    QTest.keyClick(ventana.lienzo, Qt.Key.Key_Right)
    QTest.keyClick(ventana.lienzo, Qt.Key.Key_Down, Qt.KeyboardModifier.ShiftModifier)
    o = ventana.documento.buscar("o1")
    assert (o.x, o.z) == (1, 16)


def test_ajuste_a_chunk_al_arrastrar(ventana):
    con_documento(ventana, Documento((hexagono("o1", 3, 5),)))
    ventana.set_seleccion(("o1",))
    lz = ventana.lienzo
    lz.ajuste_chunk = True
    lz._desplazamiento = (0, 0)
    assert lz._ajustar_desplazamiento_a_chunk(10, 0) == (13, -5)
    assert lz._ajustar_desplazamiento_a_chunk(-2, -1) == (-3, -5)


def test_agrupar_fusionar_separar_y_deshacer(ventana):
    con_documento(ventana, Documento((hexagono("o1", 0, 0), hexagono("o2", 12, 0), hexagono("o3", 60, 0))))
    antes = ventana.construccion.total
    ventana.set_seleccion(("o1", "o2"))
    ventana._ejecutar("agrupar")
    assert ventana.documento.buscar("o1").grupo == ventana.documento.buscar("o2").grupo
    assert ventana.construccion.total == antes
    ventana.fusionar(FUSION_SILUETA, "contorno", "Base")
    assert [o.tipo for o in ventana.documento.objetos] == ["compuesta", "hexagono"], "la compuesta ocupa el lugar de su origen más alto"
    assert ventana.construccion.total < antes, "la silueta elimina las líneas internas"
    ventana._ejecutar("separar")
    assert [o.id for o in ventana.documento.objetos] == ["o1", "o2", "o3"]
    ventana.deshacer()
    ventana.deshacer()
    assert ventana.documento.buscar("o1").grupo is not None and ventana.construccion.total == antes
    ventana.deshacer()
    assert ventana.documento.buscar("o1").grupo is None


def test_duplicar_eliminar_y_bloqueo(ventana):
    con_documento(ventana, Documento((hexagono("o1", 0, 0), hexagono("o2", 30, 0, bloqueado=True))))
    ventana.set_seleccion(("o1",))
    ventana._ejecutar("duplicar")
    assert len(ventana.documento.objetos) == 3
    ventana.set_seleccion(("o2",))
    ventana.mover_seleccion(5, 0)
    assert ventana.documento.buscar("o2").x == 30
    ventana._ejecutar("eliminar")
    assert ventana.documento.buscar("o2") is not None
    ventana._alternar(("o2",), "bloqueado")
    ventana._ejecutar("eliminar")
    assert ventana.documento.buscar("o2") is None


def test_ocultos_no_cuentan_bloqueados_si(ventana):
    con_documento(ventana, Documento((hexagono("o1", 0, 0), hexagono("o2", 40, 0))))
    total = ventana.construccion.total
    ventana._alternar(("o2",), "visible")
    assert ventana.construccion.total == total // 2
    ventana._alternar(("o1",), "bloqueado")
    assert ventana.construccion.total == total // 2


def test_propiedades_editan_y_validan(ventana):
    con_documento(ventana, Documento((hexagono("o1", 0, 0),)))
    ventana.set_seleccion(("o1",))
    panel = ventana.propiedades
    assert panel.modo == "simple"
    panel.spin_tamano.setValue(31)
    assert ventana.documento.buscar("o1").tamano == 31
    panel.spin_tamano.setValue(0)
    assert ventana.documento.buscar("o1").tamano == 31
    assert "entre 1 y 1000" in panel.lbl_error.text()
    panel.spin_x.setValue(-17)
    assert ventana.documento.buscar("o1").x == -17
    panel.muestras["#B0503C"].click()
    assert ventana.documento.buscar("o1").color == "#B0503C"
    ventana.deshacer()
    assert ventana.documento.buscar("o1").color != "#B0503C"


def test_solo_parametros_relevantes(ventana):
    panel = ventana.propiedades
    ventana.set_seleccion(())
    assert panel.modo == "plantilla" and panel.btn_anadir.isVisibleTo(panel)
    panel.seleccionar_tipo("circulo")
    assert not panel.seccion_orientacion.isVisibleTo(panel)
    panel.seleccionar_tipo("triangulo")
    visibles = {o for o, b in panel.botones_orientacion.items() if b.isVisibleTo(panel)}
    assert visibles == {"arriba", "abajo", "izquierda", "derecha"}
    assert ventana.propiedades.plantilla().tipo == "triangulo"
    con_documento(ventana, Documento((hexagono("o1", 0, 0), hexagono("o2", 30, 0))))
    ventana.set_seleccion(("o1", "o2"))
    assert panel.modo == "varios" and panel.seccion_alinear.isVisibleTo(panel)
    assert not panel.seccion_tamano.isVisibleTo(panel)


def test_panel_construccion_por_ambito(ventana):
    con_documento(ventana, Documento((hexagono("o1", 0, 0), hexagono("o2", 40, 0, tamano=11))))
    ventana.set_seleccion(("o2",))
    panel = ventana.panel_construccion
    panel.set_ambito("seleccion")
    esperado = construir([ventana.documento.buscar("o2")])
    assert panel.dato_total.lbl_valor.text() == str(esperado.total)
    assert panel.modelo_chunks.rowCount() == len(esperado.por_chunk)
    panel.set_ambito("diseno")
    assert panel.dato_total.lbl_valor.text() == str(ventana.construccion.total)


def test_instrucciones_por_chunk(ventana):
    con_documento(ventana, Documento((hexagono("o1", -5, -5),)))
    texto = ventana.texto_instrucciones("chunks")
    for (cx, cz), n in ventana.construccion.por_chunk.items():
        assert f"Chunk ({cx}, {cz})" in texto
    assert f"TOTAL: {ventana.construccion.total} bloques únicos" in texto


def test_cursor_muestra_chunk_y_local(ventana):
    ventana._mostrar_cursor((-1, 16))
    assert "X -1 · Z 16 · chunk (-1, 1) · local (15, 0)" in ventana.lbl_cursor.text()


@pytest.mark.parametrize("fondo", ["claro", "oscuro", "transparente"])
@pytest.mark.parametrize("coordenadas", [False, True])
def test_png_contiene_exactamente_los_bloques(app, fondo, coordenadas):
    from figuras_bloques.ui.exportar import geometria_png, renderizar_png

    doc = Documento((
        Objeto("o1", "a", "hexagono", x=-20, z=-3, tamano=15, color="#FF0000"),
        Objeto("o2", "b", "circulo", x=-12, z=4, tamano=9, color="#0000FF", modo="relleno"),
    ))
    c = construir(doc.objetos)
    px = 6
    imagen = renderizar_png(c, px, cuadricula=True, chunks=True, coordenadas=coordenadas, fondo=fondo)
    _, _, origen = geometria_png(c, px, coordenadas)
    x0, z0, x1, z1 = c.limites
    encontrados = {}
    for z in range(z0 - 1, z1 + 2):
        for x in range(x0 - 1, x1 + 2):
            color = imagen.pixelColor(int(origen.x() + (x + 0.5) * px), int(origen.y() + (z + 0.5) * px))
            if color in (QColor("#FF0000"), QColor("#0000FF")):
                encontrados[(x, z)] = color.name().upper()
    assert encontrados == {(x, z): color for x, z, color in c.celdas()}


def test_guardar_abrir_y_cambios_pendientes(ventana, tmp_path):
    doc = Documento((hexagono("o1", 0, 0), hexagono("o2", 12, 0, color="#3F7FE0")))
    doc, _ = op.fusionar(doc, ["o1", "o2"], FUSION_SILUETA)
    con_documento(ventana, doc)
    ventana._colocar(50, 50)
    assert ventana.hay_cambios() and ventana.isWindowModified()
    ruta = tmp_path / "diseno.json"
    assert ventana._escribir(ruta)
    assert not ventana.hay_cambios() and "diseno.json" in ventana.windowTitle()
    guardado = ventana.documento
    ventana.mover_seleccion(3, 3)
    assert ventana.abrir_ruta(str(ruta))
    assert ventana.documento == guardado and not ventana.hay_cambios()


def test_abrir_diseno_version_1(ventana):
    archivo = RAIZ / "tests" / "datos" / "v1_hexagono_21_plano_contorno.json"
    assert ventana.abrir_ruta(str(archivo))
    (objeto,) = ventana.documento.objetos
    assert (objeto.tipo, objeto.tamano, objeto.x, objeto.z) == ("hexagono", 21, 0, 0)


def test_confirmacion_antes_de_descartar(ventana, decision):
    from figuras_bloques.ui import dialogos

    ventana._colocar(30, 30)
    decision["valor"] = dialogos.Decision.CANCELAR
    assert not ventana.close()
    assert ventana.isVisible() and decision["preguntas"] == 1
    decision["valor"] = dialogos.Decision.DESCARTAR
    ventana.nuevo()
    assert not ventana.documento.objetos and not ventana.hay_cambios()


def test_preferencias_persisten(app, ajustes_temporales, decision):
    from figuras_bloques.ui.ventana import VentanaPrincipal

    v = VentanaPrincipal()
    v.show()
    v.acc_chunks.setChecked(False)
    v.acc_fondo_claro.setChecked(True)
    v.acc_ajuste_chunk.setChecked(True)
    v.propiedades.seleccionar_tipo("circulo")
    app.processEvents()
    v._guardado = v.documento
    v.close()
    nueva = VentanaPrincipal()
    assert not nueva.acc_chunks.isChecked() and nueva.acc_fondo_claro.isChecked()
    assert nueva.lienzo.ajuste_chunk and nueva.lienzo.opciones.paleta.nombre == "claro"
    assert nueva.propiedades.plantilla().tipo == "circulo"
    assert nueva.ajustes.value("ventana/geometria") is not None
    nueva._guardado = nueva.documento
    nueva.close()


def test_atajos_principales(ventana):
    esperados = {
        ventana.acc_deshacer: "Ctrl+Z", ventana.acc_rehacer: "Ctrl+Y", ventana.acc_duplicar: "Ctrl+D",
        ventana.acc_agrupar: "Ctrl+G", ventana.acc_fusionar: "Ctrl+M", ventana.acc_guardar: "Ctrl+S",
        ventana.acc_png: "Ctrl+E", ventana.acc_anadir: "Insert", ventana.acc_chunks: "K",
        ventana.herramientas["mano"]: "H",
    }
    for accion, tecla in esperados.items():
        assert QKeySequence(tecla) in accion.shortcuts()


def test_deslizador_sincronizado(ventana):
    from figuras_bloques.ui.panel_propiedades import deslizador_desde_tamano, tamano_desde_deslizador

    tamanos = [tamano_desde_deslizador(p) for p in range(1001)]
    assert tamanos[0] == 1 and tamanos[-1] == 1000 and tamanos == sorted(tamanos)
    for t in (1, 2, 21, 100, 1000):
        assert tamano_desde_deslizador(deslizador_desde_tamano(t)) == t
    ventana.set_seleccion(())
    ventana.propiedades.spin_tamano.setValue(100)
    assert ventana.propiedades.deslizador.value() == deslizador_desde_tamano(100)


def test_recursos_de_marca(app):
    from figuras_bloques.ui import recursos

    assert all(recursos.comprobar().values())
    datos = recursos.ICONO_APP.read_bytes()
    _, tipo, cantidad = struct.unpack("<HHH", datos[:6])
    lados = {struct.unpack("<B", datos[6 + 16 * i: 7 + 16 * i])[0] or 256 for i in range(cantidad)}
    assert tipo == 1 and {16, 32, 256} <= lados
    for nombre in ("seleccionar", "mano", "chunks", "fusionar", "agrupar", "deshacer", "alinear_centro_x"):
        assert not recursos.icono(nombre).isNull()


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


def test_arrastre_devuelto_al_inicio_no_congela_la_vista(ventana, app):
    """Arrastrar una figura y soltarla donde estaba no debe dejar la vista previa activa."""
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtTest import QTest

    lz = ventana.lienzo
    objeto = ventana.documento.objetos[0]
    x0, z0, _, z1 = objeto.limites()
    vista, d = lz.vista(), lz.devicePixelRatioF()
    punto = QPoint(int(vista.px(x0 + 1.5) / d), int(vista.pz((z0 + z1) / 2) / d))
    QTest.mousePress(lz, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, punto)
    QTest.mouseMove(lz, punto + QPoint(60, 0))
    QTest.mouseMove(lz, punto + QPoint(1, 0))
    QTest.mouseRelease(lz, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, punto + QPoint(1, 0))
    app.processEvents()
    assert ventana.documento.objetos[0].x == objeto.x
    ventana.propiedades.spin_tamano.setValue(200)
    assert ventana.documento.objetos[0].tamano == 200
    assert lz.documento.objetos[0].tamano == 200, "el lienzo muestra el documento real"
    assert ventana.construccion.total == construir(ventana.documento.objetos).total
    ventana.set_seleccion(())
    assert ventana.propiedades.modo == "plantilla", "los paneles siguen sincronizados"
