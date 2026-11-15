class Proceso:
    def __init__(
        self,
        pid: int,
        nombre: str,
        servicio: str,
        usuario: str,
        estado: str,
        tiempo_llegada: int,
        rafaga_cpu: int,
    ):
        self.pid = pid
        self.nombre = nombre
        self.servicio = servicio
        self.usuario = usuario
        self.estado = estado
        self.tiempo_llegada = tiempo_llegada
        self.rafaga_cpu = rafaga_cpu
        self.abortar = 0
        self.hilos = []

        # Metricas únicas de cada proceso
        self.tiempo_espera = 0
        self.tiempo_retorno = 0
        self.tiempo_finalizacion = 0

    def cambiar_estado(self, nuevo_estado):
        self.estado = nuevo_estado

    def terminar(self):
        self.abortar = 1
