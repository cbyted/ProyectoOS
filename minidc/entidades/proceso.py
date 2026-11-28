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
        programa: list | None = None,
    ):
        self.pid = pid
        self.nombre = nombre
        self.usuario = usuario
        self.servicio = None
        self.estado = estado
        self.tiempo_llegada = tiempo_llegada
        self.rafaga_cpu = rafaga_cpu
        self.memoria_bytes = memoria_bytes
        self.cuota_marcos = cuota_marcos
        self.prioridad = prioridad
        self.hilos = []

        # Copia las instrucciones para que cada proceso tenga su propio estado.
        self.programa = list(programa or [])
        self.indice_instruccion = 0
        self.tiempo_restante_instruccion = self.programa[0][1] if self.programa else 0

        # Métricas
        self.tiempo_inanicion = 0
        self.espera_consecutiva = 0
        self.tiempo_espera = 0
        self.tiempo_retorno = 0
        self.tiempo_finalizacion = 0
        self.cpu_usada = 0
        self.tiempo_primera_ejecucion = None

    def cambiar_estado(self, nuevo_estado):
        self.estado = nuevo_estado


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
        programa: list | None = None,
    ):
        self.pid = pid
        self.nombre = nombre
        self.usuario = usuario
        self.servicio = None
        self.estado = estado
        self.tiempo_llegada = tiempo_llegada
        self.rafaga_cpu = rafaga_cpu  # CPU total que falta (informativo)
        self.memoria_bytes = memoria_bytes
        self.cuota_marcos = cuota_marcos
        self.prioridad = prioridad
        self.hilos = []

        # Ejecución del programa
        self.programa = [tuple(i) for i in (programa or [])]
        self.indice_instruccion = 0
        self.restante_instr = None  # ticks que faltan de la instrucción CPU actual

        # Planificación
        self.nivel = 0  # cola MLFQ en la que está (o estuvo)
        self.motivo_bloqueo = None  # "DISCO", "FALLO_PAGINA", "SEMAFORO"
        self.bloqueado_hasta = None  # tick de despertar (solo fallo de página)

        # Métricas
        self.espera_consecutiva = 0  # ticks seguidos en cola de listos
        self.tiempo_espera = 0  # total de ticks en cola de listos
        self.tiempo_retorno = 0
        self.tiempo_finalizacion = 0
        self.cpu_usada = 0
        self.tiempo_primera_ejecucion = None

    def cambiar_estado(self, nuevo_estado):
        self.estado = nuevo_estado
