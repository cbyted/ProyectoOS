from .archivos import *
from .disco import *
from .memoria import *
from .procesos import *
from .sincronizacion import *
from .consola import *

"""
"""


class Kernel:
    def __init__(self, config):
        self.reloj = 0

        # Resumen sistema
        self.procesos_activos = []
        self.marcos_libres = []
        self.bloques_libres = []

        # Config
        self.num_cpus = 0
        self.marcos_fisicos = []
        self.tam_pagina = 0
        self.bloques_disco = 0
        self.tam_bloque = 0
        self.cache_bloques = 0

    # Reinicia TODO el sistema
    def inicia_sistema(self, config: dict) -> None:
        pass

    # Resumen final
    def apagar_sistema(self) -> dict:
        pass

    def tick(self) -> None:
        self.reloj += 1

    def ejecutar_ticks(self, n: int) -> None:
        for _ in range(n):
            self.tick()

    def reloj_actual(self) -> int:
        return self.reloj

    def cargar_escenario(self, ruta_json: str) -> None:
        pass

    def resumen_sistema(self) -> dict:
        pass
