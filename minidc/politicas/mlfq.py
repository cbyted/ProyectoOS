from .proceso import Proceso
from collections import deque

"""
Implementar Miultilevel Feedback Queue
El algoritmo está limitado a tres 3 colas.
El número de quantums correstone al numero de colas - 1
"""


class MLFQ:
    def __init__(
        self,
        reloj: int,
        quantums: list[int],
        procesos: list[Proceso],
    ) -> None:
        # El número de colas que usa esta Implementación
        self.num_colas = 3

        # Reloj actual
        self.reloj = reloj

        # Los quantums para cada cola
        self.quantums = quantums

        # Lista de procesos
        self.procesos = procesos

        # Cola de procesos listos
        self.listos = deque[self.procesos]

        # Cola de procesos terminados
        self.terminados: deque[Proceso] = deque()

    # Devuelve el reloj actual para que el kernel
    # pueda actualizar el reloj global
    def reloj_actual(self) -> int:
        return self.reloj

    def calcular_tiempo_espera(self, cola: list[Proceso]) -> list[int]:
        tiempos = []
        return tiempos

    def calcular_tiempo_retorno(self):
        pass

    def calcular_tiempo_finalizacion(self):
        pass

    def calcular_tiempo_restante(self):
        pass

    def first_come_first_served(self):
        pass

    def round_robin(self):
        pass

    def multilevel_feedback_queue(self):
        pass
