class GestorDisco:
    """Registra solicitudes y ofrece un servicio FIFO"""

    def __init__(self) -> None:
        self.bloques_totales = 0
        self.tam_bloque = 0
        self.capacidad_cache = 0
        self._siguiente_id = 0
        self._pendientes: list[dict] = []
        self._solicitudes_atendidas = 0
        self._desplazamiento_total = 0
        self._posicion_cabezal = 0

    def configurar(
        self, bloques_totales: int, tam_bloque: int, cache_bloques: int
    ) -> None:
        valores = (bloques_totales, tam_bloque, cache_bloques)
        if any(isinstance(valor, bool) or not isinstance(valor, int) for valor in valores):
            raise ValueError("La configuración del disco debe contener enteros.")
        if bloques_totales < 1 or tam_bloque < 1 or cache_bloques < 0:
            raise ValueError("La configuración del disco contiene valores inválidos.")

        self.bloques_totales = bloques_totales
        self.tam_bloque = tam_bloque
        self.capacidad_cache = cache_bloques
        self._siguiente_id = 0
        self._pendientes = []
        self._solicitudes_atendidas = 0
        self._desplazamiento_total = 0
        self._posicion_cabezal = 0

    def encolar_solicitud_disco(self, pid: int, bloque: int, operacion: str) -> int:
        if isinstance(pid, bool) or not isinstance(pid, int) or pid < 0:
            raise ValueError("El PID debe ser un entero no negativo.")
        if isinstance(bloque, bool) or not isinstance(bloque, int):
            raise ValueError("El bloque debe ser un entero.")
        if not 0 <= bloque < self.bloques_totales:
            raise ValueError("El bloque solicitado está fuera del disco.")
        if not isinstance(operacion, str) or operacion.upper() not in ("L", "E"):
            raise ValueError("La operación debe ser 'L' (lectura) o 'E' (escritura).")

        solicitud_id = self._siguiente_id
        self._siguiente_id += 1
        self._pendientes.append(
            {
                "id": solicitud_id,
                "pid": pid,
                "bloque": bloque,
                "operacion": operacion.upper(),
            }
        )
        return solicitud_id

    def procesar_disco(self) -> list[int]:
        """Atiende las solicitudes pendientes en orden de llegada (FIFO)."""
        atendidos = []
        while self._pendientes:
            solicitud = self._pendientes.pop(0)
            bloque = solicitud["bloque"]
            self._desplazamiento_total += abs(bloque - self._posicion_cabezal)
            self._posicion_cabezal = bloque
            self._solicitudes_atendidas += 1
            atendidos.append(bloque)
        return atendidos

    def cola_disco(self) -> list[int]:
        return [solicitud["bloque"] for solicitud in self._pendientes]

    def metricas_disco(self) -> dict:
        return {
            "solicitudes_atendidas": self._solicitudes_atendidas,
            "desplazamiento_total": self._desplazamiento_total,
            "posicion_cabezal": self._posicion_cabezal,
        }

    def info_cache(self) -> dict:
        # La caché se deja preparada para la implementación avanzada.
        return {
            "capacidad_bloques": self.capacidad_cache,
            "aciertos": 0,
            "fallos": 0,
            "tasa_aciertos": 0.0,
        }

    def politica_disco(self) -> str:
        return "FCFS (implementación básica provisional)"


_gestor = GestorDisco()


def _configurar(bloques_totales: int, tam_bloque: int, cache_bloques: int) -> None:
    _gestor.configurar(bloques_totales, tam_bloque, cache_bloques)


def encolar_solicitud_disco(pid: int, bloque: int, operacion: str) -> int:
    return _gestor.encolar_solicitud_disco(pid, bloque, operacion)


def procesar_disco() -> list[int]:
    return _gestor.procesar_disco()


def cola_disco() -> list[int]:
    return _gestor.cola_disco()


def metricas_disco() -> dict:
    return _gestor.metricas_disco()


def info_cache() -> dict:
    return _gestor.info_cache()


def politica_disco() -> str:
    return _gestor.politica_disco()
