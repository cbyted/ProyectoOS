from collections import OrderedDict


class GestorDisco:
    """Administra solicitudes, el cabezal y una caché LRU de bloques."""

    def __init__(self) -> None:
        self.bloques_totales = 0
        self.tam_bloque = 0
        self.capacidad_cache = 0
        self._siguiente_id = 0
        self._pendientes: list[dict] = []
        self._solicitudes_atendidas = 0
        self._desplazamiento_total = 0
        self._posicion_cabezal = 0
        self._cache: OrderedDict[int, None] = OrderedDict()
        self._aciertos_cache = 0
        self._fallos_cache = 0

    def configurar(
        self, bloques_totales: int, tam_bloque: int, cache_bloques: int
    ) -> None:
        valores = (bloques_totales, tam_bloque, cache_bloques)
        if any(
            isinstance(valor, bool) or not isinstance(valor, int)
            for valor in valores
        ):
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
        self._cache.clear()
        self._aciertos_cache = 0
        self._fallos_cache = 0

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

    def _ordenar_solicitudes(self) -> list[dict]:
        """Ordena en una vuelta ascendente y luego atiende las de menor bloque."""
        posteriores = []
        anteriores = []
        for solicitud in self._pendientes:
            grupo = (
                posteriores
                if solicitud["bloque"] >= self._posicion_cabezal
                else anteriores
            )
            grupo.append(solicitud)

        posteriores.sort(key=lambda solicitud: solicitud["bloque"])
        anteriores.sort(key=lambda solicitud: solicitud["bloque"])
        return posteriores + anteriores

    def cola_disco(self) -> list[int]:
        """Devuelve los bloques pendientes en el orden C-SCAN previsto."""
        return [solicitud["bloque"] for solicitud in self._ordenar_solicitudes()]

    def procesar_disco(self) -> list[int]:
        """Atiende todas las solicitudes y devuelve su orden de finalización."""
        orden = self._ordenar_solicitudes()
        self._pendientes = []
        atendidos = []
        envolvio = False

        for solicitud in orden:
            bloque = solicitud["bloque"]
            if bloque in self._cache:
                # Una lectura o escritura reciente no requiere mover el cabezal.
                self._aciertos_cache += 1
                self._cache.move_to_end(bloque)
            else:
                self._fallos_cache += 1
                if bloque < self._posicion_cabezal and not envolvio:
                    # C-SCAN recorre hasta el último bloque y vuelve al inicio.
                    ultimo_bloque = self.bloques_totales - 1
                    self._desplazamiento_total += (
                        ultimo_bloque - self._posicion_cabezal
                    ) + ultimo_bloque
                    self._posicion_cabezal = 0
                    envolvio = True

                self._desplazamiento_total += abs(
                    bloque - self._posicion_cabezal
                )
                self._posicion_cabezal = bloque
                if self.capacidad_cache:
                    self._cache[bloque] = None
                    self._cache.move_to_end(bloque)
                    if len(self._cache) > self.capacidad_cache:
                        self._cache.popitem(last=False)

            self._solicitudes_atendidas += 1
            atendidos.append(bloque)
        return atendidos

    def metricas_disco(self) -> dict:
        return {
            "solicitudes_atendidas": self._solicitudes_atendidas,
            "desplazamiento_total": self._desplazamiento_total,
            "posicion_cabezal": self._posicion_cabezal,
        }

    def info_cache(self) -> dict:
        accesos = self._aciertos_cache + self._fallos_cache
        tasa = self._aciertos_cache / accesos if accesos else 0.0
        return {
            "capacidad_bloques": self.capacidad_cache,
            "aciertos": self._aciertos_cache,
            "fallos": self._fallos_cache,
            "tasa_aciertos": tasa,
        }

    def politica_disco(self) -> str:
        return "C-SCAN"


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
