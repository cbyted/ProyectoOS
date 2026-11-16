from entidades.proceso import Proceso
from politicas.mlfq import MLFQ

# "programa": [ ["CPU", 2], ["ES", 40], ["CPU", 1] ]


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
        reloj_actual=None,
    ) -> int:

        if not programa:
            raise ValueError("El programa no puede estar vacío.")

        rafaga_cpu = None

        for tipo, valor in programa:
            if tipo == "CPU":
                rafaga_cpu = valor

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
        return {
            "nombre": "MLFQ",
            "num_colas": self.planificador.num_colas,
            "quantums": self.planificador.quantums,
            "num_cpus": self.planificador.num_cpus,
        }
