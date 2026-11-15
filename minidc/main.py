#!/usr/bin/env python
from entidades.proceso import Proceso
from politicas.mlfq import MLFQ

reloj = 0


def main():
    global reloj

    procesos = [
        Proceso(1, "Editor", "edicion", "ana", "NUEVO", 1, 20),
        Proceso(2, "Navegador", "web", "luis", "NUEVO", 1, 25),
        Proceso(3, "Compilador", "desarrollo", "ana", "NUEVO", 2, 39),
        Proceso(4, "Reproductor", "multimedia", "marta", "NUEVO", 3, 40),
        Proceso(5, "Terminal", "sistema", "luis", "NUEVO", 4, 60),
        Proceso(6, "Respaldos", "sistema", "luis", "NUEVO", 1, 30),
    ]

    # Inicializa el planificador
    planificador = MLFQ([17, 25], 2)

    # Ejecutar varios ticks para prueba
    for i in range(100):
        reloj += 1
        planificador.ejecutar_tick(procesos, reloj)


if __name__ == "__main__":
    main()
