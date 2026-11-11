"""Guía de construcción por filas (sin dependencias de Qt).

Toda la información sale de :class:`~figuras_bloques.geometria.Figura`, por lo
que coincide siempre con lo que se dibuja y se exporta. Las filas y columnas se
numeran desde 1 (fila 1 = arriba, columna 1 = izquierda).
"""

from __future__ import annotations

from dataclasses import dataclass

from .geometria import MEDIDA_TAMANO, Figura, descripcion


@dataclass(frozen=True)
class FilaGuia:
    fila: int  # base 1
    bloques: int
    tramos: tuple[tuple[int, int], ...]  # base 1, ambos extremos incluidos

    @property
    def texto_tramos(self) -> str:
        return texto_tramos(self.tramos)


def texto_tramos(tramos: tuple[tuple[int, int], ...]) -> str:
    if not tramos:
        return "—"
    partes = []
    for a, b in tramos:
        partes.append(f"{a}" if a == b else f"{a}–{b}")
    return ", ".join(partes)


def texto_tramos_largo(tramos: tuple[tuple[int, int], ...]) -> str:
    """"columnas 3–8" · "columna 3 y columna 8" · "columnas 2–3 y columnas 8–9"."""
    if not tramos:
        return "fila vacía"
    partes = [f"columna {a}" if a == b else f"columnas {a}–{b}" for a, b in tramos]
    if len(partes) == 1:
        return partes[0]
    return ", ".join(partes[:-1]) + " y " + partes[-1]


def filas_guia(figura: Figura) -> list[FilaGuia]:
    resultado = []
    for y, fila in enumerate(figura.filas):
        tramos = tuple((x0 + 1, x1 + 1) for x0, x1 in fila)
        bloques = sum(b - a + 1 for a, b in tramos)
        resultado.append(FilaGuia(y + 1, bloques, tramos))
    return resultado


def formato_num(valor: float, decimales: int = 2) -> str:
    """Número con coma decimal y sin ceros sobrantes (8,66 · 10 · 5,5)."""
    texto = f"{valor:.{decimales}f}".rstrip("0").rstrip(".")
    return texto.replace(".", ",")


def posicion_centro(valor_celdas: float, nombre: str) -> str:
    """Describe una coordenada del centro dada en unidades de bloque.

    ``valor_celdas`` es la distancia al borde izquierdo/superior de la figura
    (la celda base 0 número ``i`` ocupa ``[i, i+1]``, así que su centro está en
    ``i + 0,5``, que corresponde a la columna/fila ``i + 1``).

    ``nombre`` es "columna" o "fila". Devuelve, p. ej., "columna 6" o
    "entre las columnas 5 y 6".
    """
    indice = valor_celdas + 0.5  # posición en numeración base 1
    if abs(indice - round(indice)) < 1e-9:
        return f"{nombre} {int(round(indice))}"
    if abs(indice - int(indice) - 0.5) < 1e-9:
        a = int(indice)
        plural = "columnas" if nombre == "columna" else "filas"
        return f"entre las {plural} {a} y {a + 1}"
    return f"{nombre} ≈ {formato_num(indice)}"


def resumen(figura: Figura) -> dict[str, str]:
    """Datos principales en texto, para la interfaz y el portapapeles."""
    cfg = figura.config
    datos = {
        "Figura": descripcion(cfg),
        "Medida pedida": f"{MEDIDA_TAMANO[cfg.figura]} = {cfg.tamano} bloques",
        "Ancho real": f"{figura.ancho} bloques (teórico {formato_num(figura.ancho_teorico)})",
        "Alto real": f"{figura.alto} bloques (teórico {formato_num(figura.alto_teorico)})",
        "Total de bloques": f"{figura.total}",
        "Centro": (
            f"{posicion_centro(figura.centro[1], 'fila')}, "
            f"{posicion_centro(figura.centro[0], 'columna')}"
        ),
    }
    if cfg.figura == "triangulo":
        datos["Centro"] += " (centroide)"
    lado = figura.lado_plano
    if lado is not None:
        if cfg.orientacion == "plano":
            datos["Lado superior"] = f"{lado} bloques (teórico {formato_num(cfg.tamano / 2)})"
        else:
            datos["Lados verticales"] = (
                f"{lado} bloques (teórico {formato_num(cfg.tamano / 3 ** 0.5)})"
            )
    return datos


def instrucciones(figura: Figura) -> str:
    """Texto completo con la guía, listo para copiar."""
    lineas = []
    for clave, valor in resumen(figura).items():
        lineas.append(f"{clave}: {valor}")
    lineas.append("")
    lineas.append(
        f"Columnas numeradas de 1 a {figura.ancho} de izquierda a derecha; "
        f"filas de 1 a {figura.alto} de arriba abajo."
    )
    lineas.append("Los tramos indican columna inicial–final (ambas incluidas).")
    lineas.append("")
    for f in filas_guia(figura):
        palabra = "bloque" if f.bloques == 1 else "bloques"
        lineas.append(f"Fila {f.fila}: {f.bloques} {palabra} — {texto_tramos_largo(f.tramos)}")
    lineas.append("")
    lineas.append(f"TOTAL: {figura.total} bloques")
    return "\n".join(lineas)
