from .entidades.marco import Marco
from .entidades.espacio_direcciones import EspacioDirecciones
from .errores import ErrorMemoria
from .politicas.lru import LRU
from collections import deque


class APIMemoria:
    def __init__(self):
        self.marcos = []
        self.marcos_fisicos = 0
        self.tam_pagina = 0
        self.fallos_pagina = 0
        self.reemplazos = 0
        self.escrituras_a_swap = 0
        self.accesos = 0
        self.tabla_espacio_direcciones = {}
        self.cuota_marcos = {}
        self.politica = LRU()
        self.reaccion_hiperpaginacion_activada = False
        self.ventana_fallos = deque(maxlen=10)

    def inicializar_memoria(self, config: dict) -> None:
        tam_pagina = config["tam_pagina"]
        marcos_fisicos = config["marcos_fisicos"]

        if tam_pagina <= 0:
            raise ValueError("tam_pagina debe ser mayor que cero")
        if marcos_fisicos < 0:
            raise ValueError("marcos_fisicos no puede ser negativo")

        self.tam_pagina = tam_pagina
        self.marcos_fisicos = marcos_fisicos
        self.marcos = [Marco(numero=i) for i in range(marcos_fisicos)]
        self.marcos_fisicos = config["marcos_fisicos"]
        self.reaccion_hiperpaginacion_activada = False

        # Reiniciar todo
        self.fallos_pagina = 0
        self.reemplazos = 0
        self.escrituras_a_swap = 0
        self.accesos = 0
        self.tabla_espacio_direcciones = {}
        self.cuota_marcos = {}
        self.ventana_fallos = deque(maxlen=10)

    def registrar_proceso(
        self,
        pid: int,
        memoria_bytes: int,
        cuota_marcos: int = 4,
    ) -> None:
        if self.tam_pagina <= 0:
            raise RuntimeError("La memoria aún no ha sido inicializada")
        if memoria_bytes <= 0:
            raise ValueError("memoria_bytes debe ser mayor que cero")
        if pid in self.tabla_espacio_direcciones:
            raise ValueError(f"El PID {pid} ya tiene memoria registrada")

        self.tabla_espacio_direcciones[pid] = EspacioDirecciones(
            pid=pid,
            memoria_bytes=memoria_bytes,
            tam_pagina=self.tam_pagina,
        )
        self.cuota_marcos[pid] = max(0, cuota_marcos)

    def acceder_memoria(self, pid, direccion_virtual, escritura=False) -> dict:
        if isinstance(direccion_virtual, bool) or not isinstance(
            direccion_virtual, int
        ):
            raise ErrorMemoria("La dirección virtual debe ser un entero.")
        espacio = self.tabla_espacio_direcciones.get(pid)
        if espacio is None or not espacio.direccion_valida(direccion_virtual):
            raise ErrorMemoria(
                f"Dirección virtual {direccion_virtual} inválida para PID {pid}"
            )

        pagina = espacio.obtener_pagina(direccion_virtual)
        entrada = espacio.paginas[pagina]

        # --- Acierto ---
        if entrada.presente:
            self.accesos += 1
            marco = self.marcos[entrada.marco]
            marco.registrar_uso(self.accesos, escritura)
            entrada.referenciada = True
            if escritura:
                entrada.modificada = True
            self.ventana_fallos.append((pid, 0))
            return {
                "marco": marco.numero,
                "fallo_pagina": False,
                "pagina_reemplazada": None,
            }

        # --- Fallo de página: primero la cuota, luego marcos libres, luego LRU ---
        residentes = [m for m in self.marcos if m.pid == pid]
        cuota = self.cuota_marcos.get(pid, 0)
        tope = cuota > 0 and len(residentes) >= cuota
        libres = [] if tope else [m for m in self.marcos if m.libre()]

        pagina_reemplazada = None
        if libres:
            marco = libres[0]
        else:
            candidatos = residentes if tope else self.marcos
            if not candidatos:
                raise ErrorMemoria("No hay marcos físicos disponibles.")
            marco = self.marcos[self.politica.pagina_menos_usada(candidatos)]
            pagina_reemplazada = (marco.pid, marco.pagina)

            anterior = self.tabla_espacio_direcciones.get(marco.pid)
            if anterior is not None:
                e = anterior.paginas[marco.pagina]
                e.marco, e.presente = None, False
                e.modificada = e.referenciada = False
            if marco.modificada:
                self.escrituras_a_swap += 1
            self.reemplazos += 1

        self.accesos += 1
        self.fallos_pagina += 1
        self.ventana_fallos.append((pid, 1))

        marco.asignar(pid, pagina, self.accesos)
        marco.modificada = escritura
        entrada.marco = marco.numero
        entrada.presente = True
        entrada.modificada = escritura
        entrada.referenciada = True
        return {
            "marco": marco.numero,
            "fallo_pagina": True,
            "pagina_reemplazada": pagina_reemplazada,
        }

    def tabla_paginas(self, pid: int) -> dict:
        espacio = self.tabla_espacio_direcciones.get(pid)

        if espacio is None:
            return {}

        return {
            pagina: {
                "marco": entrada.marco,
                "presente": entrada.presente,
                "modificada": entrada.modificada,
                "referenciada": entrada.referenciada,
            }
            for pagina, entrada in espacio.paginas.items()
        }

    # Liberar la memoria de un proceso
    def liberar_memoria(self, pid: int) -> int:
        liberados = 0

        for marco in self.marcos:
            if marco.pid == pid:
                marco.liberar()
                liberados += 1

        self.tabla_espacio_direcciones.pop(pid, None)
        self.cuota_marcos.pop(pid, None)
        return liberados

    def estado_memoria(self) -> dict:
        marcos_por_proceso = {pid: 0 for pid in self.tabla_espacio_direcciones}

        for marco in self.marcos:
            if not marco.libre() and marco.pid in marcos_por_proceso:
                marcos_por_proceso[marco.pid] += 1

        fragmentacion = sum(
            len(espacio.paginas) * self.tam_pagina - espacio.memoria_bytes
            for espacio in self.tabla_espacio_direcciones.values()
        )

        return {
            "marcos_totales": self.marcos_fisicos,
            "marcos_libres": sum(1 for marco in self.marcos if marco.libre()),
            "marcos_por_proceso": marcos_por_proceso,
            "fragmentacion_interna_bytes": fragmentacion,
        }

    def metricas_memoria(self) -> dict:
        tasa = self.fallos_pagina / self.accesos if self.accesos else 0.0

        return {
            "accesos": self.accesos,
            "fallos_pagina": self.fallos_pagina,
            "tasa_fallos": tasa,
            "reemplazos": self.reemplazos,
            "escrituras_a_swap": self.escrituras_a_swap,
        }

    def detectar_hiperpaginacion(self) -> bool:
        return (
            len(self.ventana_fallos) == self.ventana_fallos.maxlen
            and sum(f for _, f in self.ventana_fallos) >= 5
        )

    # --- Reacción a la hiperpaginación (RM2) ---
    def fallos_recientes(self) -> dict:
        cuenta = {}
        for pid, fallo in self.ventana_fallos:
            if fallo:
                cuenta[pid] = cuenta.get(pid, 0) + 1
        return cuenta

    def reiniciar_ventana(self) -> None:
        self.ventana_fallos.clear()

    def cuota_de(self, pid: int) -> int:
        return max(1, self.cuota_marcos.get(pid, 1))

    def suspender_proceso(self, pid: int) -> int:
        """Swap-out: libera todos los marcos pero conserva el espacio de direcciones."""
        espacio = self.tabla_espacio_direcciones.get(pid)
        if espacio is None:
            return 0
        liberados = 0
        for marco in self.marcos:
            if marco.pid == pid:
                if marco.modificada:
                    self.escrituras_a_swap += 1
                marco.liberar()
                liberados += 1
        for e in espacio.paginas.values():
            e.marco, e.presente = None, False
            e.modificada = e.referenciada = False
        return liberados

    def politica_reemplazo(self) -> str:
        return "LRU"


