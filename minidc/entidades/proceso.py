class Proceso:
    def __init__(
        self,
        pid,
        nombre,
        servicio,
        usuario,
    ):
        self.pid = pid
        self.nombre = nombre
        self.servicio = servicio
        self.usuario = usuario
        self.estado = "NUEVO"
        self.abortar = 0
        self.hilos = []

    def cambiar_estado(self, nuevo_estado):
        pass

    def asignar_cpu(self, cpu_time):
        self.cpu_time = cpu_time

    def despojar_cpu(self):
        self.cpu_time = 0

    def abortar(self):
        self.abortar = 1
