from .entidades.proceso import Proceso
from .errores import ErrorNoExiste
from .politicas.mlfq import MLFQ
from . import disco, memoria


_INSTRUCCIONES = {"CPU", "ES", "MEM", "WAIT", "SIGNAL"}


class APIProcesos:
    def __init__(self, planificador: MLFQ) -> None:
        self.planificador = planificador
        self.pid_siguiente = 0
        self.procesos: list[Proceso] = []

    def _buscar(self, pid: int) -> Proceso:
        for proceso in self.procesos:
            if proceso.pid == pid:
                return proceso
        raise ErrorNoExiste(f"No existe el proceso {pid}.")

    def crear_proceso(
        self,
        nombre: str,
        usuario: str,
        programa: list,
        memoria_bytes: int = 4096,
        cuota_marcos: int = 4,
        prioridad: int = 0,
    ) -> int:
        if not programa:
            raise ValueError("El programa no puede estar vacío.")
        for instruccion in programa:
            if len(instruccion) != 2 or instruccion[0] not in _INSTRUCCIONES:
                raise ValueError(f"Instrucción inválida: {instruccion}.")

        rafaga_cpu = sum(v for tipo, v in programa if tipo == "CPU")
        pid = self.pid_siguiente
        proceso = Proceso(
            pid=pid,
            nombre=nombre,
            usuario=usuario,
            estado="NUEVO",
            tiempo_llegada=_reloj_actual(),
            rafaga_cpu=rafaga_cpu,
            memoria_bytes=memoria_bytes,
            cuota_marcos=cuota_marcos,
            prioridad=prioridad,
            programa=programa,  # <- antes no se pasaba
        )

        memoria.registrar_proceso(pid, memoria_bytes, cuota_marcos)
        self.procesos.append(proceso)
        self.pid_siguiente += 1
        return pid

    def crear_hilo(self, pid: int, programa: list) -> int:
        raise NotImplementedError  # Prototipo 2

    def terminar_proceso(self, pid: int) -> None:
        proceso = self._buscar(pid)
        if proceso.estado != "TERMINADO":
            self.planificador.finalizar(proceso, _reloj_actual())

    def desbloquear(self, pid: int) -> bool:
        """La llama el kernel cuando el disco termina una solicitud."""
        return self.planificador.desbloquear(pid)

    def estado_proceso(self, pid: int) -> str:
        return self._buscar(pid).estado

    def listar_procesos(self) -> list:
        return [
            {
                "pid": p.pid,
                "nombre": p.nombre,
                "usuario": p.usuario,
                "estado": p.estado,
                "prioridad": p.prioridad,
                "cpu_usada": p.cpu_usada,
                "tiempo_espera": p.tiempo_espera,
            }
            for p in self.procesos
        ]

    def cola_listos(self) -> list:
        return [p.pid for cola in self.planificador.colas for p in cola]

    def proceso_en_ejecucion(self, cpu: int = 0):
        actual = self.planificador.proceso_actual[cpu]
        return None if actual is None else actual.pid

    def metricas_planificacion(self) -> dict:
        return self.planificador.metricas(self.procesos)

    def politica_planificacion(self) -> str:
        return "MLFQ de 3 niveles (RR q=4, RR q=8, FCFS) con envejecimiento"


# ----------------------------------------------------------------------
# Hooks hacia otros subsistemas (importación perezosa: sin ciclos)
# ----------------------------------------------------------------------
def _hook_es(proceso, bloque):
    disco.encolar_solicitud_disco(proceso.pid, bloque, "L")


def _hook_mem(proceso, direccion) -> bool:
    return memoria.acceder_memoria(proceso.pid, direccion)["fallo_pagina"]


def _hook_liberar(proceso):
    memoria.liberar_memoria(proceso.pid)
    disco._cancelar_pid(proceso.pid)


def _reloj_cero() -> int:
    return 0


_api = None
_reloj_actual = _reloj_cero


def _configurar(num_cpus: int, reloj_actual=None) -> APIProcesos:
    global _api, _reloj_actual
    _reloj_actual = reloj_actual or _reloj_cero
    planificador = MLFQ([4, 8], num_cpus)
    planificador.hooks.update(
        {"ES": _hook_es, "MEM": _hook_mem, "LIBERAR": _hook_liberar}
    )
    _api = APIProcesos(planificador)
    return _api


_configurar(1)


def crear_proceso(
    nombre: str,
    usuario: str,
    programa: list,
    memoria_bytes: int = 4096,
    cuota_marcos: int = 4,
    prioridad: int = 0,
) -> int:
    return _api.crear_proceso(
        nombre, usuario, programa, memoria_bytes, cuota_marcos, prioridad
    )


def crear_hilo(pid: int, programa: list) -> int:
    return _api.crear_hilo(pid, programa)


def terminar_proceso(pid: int) -> None:
    _api.terminar_proceso(pid)


def estado_proceso(pid: int) -> str:
    return _api.estado_proceso(pid)


def listar_procesos() -> list:
    return _api.listar_procesos()


def cola_listos() -> list:
    return _api.cola_listos()


def proceso_en_ejecucion(cpu: int = 0):
    return _api.proceso_en_ejecucion(cpu)


def metricas_planificacion() -> dict:
    return _api.metricas_planificacion()


def politica_planificacion() -> str:
    return _api.politica_planificacion()
