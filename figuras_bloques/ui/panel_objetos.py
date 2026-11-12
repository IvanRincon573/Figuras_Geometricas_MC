"""Panel de objetos: lista en orden de apilado (arriba = encima), grupos y acciones."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QGridLayout,
    QHeaderView,
    QLabel,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..documento import NOMBRES_FUSION, NOMBRES_TIPO, Documento, Objeto
from . import recursos

COLUMNA_NOMBRE, COLUMNA_VISIBLE, COLUMNA_BLOQUEO = 0, 1, 2
ROL_ID = Qt.ItemDataRole.UserRole

ACCIONES = (
    ("duplicar", "Duplicar", "duplicar", "Duplicar la selección (Ctrl+D)"),
    ("eliminar", "Eliminar", "eliminar", "Eliminar la selección (Supr)"),
    ("agrupar", "Agrupar", "agrupar", "Agrupar: se mueven juntas pero siguen siendo independientes (Ctrl+G)"),
    ("desagrupar", "Desagrupar", "desagrupar", "Deshacer el grupo conservando las posiciones (Ctrl+Shift+G)"),
    ("fusionar", "Fusionar…", "fusionar", "Combinar en una figura compuesta (Ctrl+M)"),
    ("separar", "Separar", "separar", "Recuperar las figuras de una compuesta (Ctrl+Shift+M)"),
    ("subir", "Subir", "subir", "Subir en el orden de apilado (Ctrl+])"),
    ("bajar", "Bajar", "bajar", "Bajar en el orden de apilado (Ctrl+[)"),
)


def _descripcion(objeto: Objeto) -> str:
    if objeto.es_compuesta:
        return f"Compuesta · {NOMBRES_FUSION[objeto.fusion]} · {len(objeto.origenes)} figuras"
    return f"{NOMBRES_TIPO[objeto.tipo]} · {objeto.tamano} bloques · {objeto.modo}"


class PanelObjetos(QWidget):
    seleccionCambiada = Signal(tuple)
    alternarVisible = Signal(tuple)
    alternarBloqueo = Signal(tuple)
    renombrar = Signal(str, str)
    accion = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._sincronizando = False
        self._documento = Documento()
        self.setObjectName("panelGuia")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)
        self.arbol = QTreeWidget()
        self.arbol.setColumnCount(3)
        self.arbol.setHeaderLabels(("Objeto", "", ""))
        self.arbol.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.arbol.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked |
                                   QAbstractItemView.EditTrigger.EditKeyPressed)
        self.arbol.setIconSize(QSize(18, 18))
        self.arbol.setRootIsDecorated(True)
        self.arbol.setUniformRowHeights(True)
        cabecera = self.arbol.header()
        cabecera.setStretchLastSection(False)
        cabecera.setSectionResizeMode(COLUMNA_NOMBRE, QHeaderView.ResizeMode.Stretch)
        for columna in (COLUMNA_VISIBLE, COLUMNA_BLOQUEO):
            cabecera.setSectionResizeMode(columna, QHeaderView.ResizeMode.Fixed)
            cabecera.resizeSection(columna, 30)
        self.arbol.itemSelectionChanged.connect(self._al_cambiar_seleccion)
        self.arbol.itemClicked.connect(self._al_hacer_clic)
        self.arbol.itemChanged.connect(self._al_editar)
        lay.addWidget(self.arbol, 1)
        lay.addLayout(self._crear_botones())
        self.lbl_ayuda = QLabel("Arriba en la lista = encima en la construcción. Doble clic para renombrar.")
        self.lbl_ayuda.setObjectName("ayuda")
        self.lbl_ayuda.setWordWrap(True)
        lay.addWidget(self.lbl_ayuda)

    def _crear_botones(self) -> QGridLayout:
        rejilla = QGridLayout()
        rejilla.setSpacing(4)
        self.botones: dict[str, QToolButton] = {}
        for i, (clave, texto, icono, consejo) in enumerate(ACCIONES):
            boton = QToolButton()
            boton.setObjectName("segmento")
            boton.setIcon(recursos.icono(icono))
            boton.setIconSize(QSize(18, 18))
            boton.setToolTip(consejo)
            boton.setAccessibleName(texto)
            boton.clicked.connect(lambda _=False, c=clave: self.accion.emit(c))
            self.botones[clave] = boton
            rejilla.addWidget(boton, i // 4, i % 4)
        return rejilla

    def mostrar(self, doc: Documento, seleccion) -> None:
        self._documento = doc
        elegidos = set(seleccion)
        self._sincronizando = True
        try:
            self.arbol.clear()
            grupos_creados: dict[str, QTreeWidgetItem] = {}
            for objeto in reversed(doc.objetos):
                padre = None
                if objeto.grupo:
                    padre = grupos_creados.get(objeto.grupo)
                    if padre is None:
                        padre = self._elemento_grupo(doc, objeto.grupo)
                        grupos_creados[objeto.grupo] = padre
                elemento = self._elemento_objeto(objeto)
                (padre.addChild if padre else self.arbol.addTopLevelItem)(elemento)
                elemento.setSelected(objeto.id in elegidos)
            for padre in grupos_creados.values():
                padre.setExpanded(True)
                padre.setSelected(all(padre.child(i).isSelected() for i in range(padre.childCount())))
        finally:
            self._sincronizando = False
        self._actualizar_botones(doc.seleccionados(seleccion))

    def _elemento_objeto(self, objeto: Objeto) -> QTreeWidgetItem:
        elemento = QTreeWidgetItem([objeto.nombre, "", ""])
        elemento.setData(COLUMNA_NOMBRE, ROL_ID, ("objeto", objeto.id))
        elemento.setFlags(elemento.flags() | Qt.ItemFlag.ItemIsEditable)
        icono = "compuesta" if objeto.es_compuesta else None
        elemento.setIcon(COLUMNA_NOMBRE, recursos.icono(icono) if icono else
                         recursos.icono_figura(objeto.tipo, objeto.orientacion, objeto.modo, lado=18))
        elemento.setToolTip(COLUMNA_NOMBRE, f"{objeto.nombre}\n{_descripcion(objeto)}\nX {objeto.x}, Z {objeto.z}")
        self._iconos_estado(elemento, objeto.visible, objeto.bloqueado)
        return elemento

    def _elemento_grupo(self, doc: Documento, id_grupo: str) -> QTreeWidgetItem:
        grupo = doc.grupo(id_grupo)
        miembros = doc.miembros(id_grupo)
        elemento = QTreeWidgetItem([grupo.nombre if grupo else id_grupo, "", ""])
        elemento.setData(COLUMNA_NOMBRE, ROL_ID, ("grupo", id_grupo))
        elemento.setIcon(COLUMNA_NOMBRE, recursos.icono("grupo"))
        elemento.setToolTip(COLUMNA_NOMBRE, f"Grupo de {len(miembros)} objetos")
        self.arbol.addTopLevelItem(elemento)
        self._iconos_estado(elemento, all(m.visible for m in miembros), all(m.bloqueado for m in miembros))
        return elemento

    @staticmethod
    def _iconos_estado(elemento: QTreeWidgetItem, visible: bool, bloqueado: bool) -> None:
        elemento.setIcon(COLUMNA_VISIBLE, recursos.icono("visible" if visible else "oculto"))
        elemento.setToolTip(COLUMNA_VISIBLE, "Visible: cuenta en la construcción" if visible
                            else "Oculto: no cuenta ni se exporta")
        elemento.setIcon(COLUMNA_BLOQUEO, recursos.icono("bloqueado" if bloqueado else "desbloqueado"))
        elemento.setToolTip(COLUMNA_BLOQUEO, "Bloqueado: no se puede mover ni editar" if bloqueado
                            else "Desbloqueado")

    def _ids_de(self, elemento: QTreeWidgetItem) -> tuple[str, ...]:
        clase, valor = elemento.data(COLUMNA_NOMBRE, ROL_ID)
        if clase == "grupo":
            return tuple(o.id for o in self._documento.miembros(valor))
        return (valor,)

    def seleccion_actual(self) -> tuple[str, ...]:
        ids: list[str] = []
        for elemento in self.arbol.selectedItems():
            ids.extend(i for i in self._ids_de(elemento) if i not in ids)
        return tuple(o.id for o in self._documento.objetos if o.id in ids)

    def _al_cambiar_seleccion(self) -> None:
        if not self._sincronizando:
            self.seleccionCambiada.emit(self.seleccion_actual())

    def _al_hacer_clic(self, elemento: QTreeWidgetItem, columna: int) -> None:
        if columna == COLUMNA_VISIBLE:
            self.alternarVisible.emit(self._ids_de(elemento))
        elif columna == COLUMNA_BLOQUEO:
            self.alternarBloqueo.emit(self._ids_de(elemento))

    def _al_editar(self, elemento: QTreeWidgetItem, columna: int) -> None:
        if self._sincronizando or columna != COLUMNA_NOMBRE:
            return
        clase, valor = elemento.data(COLUMNA_NOMBRE, ROL_ID)
        nombre = elemento.text(COLUMNA_NOMBRE).strip()
        if nombre:
            self.renombrar.emit(f"{clase}:{valor}", nombre)

    def _actualizar_botones(self, seleccion: tuple[Objeto, ...]) -> None:
        hay = bool(seleccion)
        varios = len(seleccion) >= 2
        disponibles = {
            "duplicar": hay, "eliminar": hay, "subir": hay, "bajar": hay,
            "agrupar": varios, "fusionar": varios,
            "desagrupar": any(o.grupo for o in seleccion),
            "separar": len(seleccion) == 1 and seleccion[0].es_compuesta,
        }
        for clave, boton in self.botones.items():
            boton.setEnabled(disponibles[clave])
