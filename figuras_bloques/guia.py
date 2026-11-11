"""Guía de construcción por filas, con filas y columnas numeradas desde 1."""

from __future__ import annotations

from dataclasses import dataclass

from .geometria import MEDIDA_TAMANO, RAIZ3, Figura, descripcion

Tramos = tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class FilaGuia:
    fila: int
    bloques: int
    tramos: Tramos

    @property
    def texto_tramos(self) -> str:
        return texto_tramos(self.tramos)


def texto_tramos(tramos: Tramos) -> str:
    if not tramos:
        return "—"
    return ", ".join(f"{a}" if a == b else f"{a}–{b}" for a, b in tramos)


def texto_tramos_largo(tramos: Tramos) -> str:
    """Por ejemplo: "columnas 3–8" o "columna 3 y columna 8"."""
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
        resultado.append(FilaGuia(y + 1, sum(b - a + 1 for a, b in tramos), tramos))
    return resultado


def formato_num(valor: float, decimales: int = 2) -> str:
    """Coma decimal y sin ceros sobrantes: 8,66 · 10 · 5,5."""
    return f"{valor:.{decimales}f}".rstrip("0").rstrip(".").replace(".", ",")


def posicion_centro(distancia: float, nombre: str) -> str:
    """Traduce una distancia en bloques desde el borde a "columna 6" o "entre las columnas 5 y 6"."""
    indice = distancia + 0.5
    if abs(indice - round(indice)) < 1e-9:
        return f"{nombre} {round(indice)}"
    if abs(indice % 1 - 0.5) < 1e-9:
        anterior = int(indice)
        plural = "columnas" if nombre == "columna" else "filas"
        return f"entre las {plural} {anterior} y {anterior + 1}"
    return f"{nombre} ≈ {formato_num(indice)}"


def resumen(figura: Figura) -> dict[str, str]:
    cfg = figura.config
    cx, cy = figura.centro
    datos = {
        "Figura": descripcion(cfg),
        "Medida pedida": f"{MEDIDA_TAMANO[cfg.figura]} = {cfg.tamano} bloques",
        "Ancho real": f"{figura.ancho} bloques (teórico {formato_num(figura.ancho_teorico)})",
        "Alto real": f"{figura.alto} bloques (teórico {formato_num(figura.alto_teorico)})",
        "Total de bloques": f"{figura.total}",
        "Centro": f"{posicion_centro(cy, 'fila')}, {posicion_centro(cx, 'columna')}",
    }
    if cfg.figura == "triangulo":
        datos["Centro"] += " (centroide)"
    lado = figura.lado_plano
    if lado is not None:
        if cfg.orientacion == "plano":
            datos["Lado superior"] = f"{lado} bloques (teórico {formato_num(cfg.tamano / 2)})"
        else:
            datos["Lados verticales"] = f"{lado} bloques (teórico {formato_num(cfg.tamano / RAIZ3)})"
    return datos


def instrucciones(figura: Figura) -> str:
    lineas = [f"{clave}: {valor}" for clave, valor in resumen(figura).items()]
    lineas += [
        "",
        f"Columnas numeradas de 1 a {figura.ancho} de izquierda a derecha; "
        f"filas de 1 a {figura.alto} de arriba abajo.",
        "Los tramos indican columna inicial–final (ambas incluidas).",
        "",
    ]
    for f in filas_guia(figura):
        palabra = "bloque" if f.bloques == 1 else "bloques"
        lineas.append(f"Fila {f.fila}: {f.bloques} {palabra} — {texto_tramos_largo(f.tramos)}")
    lineas += ["", f"TOTAL: {figura.total} bloques"]
    return "\n".join(lineas)
