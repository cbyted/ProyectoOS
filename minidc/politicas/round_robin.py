from .procesos import Process


class RoundRobin:
    def __init__(self, reloj: int, quantum: int, procesos: Process):
        self.quantum = quantum
        self.procesos = procesos
        self.actual = self.procesos[0]
        self.listos = []
        self.terminados = []
        self.cambios_contexto = 0

    def siguiente_proceso(self):
        return self.listos[0]

    def mover_a_listos(self, proceso):
        self.listos.append(proceso)

    def mover_a_terminados(self, proceso):
        self.terminados.append(proceso)

    def ejecutar(self):
        pass

    # Esta función es solo para validar los resultados.
    # No va en el prototipo final
    def mostrar_resultados(self):
        pass
