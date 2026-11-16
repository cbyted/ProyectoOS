#!/usr/bin/env python
from entidades.proceso import Proceso
from politicas.mlfq import MLFQ
from procesos import APIProcesos

reloj = 0


def main():
    global reloj

    # Inicializa el planificador
    planificador = MLFQ([17, 25], 2)
    api_procesos = APIProcesos(planificador)

    api_procesos = APIProcesos(planificador)

    procesos_a_crear = [
        ("Editor", "ana", 20, 1, 0),
        ("Navegador", "luis", 25, 1, 1),
        ("Compilador", "ana", 39, 2, 0),
        ("Reproductor", "marta", 40, 3, 2),
        ("Terminal", "luis", 60, 4, 0),
        ("Respaldos", "luis", 30, 1, 0),
    ]

    for nombre, usuario, rafaga_cpu, llegada, prioridad in procesos_a_crear:
        api_procesos.crear_proceso(
            nombre=nombre,
            usuario=usuario,
            programa=[("CPU", rafaga_cpu)],
            prioridad=prioridad,
            reloj_actual=llegada,
        )

    # Ejecutar varios ticks para prueba
    for i in range(100):
        reloj += 1
        planificador.ejecutar_tick(api_procesos.procesos, reloj)


if __name__ == "__main__":
    main()
