from .entidades.proceso import Proceso
from .politicas.mlfq import MLFQ


class APIProcesos:
    def __init__(self, planificador: MLFQ) -> None:
        self.planificador = planificador
        self.pid_siguiente = 0
        self.procesos: list[Proceso] = []
        self.cola_listos = []

    # Devuelve el PID
    def crear_proceso(
        self,
        nombre: str,
        usuario: str,
        programa: list,
        memoria_bytes: int = 4096,
        cuota_marcos: int = 4,
        prioridad: int = 0,
    ) -> int:

        reloj_actual = 0
        if not programa:
            raise ValueError("El programa no puede estar vacío.")

        rafaga_cpu = sum(valor for tipo, valor in programa if tipo == "CPU")
        if rafaga_cpu <= 0:
            raise ValueError("El programa debe incluir una ráfaga de CPU positiva.")
        if reloj_actual is None:
            reloj_actual = 0

        pid = self.pid_siguiente
        proceso = Proceso(
            pid=pid,
            nombre=nombre,
            usuario=usuario,
            estado="NUEVO",
            tiempo_llegada=reloj_actual,
            rafaga_cpu=rafaga_cpu,
            memoria_bytes=memoria_bytes,
            cuota_marcos=cuota_marcos,
            prioridad=prioridad,
        )

        self.procesos.append(proceso)
        self.pid_siguiente += 1
        return pid

    # Devuelve el TID
    def crear_hilo(pid: int, programa: list) -> int:
        pass

    def terminar_proceso(self, pid: int) -> None:
        for proceso in self.procesos:
            if proceso.pid == pid:
                proceso.cambiar_estado("TERMINADO")

    # NUEVO, LISTO, EJECUTANDO, BLOQUEADO, TERMINADO
    def estado_proceso(self, pid: int):
        for proceso in self.procesos:
            if proceso.pid == pid:
                return proceso.estado

    # dicts: pid, nombre, usuario, e|stado, prioridad, cpu_usada, tiempo_espera
    def listar_procesos(self) -> list:
        return [
            {
                "pid": proceso.pid,
                "nombre": proceso.nombre,
                "usuario": proceso.usuario,
                "estado": proceso.estado,
                "prioridad": proceso.prioridad,
                "cpu_usada": proceso.cpu_usada,
                "tiempo_espera": proceso.tiempo_espera,
            }
            for proceso in self.procesos
        ]

    def cola_listos(self) -> list[Proceso]:
        return [list(cola) for cola in self.planificador.colas]

    def proceso_en_ejecucion(self, cpu: int = 0) -> int:
        if self.planificador.proceso_actual[cpu] is None:
            return None
        else:
            return self.planificador.proceso_actual[cpu].pid

    def metricas_planificacion(self, reloj_actual=None) -> dict:
        pass

    def politica_planificacion(self) -> str:
        return "MLFQ"


def _reloj_cero() -> int:
    return 0


_api = APIProcesos(MLFQ([4, 8], 1))
_reloj_actual = _reloj_cero


def _configurar(num_cpus: int, reloj_actual=None) -> APIProcesos:
    global _api, _reloj_actual
    _reloj_actual = reloj_actual or _reloj_cero
    _api = APIProcesos(MLFQ([4, 8], num_cpus))
    return _api


def crear_proceso(
    nombre: str,
    usuario: str,
    programa: list,
    memoria_bytes: int = 4096,
    cuota_marcos: int = 4,
    prioridad: int = 0,
) -> int:
    return _api.crear_proceso(
        nombre,
        usuario,
        programa,
        memoria_bytes,
        cuota_marcos,
        prioridad,
    )


def terminar_proceso(pid: int) -> None:
    _api.terminar_proceso(pid)


def estado_proceso(pid: int):
    return _api.estado_proceso(pid)


def listar_procesos() -> list:
    return _api.listar_procesos()


def cola_listos() -> list:
    return [proceso.pid for cola in _api.planificador.colas for proceso in cola]


def proceso_en_ejecucion(cpu: int = 0):
    return _api.proceso_en_ejecucion(cpu)


def politica_planificacion() -> str:
    return _api.politica_planificacion()
