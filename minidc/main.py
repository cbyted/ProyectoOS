#!/usr/bin/env python
from entidades.proceso import Proceso
from politicas.mlfq import MLFQ

reloj = 0


def main():
    global reloj

    procesos = [
        Proceso(1, "Editor", "edicion", "ana", "NUEVO", 3, 1, 20),
        Proceso(2, "Navegador", "web", "luis", "NUEVO", 1, 1, 25),
        Proceso(3, "Compilador", "desarrollo", "ana", "NUEVO", 2, 2, 39),
        Proceso(4, "Reproductor", "multimedia", "marta", "NUEVO", 4, 3, 40),
        Proceso(5, "Terminal", "sistema", "luis", "NUEVO", 2, 4, 60),
    ]

    planificador = MLFQ([17, 25], procesos, 2)

    # Ejecutar varios ticks para prueba
    for i in range(100):
        reloj += 1
        print(f"RELOJ ACTUAL: {reloj}")
        planificador.mostrar_resultado_tick()
        planificador.ejecutar_tick(reloj)


if __name__ == "__main__":
    main()
