#!/usr/bin/env python
from entidades.proceso import Proceso
from politicas.mlfq import MLFQ

reloj = 0


def main():
    global reloj

    procesos = [
        Proceso(1, "Editor", "edicion", "ana", "listo", 3, 0, 8),
        Proceso(2, "Navegador", "web", "luis", "listo", 1, 1, 5),
        Proceso(3, "Compilador", "desarrollo", "ana", "listo", 2, 2, 10),
        Proceso(4, "Reproductor", "multimedia", "marta", "listo", 4, 3, 4),
        Proceso(5, "Terminal", "sistema", "luis", "listo", 2, 4, 6),
    ]

    planificador = MLFQ([17, 25], procesos, 2)

    # Ejecutar varios ticks para prueba
    for i in range(100):
        reloj += 1
        planificador.ejecutar_tick(reloj)
        planificador.mostrar_resultado_tick()
        print("\n")


if __name__ == "__main__":
    main()
