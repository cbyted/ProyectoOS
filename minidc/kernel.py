import json
from pathlib import Path

from . import archivos, consola, disco, memoria, procesos


_CLAVES_CONFIG = (
    "num_cpus",
    "marcos_fisicos",
    "tam_pagina",
    "bloques_disco",
    "tam_bloque",
    "cache_bloques",
)


def _validar_config(config: dict) -> dict:
    if not isinstance(config, dict):
        raise ValueError("La configuración debe ser un diccionario.")

    faltantes = [clave for clave in _CLAVES_CONFIG if clave not in config]
    if faltantes:
        raise ValueError(f"Faltan claves de configuración: {', '.join(faltantes)}.")

    valores = dict(config)
    for clave in _CLAVES_CONFIG:
        minimo = 0 if clave == "cache_bloques" else 1
        valor = valores[clave]
        if isinstance(valor, bool) or not isinstance(valor, int) or valor < minimo:
            raise ValueError(f"'{clave}' debe ser un entero mayor o igual a {minimo}.")
    return valores


class Kernel:
    """Coordina el reloj, las llegadas y la planificación de NimbusDC."""

    def __init__(self) -> None:
        self.reloj = 0
        self.config = {}
        self.procesos_activos = []
        self.marcos_libres = 0
        self.bloques_libres = 0
        self.num_cpus = 0
        self.marcos_fisicos = 0
        self.tam_pagina = 0
        self.bloques_disco = 0
        self.tam_bloque = 0
        self.cache_bloques = 0
        self.api_procesos = None
        self.catalogo = {}
        self.llegadas = []
        self._siguiente_llegada = 0

    def iniciar_sistema(self, config: dict) -> None:
        nueva_config = _validar_config(config)

        self.reloj = 0
        self.config = nueva_config
        self.num_cpus = nueva_config["num_cpus"]
        self.marcos_fisicos = nueva_config["marcos_fisicos"]
        self.tam_pagina = nueva_config["tam_pagina"]
        self.bloques_disco = nueva_config["bloques_disco"]
        self.tam_bloque = nueva_config["tam_bloque"]
        self.cache_bloques = nueva_config["cache_bloques"]
        self.marcos_libres = self.marcos_fisicos
        self.bloques_libres = self.bloques_disco
        self.procesos_activos = []
        self.catalogo = {}
        self.llegadas = []
        self._siguiente_llegada = 0

        # Cada subsistema conserva su propio estado.
        memoria.inicializar_memoria(nueva_config)
        disco._configurar(
            self.bloques_disco,
            self.tam_bloque,
            self.cache_bloques,
        )
        archivos._configurar(self.bloques_disco, self.tam_bloque)
        consola._reiniciar_estado()
        self.api_procesos = procesos._configurar(self.num_cpus, lambda: self.reloj)

    def apagar_sistema(self) -> dict:
        return self.resumen_sistema()

    def _procesar_llegadas(self) -> None:
        while (
            self._siguiente_llegada < len(self.llegadas)
            and self.llegadas[self._siguiente_llegada]["tick"] <= self.reloj
        ):
            llegada = self.llegadas[self._siguiente_llegada]
            self._siguiente_llegada += 1
            definicion = self.catalogo[llegada["programa"]]
            self.api_procesos.crear_proceso(
                nombre=llegada["programa"],
                usuario=llegada["usuario"],
                programa=definicion["programa"],
                memoria_bytes=definicion.get("memoria_bytes", 4096),
                cuota_marcos=definicion.get("cuota_marcos", 4),
                prioridad=definicion.get("prioridad", 0),
            )

    def tick(self) -> None:
        if self.api_procesos is None:
            raise RuntimeError("El sistema no ha sido iniciado.")

        self.reloj += 1
        self._procesar_llegadas()
        self.api_procesos.planificador.ejecutar_tick(
            self.api_procesos.procesos, self.reloj
        )
        self.procesos_activos = [
            proceso
            for proceso in self.api_procesos.procesos
            if proceso.estado != "TERMINADO"
        ]

    def ejecutar_ticks(self, n: int) -> None:
        if isinstance(n, bool) or not isinstance(n, int) or n < 0:
            raise ValueError("La cantidad de ticks debe ser un entero no negativo.")
        for _ in range(n):
            self.tick()

    def reloj_actual(self) -> int:
        return self.reloj

    def cargar_escenario(self, ruta_json: str) -> None:
        with Path(ruta_json).open("r", encoding="utf-8") as archivo:
            escenario = json.load(archivo)

        if not isinstance(escenario, dict):
            raise ValueError("El escenario debe ser un objeto JSON.")
        config = _validar_config(escenario.get("config"))
        catalogo = escenario.get("catalogo", {})
        llegadas = escenario.get("llegadas", [])
        usuarios = escenario.get("usuarios", [])
        if not isinstance(catalogo, dict) or not isinstance(llegadas, list):
            raise ValueError("'catalogo' debe ser un objeto y 'llegadas' una lista.")
        if not isinstance(usuarios, list) or any(
            not isinstance(nombre, str) or not nombre.strip() for nombre in usuarios
        ):
            raise ValueError("'usuarios' debe ser una lista de nombres no vacíos.")
        usuarios = [nombre.strip() for nombre in usuarios]

        # JSON representa las instrucciones como listas; internamente se
        # normalizan a tuplas, tal como define el modelo del proyecto.
        catalogo_validado = {}
        for nombre, definicion in catalogo.items():
            if not isinstance(nombre, str) or not nombre:
                raise ValueError("Cada programa del catálogo debe tener un nombre.")
            if not isinstance(definicion, dict):
                raise ValueError(f"Definición inválida para el programa '{nombre}'.")
            programa = definicion.get("programa")
            if not isinstance(programa, list) or not programa:
                raise ValueError(
                    f"Definición inválida para el programa '{nombre}': falta programa."
                )
            instrucciones = []
            for instruccion in programa:
                if not isinstance(instruccion, (list, tuple)) or len(instruccion) != 2:
                    raise ValueError(
                        f"Instrucción inválida en el programa '{nombre}': {instruccion}."
                    )
                instrucciones.append(tuple(instruccion))
            definicion_validada = dict(definicion)
            definicion_validada["programa"] = instrucciones
            catalogo_validado[nombre] = definicion_validada

        llegadas_validadas = []
        usuarios_escenario = list(usuarios)
        for llegada in llegadas:
            if not isinstance(llegada, dict):
                raise ValueError("Cada llegada debe ser un objeto.")
            tick = llegada.get("tick")
            nombre_programa = llegada.get("programa")
            usuario = llegada.get("usuario", "admin")
            if isinstance(tick, bool) or not isinstance(tick, int) or tick < 0:
                raise ValueError("El tick de llegada debe ser un entero no negativo.")
            if (
                not isinstance(nombre_programa, str)
                or nombre_programa not in catalogo_validado
            ):
                raise ValueError(
                    f"Programa no definido en el catálogo: {nombre_programa}."
                )
            if not isinstance(usuario, str) or not usuario.strip():
                raise ValueError(
                    "El usuario de cada llegada debe ser un texto no vacío."
                )
            usuario = usuario.strip()
            if usuario not in usuarios_escenario and usuario != "admin":
                usuarios_escenario.append(usuario)
            llegadas_validadas.append(
                {"tick": tick, "programa": nombre_programa, "usuario": usuario}
            )

        self.iniciar_sistema(config)
        self.catalogo = catalogo_validado
        for nombre_usuario in dict.fromkeys(usuarios_escenario):
            if nombre_usuario != "admin":
                archivos.crear_usuario(nombre_usuario)
        self.llegadas = sorted(llegadas_validadas, key=lambda evento: evento["tick"])
        self._procesar_llegadas()

    def resumen_sistema(self) -> dict:
        procesos_activos = (
            sum(proceso.estado != "TERMINADO" for proceso in self.api_procesos.procesos)
            if self.api_procesos is not None
            else 0
        )
        if self.api_procesos is not None:
            self.marcos_libres = memoria.estado_memoria()["marcos_libres"]
            self.bloques_libres = archivos.fs_estado_disco()["bloques_libres"]
        return {
            "reloj": self.reloj,
            "procesos_activos": procesos_activos,
            "marcos_libres": self.marcos_libres,
            "bloques_libres": self.bloques_libres,
        }


_kernel = Kernel()


def iniciar_sistema(config: dict) -> None:
    _kernel.iniciar_sistema(config)


def apagar_sistema() -> dict:
    return _kernel.apagar_sistema()


def tick() -> None:
    _kernel.tick()


def ejecutar_ticks(n: int) -> None:
    _kernel.ejecutar_ticks(n)


def reloj_actual() -> int:
    return _kernel.reloj_actual()


def cargar_escenario(ruta_json: str) -> None:
    _kernel.cargar_escenario(ruta_json)


def resumen_sistema() -> dict:
    return _kernel.resumen_sistema()
