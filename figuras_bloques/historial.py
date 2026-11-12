"""Historial de deshacer y rehacer basado en instantáneas inmutables del documento."""

from __future__ import annotations

from dataclasses import dataclass

from .documento import Documento

LIMITE = 200


@dataclass(frozen=True)
class Entrada:
    documento: Documento
    descripcion: str
    clave: str | None


class Historial:
    def __init__(self, inicial: Documento) -> None:
        self._entradas = [Entrada(inicial, "Inicio", None)]
        self._posicion = 0

    @property
    def actual(self) -> Documento:
        return self._entradas[self._posicion].documento

    def registrar(self, documento: Documento, descripcion: str, clave: str | None = None) -> None:
        """Añade un paso. Si ``clave`` coincide con la del último paso, lo sustituye
        (por ejemplo, varias pulsaciones seguidas sobre el mismo campo)."""
        if documento == self.actual:
            return
        del self._entradas[self._posicion + 1:]
        ultima = self._entradas[-1]
        if clave is not None and ultima.clave == clave and self._posicion > 0:
            self._entradas[-1] = Entrada(documento, descripcion, clave)
        else:
            self._entradas.append(Entrada(documento, descripcion, clave))
            if len(self._entradas) > LIMITE:
                del self._entradas[0]
        self._posicion = len(self._entradas) - 1

    def cortar_fusion(self) -> None:
        """Impide que el siguiente paso se combine con el anterior."""
        ultima = self._entradas[self._posicion]
        self._entradas[self._posicion] = Entrada(ultima.documento, ultima.descripcion, None)

    def puede_deshacer(self) -> bool:
        return self._posicion > 0

    def puede_rehacer(self) -> bool:
        return self._posicion < len(self._entradas) - 1

    def deshacer(self) -> Documento:
        if self.puede_deshacer():
            self._posicion -= 1
        return self.actual

    def rehacer(self) -> Documento:
        if self.puede_rehacer():
            self._posicion += 1
        return self.actual

    def descripcion_deshacer(self) -> str:
        return self._entradas[self._posicion].descripcion if self.puede_deshacer() else ""

    def descripcion_rehacer(self) -> str:
        return self._entradas[self._posicion + 1].descripcion if self.puede_rehacer() else ""

    def reiniciar(self, documento: Documento) -> None:
        self._entradas = [Entrada(documento, "Inicio", None)]
        self._posicion = 0
