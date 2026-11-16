import shlex

from . import kernel, procesos
from .errores import ErrorSistema

"""
Comandos obligatorios:

archivos:
pwd, cd, ls, ls -l, mkdir, touch, cat, echo "texto" > archivo, echo "texto" >> archivo,
rm, rm -r, chmod, ln -s, tree

Procesos:
ps, kill PID, run NOMBRE (crea un proceso desde el catálogo del escenario),
top (instantánea), tick N

Recursos:
free (memoria), df (disco), whoami
"""

class EstadoSesion:
    """Almacena el estado independiente de cada usuario."""

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
        self._comandos: dict[str, str] = {
            "ps": "_cmd_ps",
            "run": "_cmd_run",
            "kill": "_cmd_kill",
            "tick": "_cmd_tick",
            "top": "_cmd_top",
        }

        self._programa_prueba: list[tuple] = [
            ("CPU", 3)
        ]

    def _obtener_sesion(self, usuario: str) -> EstadoSesion:
        """Recupera la sesion de un usuario."""

        # Crear la sesion cuando todavia no existe
        if usuario not in self._sesiones:
            self._sesiones[usuario] = EstadoSesion()

        return self._sesiones[usuario]

    def ejecutar(self, linea: str, usuario: str = "admin") -> str:
        """Interpreta y ejecuta una instruccion de la consola."""

        # Eliminacion de espacios.
        linea = linea.strip()
        if not linea:
            return ""

        # Recuperar la sesion para guardar el comando ejecutado
        sesion = self._obtener_sesion(usuario)
        sesion.historial.append(linea)

        try:
            # Separar argumentos respetando las comillas.
            partes = shlex.split(linea)
            if not partes:
                return ""

            nombre_comando = partes[0]
            argumentos = partes[1:]

            # Comprobar que el comando esté implementado.
            if nombre_comando not in self._comandos:
                return f"Error: comando desconocido '{nombre_comando}'"

            # Invocacion mediante el nombre del metodo
            nombre_metodo = self._comandos[nombre_comando]
            ejecutor = getattr(self, nombre_metodo)

            return ejecutor(argumentos, usuario)

        except ErrorSistema as error:
            # Excepciones propias de los subsistemas.
            return f"Error: {error}"

        except ValueError as error:
            # Errores de sintaxis y conversiones numericas.
            return f"Error: {error}"


    def _cmd_ps(self, args: list[str], usuario: str) -> str:
        """Estructura base para listar procesos."""
        if args:
            raise ValueError("Uso: ps")

        pass

        return "PID NOMBRE USUARIO ESTADO\n(Sin procesos activos)"

    def _cmd_run(self, args: list[str], usuario: str) -> str:
        """Estructura base para crear/ejecutar un proceso."""
        if len(args) != 1:
            raise ValueError("Uso: run NOMBRE")

        nombre = args[0]

        pass

        return f"[Stub] Proceso '{nombre}' iniciado simulado"

    def _cmd_kill(self, args: list[str], usuario: str) -> str:
        """Estructura base para terminar un proceso."""
        if len(args) != 1:
            raise ValueError("Uso: kill PID")

        pid = int(args[0])
        if pid <= 0:
            raise ValueError("El PID debe ser positivo")

        pass

        return f"[Stub] Proceso {pid} terminado"

    def _cmd_tick(self, args: list[str], usuario: str) -> str:
        """Estructura base para avanzar el reloj del kernel."""
        if len(args) != 1:
            raise ValueError("Uso: tick N")

        cantidad = int(args[0])
        if cantidad < 1:
            raise ValueError("La cantidad de ticks debe ser positiva")

        pass

        return f"[Stub] Reloj avanzado {cantidad} ticks"

    def _cmd_top(self, args: list[str], usuario: str) -> str:
        """Estructura base para la instantanea del sistema."""
        if args:
            raise ValueError("Uso: top")

        pass

        return "Reloj: 0\nProcesos activos: 0\nMarcos libres: 0\nBloques libres: 0\nCPU: 0.0%"

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