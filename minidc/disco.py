from collections import OrderedDict


class GestorDisco:
    """SCAN (LOOK) con tope de espera, servicio por ticks y caché LRU."""

    ESPERA_LIMITE = (
        100  # a partir de aquí se atiende primero la más antigua (<200, RD1)
    )

    def __init__(self) -> None:
        self.bloques_totales = 0
        self.tam_bloque = 0
        self.capacidad_cache = 0
        self._cache: OrderedDict[int, None] = OrderedDict()
        self._reiniciar_estado()

    def _reiniciar_estado(self) -> None:
        self._siguiente_id = 0
        self._pendientes: list[dict] = []
        self._en_servicio: dict | None = None
        self._completadas: list[int] = []  # PIDs terminados en modo por lotes
        self._tick = 0
        self._direccion = 1
        self._solicitudes_atendidas = 0
        self._desplazamiento_total = 0
        self._posicion_cabezal = 0
        self._espera_maxima = 0
        self._cache.clear()
        self._aciertos_cache = 0
        self._fallos_cache = 0

    def configurar(
        self, bloques_totales: int, tam_bloque: int, cache_bloques: int
    ) -> None:
        valores = (bloques_totales, tam_bloque, cache_bloques)
        if any(isinstance(v, bool) or not isinstance(v, int) for v in valores):
            raise ValueError("La configuración del disco debe contener enteros.")
        if bloques_totales < 1 or tam_bloque < 1 or cache_bloques < 0:
            raise ValueError("La configuración del disco contiene valores inválidos.")
        self.bloques_totales = bloques_totales
        self.tam_bloque = tam_bloque
        self.capacidad_cache = cache_bloques
        self._reiniciar_estado()

    # ------------------------------------------------------------------
    def encolar_solicitud_disco(self, pid: int, bloque: int, operacion: str) -> int:
        if isinstance(pid, bool) or not isinstance(pid, int) or pid < 0:
            raise ValueError("El PID debe ser un entero no negativo.")
        if isinstance(bloque, bool) or not isinstance(bloque, int):
            raise TypeError("El bloque debe ser un entero.")
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
                "llegada": self._tick,
            }
        )
        return solicitud_id

    def cancelar_solicitudes(self, pid: int) -> None:
        """Descarta las solicitudes de un proceso que terminó."""
        self._pendientes = [s for s in self._pendientes if s["pid"] != pid]
        if self._en_servicio and self._en_servicio["solicitud"]["pid"] == pid:
            self._en_servicio = None

    # ------------------------------------------------------------------
    # Política: SCAN con tope de espera
    # ------------------------------------------------------------------
    def _elegir(self, pendientes, cabezal, direccion, tick):
        vencidas = [s for s in pendientes if tick - s["llegada"] >= self.ESPERA_LIMITE]
        if vencidas:
            return min(vencidas, key=lambda s: (s["llegada"], s["id"])), direccion
        for d in (direccion, -direccion):
            delante = [s for s in pendientes if (s["bloque"] - cabezal) * d >= 0]
            if delante:
                s = min(delante, key=lambda s: (abs(s["bloque"] - cabezal), s["id"]))
                return s, d
        raise RuntimeError("sin solicitudes")  # no ocurre si pendientes no está vacío

    def _orden_previsto(self) -> list[int]:
        pend = list(self._pendientes)
        cab, d, t = self._posicion_cabezal, self._direccion, self._tick
        orden = []
        if self._en_servicio:
            orden.append(self._en_servicio["solicitud"]["bloque"])
            t += self._en_servicio["restante"]
        while pend:
            s, d = self._elegir(pend, cab, d, t)
            pend.remove(s)
            orden.append(s["bloque"])
            t += 1 + abs(s["bloque"] - cab) // 10
            cab = s["bloque"]
        return orden

    def cola_disco(self) -> list[int]:
        return self._orden_previsto()

    # ------------------------------------------------------------------
    # Servicio
    # ------------------------------------------------------------------
    def _guardar_en_cache(self, bloque: int) -> None:
        if self.capacidad_cache:
            self._cache[bloque] = None
            self._cache.move_to_end(bloque)
            if len(self._cache) > self.capacidad_cache:
                self._cache.popitem(last=False)

    def _iniciar_servicio(self, s: dict) -> int:
        """Mueve el cabezal, actualiza la caché y devuelve el tiempo de servicio."""
        bloque = s["bloque"]
        if s["operacion"] == "L":
            if bloque in self._cache:
                self._aciertos_cache += 1
                self._cache.move_to_end(bloque)
                return 1  # acierto: sin movimiento del cabezal
            self._fallos_cache += 1
        distancia = abs(bloque - self._posicion_cabezal)
        self._desplazamiento_total += distancia
        self._posicion_cabezal = bloque
        self._guardar_en_cache(bloque)
        return 1 + distancia // 10

    def _registrar_fin(self, s: dict) -> None:
        self._solicitudes_atendidas += 1
        self._espera_maxima = max(self._espera_maxima, self._tick - s["llegada"])

    def _avanzar_tick(self) -> list[int]:
        """Avanza el disco 1 tick; devuelve los PID cuya E/S terminó."""
        self._tick += 1
        terminados = self._completadas
        self._completadas = []

        if self._en_servicio is None and self._pendientes:
            s, self._direccion = self._elegir(
                self._pendientes, self._posicion_cabezal, self._direccion, self._tick
            )
            self._pendientes.remove(s)
            self._en_servicio = {"solicitud": s, "restante": self._iniciar_servicio(s)}

        if self._en_servicio is not None:
            self._en_servicio["restante"] -= 1
            if self._en_servicio["restante"] <= 0:
                s = self._en_servicio["solicitud"]
                self._en_servicio = None
                self._registrar_fin(s)
                terminados.append(s["pid"])
        return terminados

    def procesar_disco(self) -> list[int]:
        """Modo por lotes: atiende todo lo pendiente sin avanzar el reloj del kernel."""
        atendidos = []
        if self._en_servicio is not None:
            s = self._en_servicio["solicitud"]
            self._tick += self._en_servicio["restante"]
            self._en_servicio = None
            self._registrar_fin(s)
            self._completadas.append(s["pid"])
            atendidos.append(s["bloque"])
        while self._pendientes:
            s, self._direccion = self._elegir(
                self._pendientes, self._posicion_cabezal, self._direccion, self._tick
            )
            self._pendientes.remove(s)
            self._tick += self._iniciar_servicio(s)
            self._registrar_fin(s)
            self._completadas.append(s["pid"])
            atendidos.append(s["bloque"])
        return atendidos

    # ------------------------------------------------------------------
    def metricas_disco(self) -> dict:
        return {
            "solicitudes_atendidas": self._solicitudes_atendidas,
            "desplazamiento_total": self._desplazamiento_total,
            "posicion_cabezal": self._posicion_cabezal,
            "espera_maxima": self._espera_maxima,
        }

    def info_cache(self) -> dict:
        accesos = self._aciertos_cache + self._fallos_cache
        return {
            "capacidad_bloques": self.capacidad_cache,
            "aciertos": self._aciertos_cache,
            "fallos": self._fallos_cache,
            "tasa_aciertos": self._aciertos_cache / accesos if accesos else 0.0,
        }

    def politica_disco(self) -> str:
        return "SCAN (LOOK) con tope de espera"


_gestor = GestorDisco()


def _configurar(bloques_totales: int, tam_bloque: int, cache_bloques: int) -> None:
    _gestor.configurar(bloques_totales, tam_bloque, cache_bloques)


def _avanzar_tick() -> list[int]:
    return _gestor._avanzar_tick()


def _cancelar_pid(pid: int) -> None:
    _gestor.cancelar_solicitudes(pid)


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
