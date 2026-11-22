import posixpath
import shlex

from . import archivos, kernel, memoria, procesos
from .errores import ErrorNoExiste, ErrorSistema


class EstadoSesion:
    """Almacena el directorio actual y el historial de cada usuario."""

    def __init__(self) -> None:

        # Directorio inicial del usuario.
        self.cwd: str = "/"

        # Historial de comandos ejecutados.
        self.historial: list[str] = []


class Consola:
    """Intérprete de comandos que delega las operaciones a cada subsistema."""

    def __init__(self) -> None:
        self._sesiones: dict[str, EstadoSesion] = {}

        # Mapeo de comandos por nombre
        self._comandos = {
            # Procesos y kernel
            "ps": self._cmd_ps,
            "run": self._cmd_run,
            "kill": self._cmd_kill,
            "tick": self._cmd_tick,
            "top": self._cmd_top,
            # Archivos
            "pwd": self._cmd_pwd,
            "cd": self._cmd_cd,
            "ls": self._cmd_ls,
            "mkdir": self._cmd_mkdir,
            "touch": self._cmd_touch,
            "cat": self._cmd_cat,
            "echo": self._cmd_echo,
            "rm": self._cmd_rm,
            "chmod": self._cmd_chmod,
            "ln": self._cmd_ln,
            "tree": self._cmd_tree,
            # Recursos.
            "free": self._cmd_free,
            "df": self._cmd_df,
            "whoami": self._cmd_whoami,
        }

    def _obtener_sesion(self, usuario: str) -> EstadoSesion:
        """Devuelve la sesión del usuario y la crea si todavía no existe."""

        if usuario not in self._sesiones:
            self._sesiones[usuario] = EstadoSesion()

        return self._sesiones[usuario]

    @staticmethod
    def _tokenizar(linea: str) -> list[str]:
        """Tokeniza comillas y operadores de redirección sin perder espacios."""

        lexer = shlex.shlex(linea, posix=True, punctuation_chars="<>")
        lexer.whitespace_split = True
        lexer.commenters = ""

        return list(lexer)

    @staticmethod
    def _ruta_absoluta(ruta: str, cwd: str) -> str:

        if not isinstance(ruta, str) or not ruta:
            raise ValueError("La ruta no puede estar vacía.")

        return posixpath.normpath(ruta if ruta.startswith("/") else posixpath.join(cwd, ruta))

    def ejecutar(self, linea: str, usuario: str = "admin") -> str:
        """Ejecuta un comando y convierte errores del sistema en texto."""

        if not isinstance(linea, str):
            return "Error: el comando debe ser una cadena de texto."

        if not isinstance(usuario, str) or not usuario.strip():
            return "Error: el usuario debe ser una cadena no vacía."

        linea = linea.strip()
        if not linea:
            return ""

        sesion = self._obtener_sesion(usuario)
        sesion.historial.append(linea)

        try:
            partes = self._tokenizar(linea)

            if not partes:
                return ""

            nombre_comando, *argumentos = partes
            ejecutor = self._comandos.get(nombre_comando)

            if ejecutor is None:
                return f"Error: comando desconocido '{nombre_comando}'."
            return ejecutor(argumentos, usuario)

        except ErrorSistema as error:
            # Excepciones propias de los subsistemas.
            return f"Error: {error}"

        except (ValueError, TypeError, IndexError) as error:
            # Errores de sintaxis y conversiones numericas.
            return f"Error: {error}"

    # ------------------------------------------------------------------
    # Comandos del kernel y procesos
    # ------------------------------------------------------------------

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
            raise ValueError(f"El programa '{nombre}' no contiene instrucciones válidas.")

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
        return (
            f"Reloj: {resumen['reloj']}\n"
            f"Procesos activos: {resumen['procesos_activos']}\n"
            f"Marcos libres: {resumen['marcos_libres']}\n"
            f"Bloques libres: {resumen['bloques_libres']}\n\n"
            f"{self._cmd_ps([], usuario)}"
        )

    # ------------------------------------------------------------------
    # Comandos del sistema de archivos
    # ------------------------------------------------------------------

    def _cmd_pwd(self, args: list[str], usuario: str) -> str:
        if args:
            raise ValueError("Uso: pwd")
        return self._obtener_sesion(usuario).cwd

    def _cmd_cd(self, args: list[str], usuario: str) -> str:
        if len(args) > 1:
            raise ValueError("Uso: cd [DIRECTORIO]")
        sesion = self._obtener_sesion(usuario)
        ruta = "/" if not args else self._ruta_absoluta(args[0], sesion.cwd)
        sesion.cwd = archivos.fs_acceder_directorio(ruta, usuario)
        return ""

    def _cmd_ls(self, args: list[str], usuario: str) -> str:
        sesion = self._obtener_sesion(usuario)
        detallado = False
        if args and args[0] == "-l":
            detallado = True
            args = args[1:]
        if len(args) > 1 or (args and args[0].startswith("-")):
            raise ValueError("Uso: ls [-l] [RUTA]")

        ruta = self._ruta_absoluta(args[0], sesion.cwd) if args else sesion.cwd
        nombres = archivos.fs_listar(ruta, usuario)
        if not detallado:
            return "\n".join(nombres) if nombres else "(directorio vacío)"

        lineas = ["MODO PROPIETARIO GRUPO TAMAÑO NOMBRE"]
        try:
            archivos.fs_acceder_directorio(ruta, usuario)
            es_directorio = True
        except ErrorSistema as error:
            if str(error) != "la ruta indicada no es un directorio.":
                raise
            es_directorio = False

        for nombre in nombres:
            ruta_elemento = posixpath.join(ruta, nombre) if es_directorio else ruta
            info = archivos.fs_info(ruta_elemento)
            lineas.append(
                f"{info['modo']} {info['propietario']} {info['grupo']} "
                f"{info['tamano']} {nombre}"
            )
        return "\n".join(lineas)

    def _cmd_mkdir(self, args: list[str], usuario: str) -> str:
        if len(args) != 1:
            raise ValueError("Uso: mkdir DIRECTORIO")
        sesion = self._obtener_sesion(usuario)
        ruta = self._ruta_absoluta(args[0], sesion.cwd)
        archivos.fs_mkdir(ruta, usuario)
        return f"Directorio creado: {ruta}"

    def _cmd_touch(self, args: list[str], usuario: str) -> str:
        if len(args) != 1:
            raise ValueError("Uso: touch ARCHIVO")
        sesion = self._obtener_sesion(usuario)
        ruta = self._ruta_absoluta(args[0], sesion.cwd)
        archivos.fs_crear_archivo(ruta, usuario)
        return f"Archivo preparado: {ruta}"

    def _cmd_cat(self, args: list[str], usuario: str) -> str:
        if len(args) != 1:
            raise ValueError("Uso: cat ARCHIVO")
        sesion = self._obtener_sesion(usuario)
        ruta = self._ruta_absoluta(args[0], sesion.cwd)
        return archivos.fs_leer(ruta, usuario)

    def _cmd_echo(self, args: list[str], usuario: str) -> str:
        if not args:
            raise ValueError('Uso: echo "TEXTO" [> ARCHIVO | >> ARCHIVO]')

        operadores_validos = (">", ">>")
        if any(
            ">" in parte and parte not in operadores_validos
            for parte in args
        ):
            raise ValueError("Redirección inválida; use > o >>.")
        posiciones = [indice for indice, parte in enumerate(args) if parte in operadores_validos]
        if not posiciones:
            return " ".join(args)
        if len(posiciones) != 1:
            raise ValueError("echo admite una sola redirección.")

        indice = posiciones[0]
        operador = args[indice]
        texto = " ".join(args[:indice])
        destino = args[indice + 1 :]
        if len(destino) != 1 or indice == 0:
            raise ValueError('Uso: echo "TEXTO" [> ARCHIVO | >> ARCHIVO]')

        sesion = self._obtener_sesion(usuario)
        ruta = self._ruta_absoluta(destino[0], sesion.cwd)
        bytes_escritos = archivos.fs_escribir(
            ruta, texto, usuario, agregar=(operador == ">>")
        )
        accion = "añadidos" if operador == ">>" else "escritos"
        return f"{bytes_escritos} bytes {accion} en {ruta}."

    def _cmd_rm(self, args: list[str], usuario: str) -> str:
        recursivo = False
        if args and args[0] == "-r":
            recursivo = True
            args = args[1:]
        if len(args) != 1 or (args and args[0].startswith("-")):
            raise ValueError("Uso: rm [-r] RUTA")
        sesion = self._obtener_sesion(usuario)
        ruta = self._ruta_absoluta(args[0], sesion.cwd)
        archivos.fs_eliminar(ruta, usuario, recursivo)
        return f"Eliminado: {ruta}"

    def _cmd_chmod(self, args: list[str], usuario: str) -> str:
        if len(args) != 2:
            raise ValueError("Uso: chmod MODO_OCTAL RUTA")
        modo, ruta_argumento = args
        sesion = self._obtener_sesion(usuario)
        ruta = self._ruta_absoluta(ruta_argumento, sesion.cwd)
        archivos.fs_chmod(ruta, modo, usuario)
        return f"Permisos de {ruta} establecidos en {modo}."

    def _cmd_ln(self, args: list[str], usuario: str) -> str:
        if len(args) != 3 or args[0] != "-s":
            raise ValueError("Uso: ln -s DESTINO ENLACE")
        sesion = self._obtener_sesion(usuario)
        ruta_enlace = self._ruta_absoluta(args[2], sesion.cwd)
        archivos.fs_enlace_simbolico(args[1], ruta_enlace, usuario)
        return f"Enlace simbólico creado: {ruta_enlace} -> {args[1]}"

    def _cmd_tree(self, args: list[str], usuario: str) -> str:
        if len(args) > 1:
            raise ValueError("Uso: tree [RUTA]")
        sesion = self._obtener_sesion(usuario)
        ruta = self._ruta_absoluta(args[0], sesion.cwd) if args else sesion.cwd
        archivos.fs_acceder_directorio(ruta, usuario)
        raiz_mostrada = ruta.rstrip("/").split("/")[-1] or "/"
        lineas = [raiz_mostrada]

        def recorrer(ruta_actual: str, prefijo: str) -> None:
            nombres = archivos.fs_listar(ruta_actual, usuario)
            for indice, nombre in enumerate(nombres):
                ultimo = indice == len(nombres) - 1
                conector = "└── " if ultimo else "├── "
                lineas.append(prefijo + conector + nombre)
                ruta_hijo = posixpath.join(ruta_actual, nombre)
                if archivos.fs_info(ruta_hijo)["tipo"] == "directorio":
                    extension = "    " if ultimo else "│   "
                    recorrer(ruta_hijo, prefijo + extension)

        recorrer(ruta, "")
        return "\n".join(lineas)

    # ------------------------------------------------------------------
    # Comandos de consultas de recursos
    # ------------------------------------------------------------------

    def _cmd_free(self, args: list[str], usuario: str) -> str:
        if args:
            raise ValueError("Uso: free")
        estado = memoria.estado_memoria()
        usados = estado["marcos_totales"] - estado["marcos_libres"]
        return (
            "Memoria física\n"
            f"Marcos totales: {estado['marcos_totales']}\n"
            f"Marcos usados: {usados}\n"
            f"Marcos libres: {estado['marcos_libres']}"
        )

    def _cmd_df(self, args: list[str], usuario: str) -> str:
        if args:
            raise ValueError("Uso: df")
        estado = archivos.fs_estado_disco()
        bloques_usados = estado["bloques_totales"] - estado["bloques_libres"]
        return (
            "Sistema de archivos\n"
            f"Bloques totales: {estado['bloques_totales']}\n"
            f"Bloques usados: {bloques_usados}\n"
            f"Bloques libres: {estado['bloques_libres']}\n"
            f"Huecos libres: {estado['huecos_libres']}"
        )

    def _cmd_whoami(self, args: list[str], usuario: str) -> str:
        if args:
            raise ValueError("Uso: whoami")
        return usuario

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