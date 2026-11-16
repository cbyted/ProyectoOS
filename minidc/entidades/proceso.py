class Proceso:
    def __init__(
        self,
        pid: int,
        nombre: str,
        usuario: str,
        estado: str,
        tiempo_llegada: int,
        rafaga_cpu: int,
        memoria_bytes: int,
        cuota_marcos: int,
        prioridad: int,
    ):
        self.pid = pid
        self.nombre = nombre
        self.usuario = usuario
        self.estado = estado
        self.tiempo_llegada = tiempo_llegada
        self.rafaga_cpu = rafaga_cpu
        self.memoria_bytes = memoria_bytes
        self.cuota_marcos = cuota_marcos
        self.prioridad = prioridad
        self.hilos = []

        # Metricas únicas de cada proceso
        self.tiempo_espera = 0
        self.tiempo_retorno = 0
        self.tiempo_finalizacion = 0
        self.cpu_usada = 0

    def cambiar_estado(self, nuevo_estado):
        self.estado = nuevo_estado
