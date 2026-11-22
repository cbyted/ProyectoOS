import shlex

from . import kernel, procesos
from .errores import ErrorNoExiste, ErrorSistema


class EstadoSesion:
    """Almacena el estado de consola independiente de cada usuario."""

    def __init__(self) -> None:

        # Directorio inicial del usuario.
        self.cwd: str = "/"

        # Historial de comandos ejecutados.
        self.historial: list[str] = []


class Consola:
    """Clase interprete de comandos para el sistema."""

    def __init__(self) -> None:
        self._sesiones: dict[str, EstadoSesion] = {}

        # Mapeo de comandos por nombre
        self._comandos: dict = {
            "ps": self._cmd_ps,
            "run": self._cmd_run,
            "kill": self._cmd_kill,
            "tick": self._cmd_tick,
            "top": self._cmd_top,
        }

    def _obtener_sesion(self, usuario: str) -> EstadoSesion:
        """Devuelve la sesión del usuario y la crea si todavía no existe."""

        if usuario not in self._sesiones:
            self._sesiones[usuario] = EstadoSesion()

        return self._sesiones[usuario]

    def ejecutar(self, linea: str, usuario: str = "admin") -> str:
        """Analiza una línea, ejecuta su comando y devuelve el resultado."""

        if not isinstance(linea, str):
            return "Error: el comando debe ser una cadena de texto."

        if not isinstance(usuario, str) or not usuario.strip():
            return "Error: el usuario debe ser una cadena no vacía."

        linea = linea.strip()
        if not linea:
            return ""

        # Registro del comando antes de interpretarse.
        self._obtener_sesion(usuario).historial.append(linea)

        try:
            partes = shlex.split(linea)
            if not partes:
                return ""

            nombre_comando = partes[0]
            argumentos = partes[1:]

            ejecutor = self._comandos.get(nombre_comando)
            if ejecutor is None:
                return f"Error: comando desconocido '{nombre_comando}'."

            return ejecutor(argumentos, usuario)

        except ErrorSistema as error:
            # Excepciones propias de los subsistemas.
            return f"Error: {error}"

        except (ValueError, TypeError) as error:
            # Errores de sintaxis y conversiones numericas.
            return f"Error: {error}"

    def _cmd_ps(self, args: list[str], usuario: str) -> str:
        """Lista los procesos registrados en el subsistema de procesos."""

        if args:
            raise ValueError("Uso: ps")

        lista_procesos = procesos.listar_procesos()
        lineas = ["PID NOMBRE USUARIO ESTADO"]

        for proceso in lista_procesos:
            lineas.append(
                f"{proceso['pid']} {proceso['nombre']} "
                f"{proceso['usuario']} {proceso['estado']}"
            )

        if not lista_procesos:
            lineas.append("(Sin procesos registrados)")

        return "\n".join(lineas)

    def _cmd_run(self, args: list[str], usuario: str) -> str:
        """Crea un proceso a partir de una definición del escenario cargado."""

        if len(args) != 1:
            raise ValueError("Uso: run NOMBRE (ejemplo: run web)")

        nombre = args[0]

        # Se accede mediante el atributo del kernel.
        instancia_kernel = getattr(kernel, "_kernel", None)
        catalogo = getattr(instancia_kernel, "catalogo", None)

        if not isinstance(catalogo, dict) or nombre not in catalogo:
            raise ErrorNoExiste(f"el programa '{nombre}' no existe en el catálogo.")

        definicion = catalogo[nombre]
        if not isinstance(definicion, dict):
            raise ValueError(f"La definición del programa '{nombre}' es inválida.")

        programa = definicion.get("programa")
        if not isinstance(programa, list) or not programa:
            raise ValueError(
                f"El programa '{nombre}' no contiene instrucciones válidas."
            )

        # Los parámetros opcionales conservan los valores por defecto.
        pid = procesos.crear_proceso(
            nombre=nombre,
            usuario=usuario,
            programa=programa,
            memoria_bytes=definicion.get("memoria_bytes", 4096),
            cuota_marcos=definicion.get("cuota_marcos", 4),
            prioridad=definicion.get("prioridad", 0),
        )

        return f"Proceso '{nombre}' iniciado con PID {pid}."

    def _cmd_kill(self, args: list[str], usuario: str) -> str:
        """Termina el proceso identificado por su PID."""

        if len(args) != 1:
            raise ValueError("Uso: kill PID")

        try:
            pid = int(args[0])
        except ValueError:
            raise ValueError("El PID debe ser un número entero.") from None

        # Validación del valor del PID
        if pid < 0:
            raise ValueError("El PID no puede ser negativo.")

        # Comprobación del estado del proceso
        estado = procesos.estado_proceso(pid)

        if estado is None:
            raise ErrorNoExiste(f"el proceso con PID {pid} no existe.")

        procesos.terminar_proceso(pid)
        return f"Proceso {pid} terminado."

    def _cmd_tick(self, args: list[str], usuario: str) -> str:
        """Avanza el reloj simulado la cantidad de ticks indicada."""

        if len(args) != 1:
            raise ValueError("Uso: tick N")

        try:
            cantidad = int(args[0])
        except ValueError:
            raise ValueError("La cantidad de ticks debe ser un entero.") from None

        if cantidad < 1:
            raise ValueError("La cantidad de ticks debe ser positiva.")

        # Pasa al kernel que controla el reloj y la ejecución del planificador.
        kernel.ejecutar_ticks(cantidad)
        return f"Reloj actual: {kernel.reloj_actual()}"

    def _cmd_top(self, args: list[str], usuario: str) -> str:
        """Muestra una instantánea del kernel y los procesos registrados."""

        if args:
            raise ValueError("Uso: top")

        resumen = kernel.resumen_sistema()

        # Muestra de datos públicos disponibles sin modificar ese subsistema.
        salida = (
            f"Reloj: {resumen['reloj']}\n"
            f"Procesos activos: {resumen['procesos_activos']}\n"
            f"Marcos libres: {resumen['marcos_libres']}\n"
            f"Bloques libres: {resumen['bloques_libres']}\n\n"
            f"{self._cmd_ps([], usuario)}"
        )

        return salida


# Instancia y funciones auxiliares publicas.
_consola = Consola()


def _reiniciar_estado() -> None:
    _consola._sesiones.clear()


def ejecutar_comando(linea: str, usuario: str = "admin") -> str:
    """Ejecuta comandos del sistema."""

    return _consola.ejecutar(linea, usuario)


def directorio_actual(usuario: str = "admin") -> str:
    """Devuelve el directorio de trabajo del usuario."""

    return _consola._obtener_sesion(usuario).cwd


def historial(usuario: str = "admin") -> list[str]:
    """Devuelve una copia del historial de comandos de un usuario."""

    return list(_consola._obtener_sesion(usuario).historial)

