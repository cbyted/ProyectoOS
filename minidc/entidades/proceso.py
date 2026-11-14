class Proceso:
    def __init__(
        self,
        pid: int,
        nombre: str,
        servicio: str,
        usuario: str,
        estado: str,
        prioridad: int,
        tiempo_llegada: int,
        tiempo_esperado: int,
        rafaga_cpu: int,
    ):
        self.pid = pid
        self.nombre = nombre
        self.servicio = servicio
        self.usuario = usuario
        self.estado = estado
        self.prioridad = prioridad
        self.tiempo_llegada = tiempo_llegada
        self.rafaga_cpu = rafaga_cpu
        self.abortar = 0
        self.hilos = []

        # Metricas únicas de cada proceso
        self.tiempo_restante = self.rafaga_cpu
        self.espera_promedio = 0
        self.espera_maxima = 0
        self.retorno_promedio = 0
        self.tiempo_completado = 0

    def cambiar_estado(self, nuevo_estado):
        pass

    def terminar(self):
        self.abortar = 1
