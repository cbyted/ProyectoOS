class APIProcesos:
    def __init__(self):
        pass


# Devuelve el PID
def crear_proceso(
    nombre: str,
    usuario: str,
    programa: list,
    memoria_bytes: int = 4096,
    cuota_marcos: int = 4,
    prioridad: int = 0,
):
    return 1


# Devuelve el TID
def crear_hilo(pid: int, programa: list):
    pass


def terminar_proceso(pid: int):
    pass

    # NUEVO, LISTO, EJECUTANDO, BLOQUEADO, TERMINADO


def estado_proceso(pid: int):
    pass


# dicts: pid, nombre, usuario, estado, prioridad, cpu_usada, tiempo_espera
def listar_procesos():
    return []


def cola_listos():
    pass


def proceso_en_ejecucion(cpu: int = 0):
    pass


def metricas_planificacion():
    return {"utilizacion_cpu": 0.0}


def politica_planificacion():
    pass
