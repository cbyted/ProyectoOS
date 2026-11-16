from ..entidades.proceso import Proceso
from collections import deque

"""
Implementar Miultilevel Feedback Queue
El algoritmo está limitado a tres 3 colas.
El número de quantums correstone al numero de colas - 1
"""


class MLFQ:
    def __init__(
        self,
        quantums: list[int],
        num_cpus: int,
    ) -> None:
        # El número de colas que usa esta Implementación
        self.num_colas = 3

        # El número de CPUs
        self.num_cpus = num_cpus

        # Los quantums para cada cola
        self.quantums = quantums

        # Cola de procesos listos
        self.colas = [deque() for _ in range(self.num_colas)]

        # Cola de procesos terminados
        self.terminados: deque[Proceso] = deque()

        # Proceso en ejecución
        self.proceso_actual = [None] * num_cpus

        # El número de cola que se está usando
        self.nivel_actual = [None] * num_cpus

        # El tiempo que falta para que el proceso termine
        self.quantum_restante = [0] * num_cpus

        # El tiempo de ocupación de cada CPU
        self.ticks_ocupados = [0] * self.num_cpus

    # Inserta un nuevo proceso listo a la cola de mayor prioridad basandose en
    # su prioridad al momento de hacer la inserción
    def nuevo(self, proceso: Proceso):
        cola = self.colas[0]

        pos = len(cola)
        for i, actual in enumerate(cola):
            if proceso.prioridad < actual.prioridad:
                pos = i
                break

        cola.insert(pos, proceso)

    # Elegir el proceso de mayor prioridad
    def elegir_proceso(self, cpu: int) -> None:
        if self.proceso_actual[cpu] is not None:
            return

        for nivel, cola in enumerate(self.colas):
            if cola:
                proceso = cola.popleft()
                self.proceso_actual[cpu] = proceso
                self.nivel_actual[cpu] = nivel

                # La última cola es FCFS y no usa quantum.
                if nivel < self.num_colas - 1:
                    self.quantum_restante[cpu] = self.quantums[nivel]
                return

    """
    Estas funciones se pueden llamar para calcular las metricas de 
    los procesos terminados.
    """

    def calcular_tiempo_espera(self, cola: list[Proceso]) -> list[int]:
        tiempos = []
        for i in range(len(cola)):
            tiempos.append(cola[i].tiempo_espera)
        return tiempos

    def calcular_tiempo_retorno(self, cola: list[Proceso]) -> list[int]:
        tiempos = []
        for i in range(len(cola)):
            tiempos.append(cola[i].tiempo_retorno)
        return tiempos

    def calcular_tiempo_finalizacion(self, cola: list[Proceso]) -> list[int]:
        tiempos = []
        for i in range(len(cola)):
            tiempos.append(cola[i].tiempo_finalizacion)
        return tiempos

    def calcular_tiempo_restante(self, cola: deque[Proceso]) -> list[int]:
        return [proc.rafaga_cpu for proc in cola]

    def actualizar_tiempo_espera(self, proceso: Proceso, reloj_actual: int) -> int:
        proceso.tiempo_espera += reloj_actual - proceso.tiempo_finalizacion

    # Algoritmo para la última cola
    def first_come_first_served(self, cpu: int, reloj_actual: int) -> None:
        self.proceso_actual[cpu].rafaga_cpu -= 1
        self.proceso_actual[cpu].cpu_usada += 1
        if self.proceso_actual[cpu] is not None:
            self.ticks_ocupados[cpu] += 1

        if self.proceso_actual[cpu].rafaga_cpu == 0:
            self.proceso_actual[cpu].tiempo_finalizacion = reloj_actual + 1
            self.proceso_actual[cpu].tiempo_retorno = (
                self.proceso_actual[cpu].tiempo_finalizacion
                - self.proceso_actual[cpu].tiempo_llegada
            )
            self.proceso_actual[cpu].cambiar_estado("TERMINADO")
            self.terminados.append(self.proceso_actual[cpu])

            self.proceso_actual[cpu] = None
            self.nivel_actual[cpu] = None
            self.quantum_restante[cpu] = 0

    # Algoritmo para las demás colas
    def round_robin(self, cpu: int, reloj_actual: int) -> None:
        self.proceso_actual[cpu].rafaga_cpu -= 1
        self.proceso_actual[cpu].cpu_usada += 1
        self.quantum_restante[cpu] -= 1

        if self.proceso_actual[cpu] is not None:
            self.ticks_ocupados[cpu] += 1

        if self.proceso_actual[cpu].rafaga_cpu == 0:
            self.proceso_actual[cpu].tiempo_finalizacion = reloj_actual + 1
            self.proceso_actual[cpu].tiempo_retorno = (
                self.proceso_actual[cpu].tiempo_finalizacion
                - self.proceso_actual[cpu].tiempo_llegada
            )
            self.proceso_actual[cpu].cambiar_estado("TERMINADO")
            self.terminados.append(self.proceso_actual[cpu])

            self.proceso_actual[cpu] = None
            self.nivel_actual[cpu] = None
            self.quantum_restante[cpu] = 0
        elif (
            self.quantum_restante[cpu] == 0 and self.proceso_actual[cpu].rafaga_cpu > 0
        ):
            nivel_siguiente = self.nivel_actual[cpu] + 1
            self.proceso_actual[cpu].cambiar_estado("LISTO")
            self.colas[nivel_siguiente].append(self.proceso_actual[cpu])

            self.proceso_actual[cpu] = None
            self.nivel_actual[cpu] = None
            self.quantum_restante[cpu] = 0

    # Mostrar resultados parciales para prueba
    def mostrar_resultado(self, reloj_actual: int) -> None:
        print(f"\nRELOJ ACTUAL: {reloj_actual}")

        for cpu, proceso in enumerate(self.proceso_actual):
            if proceso is None:
                print(f"CPU {cpu}: libre")
            else:
                print(
                    f"CPU {cpu}: {proceso.nombre}, "
                    f"rafaga restante: {proceso.rafaga_cpu}, "
                    f"nivel: {self.nivel_actual[cpu]}"
                )

        for nivel, cola in enumerate(self.colas):
            procesos = ", ".join(f"{p.nombre} (rafaga: {p.rafaga_cpu})" for p in cola)
            print(f"Nivel {nivel}: [{procesos}]")

    def ejecutar_tick(self, procesos: list[Proceso], reloj_actual: int) -> None:
        # Admitir procesos
        for proceso in procesos:
            if (
                proceso.estado == "NUEVO"
                and proceso.tiempo_llegada <= reloj_actual
            ):
                proceso.cambiar_estado("LISTO")
                self.nuevo(proceso)

        # Los procesos listos esperan un tick.
        for cola in self.colas:
            for proceso in cola:
                proceso.tiempo_espera += 1

        # Cada CPU selecciona y ejecuta como máximo un proceso.
        for cpu in range(self.num_cpus):
            self.elegir_proceso(cpu)

            nivel = self.nivel_actual[cpu]
            if self.proceso_actual[cpu] is None or nivel is None:
                continue

            self.proceso_actual[cpu].cambiar_estado("EJECUTANDO")

            if nivel == self.num_colas - 1:
                self.first_come_first_served(cpu, reloj_actual)
            else:
                self.round_robin(cpu, reloj_actual)