_api = APIMemoria()


def inicializar_memoria(config: dict) -> None:
    _api.inicializar_memoria(config)


def registrar_proceso(
    pid: int,
    memoria_bytes: int,
    cuota_marcos: int = 4,
) -> None:
    _api.registrar_proceso(pid, memoria_bytes, cuota_marcos)


def acceder_memoria(
    pid: int,
    direccion_virtual: int,
    escritura: bool = False,
) -> dict:
    return _api.acceder_memoria(pid, direccion_virtual, escritura)


def tabla_paginas(pid: int) -> dict:
    return _api.tabla_paginas(pid)


def liberar_memoria(pid: int) -> int:
    return _api.liberar_memoria(pid)


def estado_memoria() -> dict:
    return _api.estado_memoria()


def metricas_memoria() -> dict:
    return _api.metricas_memoria()


def detectar_hiperpaginacion() -> bool:
    return _api.detectar_hiperpaginacion()


def fallos_recientes() -> dict:
    return _api.fallos_recientes()


def reiniciar_ventana() -> None:
    _api.reiniciar_ventana()


def cuota_de(pid: int) -> int:
    return _api.cuota_de(pid)


def suspender_proceso(pid: int) -> int:
    return _api.suspender_proceso(pid)


def politica_reemplazo() -> str:
    return _api.politica_reemplazo()
