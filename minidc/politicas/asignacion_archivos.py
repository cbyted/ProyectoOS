from ..errores import ErrorSistema


class AsignacionIndexada:
    """Asigna a cada archivo una lista de bloques no necesariamente contiguos."""

    def __init__(self, bloques_totales: int = 0) -> None:
        """Inicializa el administrador de bloques."""

        self.reiniciar(bloques_totales)

    def reiniciar(self, bloques_totales: int) -> None:
        """Inicializa nuevamente el espacio de almacenamiento."""

        if isinstance(bloques_totales, bool) or not isinstance(bloques_totales, int):
            raise ValueError("La cantidad de bloques debe ser un entero.")

        if bloques_totales < 0:
            raise ValueError("La cantidad de bloques no puede ser negativa.")

        self.bloques_totales = bloques_totales
        self._libres = list(range(bloques_totales))

    def asignar(self, cantidad: int) -> list[int]:

        if isinstance(cantidad, bool) or not isinstance(cantidad, int) or cantidad < 0:
            raise ValueError("La cantidad de bloques solicitada no es válida.")

        if cantidad > len(self._libres):
            raise ErrorSistema("no hay espacio suficiente en el disco.")

        asignados = self._libres[:cantidad]
        del self._libres[:cantidad]

        return asignados

    def liberar(self, bloques: list[int]) -> None:
        """Devuelve bloques ocupados al conjunto de bloques libres."""

        for bloque in bloques:
            if (
                isinstance(bloque, int)
                and not isinstance(bloque, bool)
                and 0 <= bloque < self.bloques_totales
                and bloque not in self._libres
            ):
                self._libres.append(bloque)

        self._libres.sort()

    def estado(self) -> dict:
        """Obtiene un resumen del estado actual del almacenamiento."""

        libres = sorted(self._libres)
        huecos = 0
        anterior = None

        for bloque in libres:
            if anterior is None or bloque != anterior + 1:
                huecos += 1
            anterior = bloque

        return {
            "bloques_totales": self.bloques_totales,
            "bloques_libres": len(libres),
            "huecos_libres": huecos,
        }
