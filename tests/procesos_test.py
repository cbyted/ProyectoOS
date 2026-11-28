from minidc.politicas.mlfq import MLFQ
from minidc.procesos import APIProcesos


PROCESOS_DE_PRUEBA = [
    ("Editor", "ana", 20, 1, 0),
    ("Navegador", "luis", 25, 1, 1),
    ("Compilador", "ana", 39, 2, 0),
    ("Reproductor", "marta", 40, 3, 2),
    ("Terminal", "luis", 60, 4, 0),
    ("Respaldos", "luis", 30, 1, 0),
]


def test_demostracion_mlfq_finaliza_todos_los_procesos(capsys):
    """Reproduce la carga de demostración y valida el resultado del planificador."""
    planificador = MLFQ([17, 25], 2)
    api_procesos = APIProcesos(planificador)

    for nombre, usuario, rafaga_cpu, llegada, prioridad in PROCESOS_DE_PRUEBA:
        pid = api_procesos.crear_proceso(
            nombre=nombre,
            usuario=usuario,
            programa=[("CPU", rafaga_cpu)],
            prioridad=prioridad,
        )
        # La versión original de la demostración escalonaba llegadas distintas.
        api_procesos.procesos[pid].tiempo_llegada = llegada

    reloj = 0
    while reloj < 200 and any(
        proceso.estado != "TERMINADO" for proceso in api_procesos.procesos
    ):
        reloj += 1
        planificador.ejecutar_tick(api_procesos.procesos, reloj)

    # La salida de diagnóstico del algoritmo queda capturada por pytest.
    salida = capsys.readouterr().out

    assert "RELOJ ACTUAL" in salida
    assert all(proceso.estado == "TERMINADO" for proceso in api_procesos.procesos)
    assert sum(proceso.cpu_usada for proceso in api_procesos.procesos) == 214
    assert len({proceso.pid for proceso in api_procesos.procesos}) == 6
    assert reloj <= 150
