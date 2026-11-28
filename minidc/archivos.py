import re

from .entidades.archivo import NodoArchivo, UsuarioSistema
from .errores import ErrorNoExiste, ErrorPermiso, ErrorSistema, ErrorYaExiste
from .politicas.asignacion_archivos import AsignacionIndexada


_MODO_POR_DEFECTO_DIRECTORIO = "755"
_MODO_POR_DEFECTO_ARCHIVO = "644"
_MAX_ENLACES = 40


class SistemaArchivos:
    """Administra el árbol, los usuarios, permisos y bloques del sistema."""

    def __init__(self) -> None:
        self.tam_bloque = 512
        self.asignador = AsignacionIndexada(200)
        self.usuarios: dict[str, UsuarioSistema] = {}
        self.raiz = NodoArchivo("/", "directorio", "admin", "admin", "755")
        self.formatear_disco()

    def configurar(self, bloques_totales: int, tam_bloque: int) -> None:
        if (
            isinstance(tam_bloque, bool)
            or not isinstance(tam_bloque, int)
            or tam_bloque < 1
        ):
            raise ValueError("El tamaño de bloque debe ser un entero positivo.")
        self.tam_bloque = tam_bloque
        self.asignador.reiniciar(bloques_totales)
        self.formatear_disco()

    def formatear_disco(self) -> None:
        """Reinicia el árbol y crea el usuario administrador y la raíz."""
        self.usuarios = {"admin": UsuarioSistema("admin", "admin")}
        self.raiz = NodoArchivo("/", "directorio", "admin", "admin", "755")
        self.asignador.reiniciar(self.asignador.bloques_totales)

    def crear_usuario(self, nombre: str, grupo: str = "usuarios") -> None:
        if not isinstance(nombre, str) or not nombre.strip():
            raise ValueError("El nombre del usuario no puede estar vacío.")
        if not isinstance(grupo, str) or not grupo.strip():
            raise ValueError("El grupo del usuario no puede estar vacío.")

        nombre = nombre.strip()
        grupo = grupo.strip()
        if nombre in self.usuarios:
            raise ErrorYaExiste(f"el usuario '{nombre}' ya existe.")
        self.usuarios[nombre] = UsuarioSistema(nombre, grupo)

    def _usuario(self, nombre: str) -> UsuarioSistema:
        if not isinstance(nombre, str) or nombre not in self.usuarios:
            raise ErrorNoExiste(f"el usuario '{nombre}' no existe.")
        return self.usuarios[nombre]

    @staticmethod
    def _normalizar_ruta(ruta: str, base: str = "/") -> str:
        if not isinstance(ruta, str) or not ruta.strip():
            raise ValueError("La ruta debe ser una cadena no vacía.")

        ruta = ruta.strip()
        if ruta.startswith("/"):
            partes = ruta.split("/")
        else:
            partes = f"{base.rstrip('/')}/{ruta}".split("/")

        resultado = []
        for parte in partes:
            if parte in ("", "."):
                continue
            if parte == "..":
                if resultado:
                    resultado.pop()
                continue
            resultado.append(parte)
        return "/" + "/".join(resultado)

    @staticmethod
    def _componentes(ruta: str) -> list[str]:
        return [parte for parte in ruta.split("/") if parte]

    @staticmethod
    def _validar_nombre(nombre: str) -> None:
        if not nombre or nombre in (".", "..") or "/" in nombre or "\x00" in nombre:
            raise ValueError("El nombre de archivo o directorio no es válido.")

    @staticmethod
    def _permisos_numericos(nodo: NodoArchivo, usuario: UsuarioSistema) -> int:
        if usuario.nombre == "admin":
            return 7
        if usuario.nombre == nodo.propietario:
            posicion = 0
        elif usuario.grupo == nodo.grupo:
            posicion = 1
        else:
            posicion = 2
        return int(nodo.modo[posicion])

    def _comprobar_permiso(
        self,
        nodo: NodoArchivo,
        usuario: UsuarioSistema,
        requerido: str,
    ) -> None:
        permisos = self._permisos_numericos(nodo, usuario)
        mascara = {"r": 4, "w": 2, "x": 1}
        if any(not (permisos & mascara[permiso]) for permiso in requerido):
            raise ErrorPermiso(
                f"el usuario '{usuario.nombre}' no tiene permiso '{requerido}' "
                f"sobre '{self._ruta_nodo(nodo)}'."
            )

    def _ruta_nodo(self, objetivo: NodoArchivo) -> str:
        """Busca la ruta de una entidad; se usa solo para mensajes de error."""
        pila = [(self.raiz, "/")]
        while pila:
            nodo, ruta = pila.pop()
            if nodo is objetivo:
                return ruta
            if nodo.tipo == "directorio":
                for hijo in nodo.hijos.values():
                    ruta_hijo = ruta.rstrip("/") + "/" + hijo.nombre
                    pila.append((hijo, ruta_hijo))
        return "/"

    def _resolver_nodo(
        self,
        ruta: str,
        usuario: UsuarioSistema | None = None,
        seguir_final: bool = True,
        enlaces_vistos: int = 0,
    ) -> tuple[NodoArchivo, str]:
        ruta_normalizada = self._normalizar_ruta(ruta)
        if ruta_normalizada == "/":
            if usuario is not None:
                self._comprobar_permiso(self.raiz, usuario, "x")
            return self.raiz, "/"

        if enlaces_vistos > _MAX_ENLACES:
            raise ErrorSistema("se detectó un ciclo de enlaces simbólicos.")

        componentes = self._componentes(ruta_normalizada)
        actual = self.raiz
        ruta_actual = "/"

        for indice, componente in enumerate(componentes):
            if actual.tipo != "directorio":
                raise ErrorSistema(f"'{ruta_actual}' no es un directorio.")
            if usuario is not None:
                self._comprobar_permiso(actual, usuario, "x")

            siguiente = actual.hijos.get(componente)
            if siguiente is None:
                raise ErrorNoExiste(f"la ruta '{ruta_normalizada}' no existe.")

            es_final = indice == len(componentes) - 1
            if siguiente.tipo == "enlace" and (seguir_final or not es_final):
                ruta_padre = ruta_actual
                destino = siguiente.destino or ""
                destino_absoluto = self._normalizar_ruta(destino, ruta_padre)
                restantes = componentes[indice + 1 :]
                if restantes:
                    destino_absoluto = self._normalizar_ruta(
                        "/".join(restantes), destino_absoluto
                    )
                return self._resolver_nodo(
                    destino_absoluto,
                    usuario,
                    seguir_final,
                    enlaces_vistos + 1,
                )

            actual = siguiente
            ruta_actual = (
                ruta_actual.rstrip("/") + "/" + componente
                if ruta_actual != "/"
                else "/" + componente
            )

        return actual, ruta_actual

    def _obtener_padre(
        self, ruta: str, usuario: UsuarioSistema
    ) -> tuple[NodoArchivo, str, str]:
        ruta_normalizada = self._normalizar_ruta(ruta)
        if ruta_normalizada == "/":
            raise ErrorPermiso(
                "no se permite modificar o eliminar la raíz del sistema."
            )

        padre_ruta, nombre = ruta_normalizada.rsplit("/", 1)
        padre_ruta = padre_ruta or "/"
        self._validar_nombre(nombre)
        padre, _ = self._resolver_nodo(padre_ruta, usuario, True)
        if padre.tipo != "directorio":
            raise ErrorSistema(f"'{padre_ruta}' no es un directorio.")
        self._comprobar_permiso(padre, usuario, "wx")
        return padre, nombre, ruta_normalizada

    def _comprobar_directorio_accesible(
        self, nodo: NodoArchivo, usuario: UsuarioSistema
    ) -> None:
        if nodo.tipo != "directorio":
            raise ErrorSistema("la ruta indicada no es un directorio.")
        self._comprobar_permiso(nodo, usuario, "x")

    def fs_acceder_directorio(self, ruta: str, nombre_usuario: str) -> str:
        """Valida que el usuario pueda entrar al directorio y devuelve su ruta."""
        usuario = self._usuario(nombre_usuario)
        nodo, ruta_real = self._resolver_nodo(ruta, usuario, True)
        self._comprobar_directorio_accesible(nodo, usuario)
        return ruta_real

    def fs_mkdir(self, ruta: str, nombre_usuario: str) -> None:
        usuario = self._usuario(nombre_usuario)
        padre, nombre, ruta_normalizada = self._obtener_padre(ruta, usuario)
        if nombre in padre.hijos:
            raise ErrorYaExiste(f"la ruta '{ruta_normalizada}' ya existe.")

        padre.hijos[nombre] = NodoArchivo(
            nombre,
            "directorio",
            usuario.nombre,
            usuario.grupo,
            _MODO_POR_DEFECTO_DIRECTORIO,
        )

    def fs_crear_archivo(self, ruta: str, nombre_usuario: str) -> None:
        """Crea un archivo vacío; si existe, conserva su contenido (touch)."""
        usuario = self._usuario(nombre_usuario)
        try:
            nodo, _ = self._resolver_nodo(ruta, usuario, True)
            if nodo.tipo == "directorio":
                raise ErrorSistema(f"'{ruta}' es un directorio.")
            if nodo.tipo == "archivo":
                self._comprobar_permiso(nodo, usuario, "w")
            return
        except ErrorNoExiste:
            pass

        padre, nombre, ruta_normalizada = self._obtener_padre(ruta, usuario)
        if nombre in padre.hijos:
            raise ErrorYaExiste(f"la ruta '{ruta_normalizada}' ya existe.")
        padre.hijos[nombre] = NodoArchivo(
            nombre,
            "archivo",
            usuario.nombre,
            usuario.grupo,
            _MODO_POR_DEFECTO_ARCHIVO,
        )

    def _cantidad_bloques(self, contenido: str) -> int:
        cantidad_bytes = len(contenido.encode("utf-8"))
        if cantidad_bytes == 0:
            return 0
        return (cantidad_bytes + self.tam_bloque - 1) // self.tam_bloque

    def fs_escribir(
        self,
        ruta: str,
        contenido: str,
        nombre_usuario: str,
        agregar: bool = False,
    ) -> int:
        """Escribe o anexa contenido reservando bloques de forma atómica."""
        usuario = self._usuario(nombre_usuario)
        if not isinstance(contenido, str):
            raise ValueError("El contenido debe ser una cadena de texto.")
        if not isinstance(agregar, bool):
            raise ValueError("El parámetro 'agregar' debe ser booleano.")

        archivo_creado = False
        try:
            nodo, _ = self._resolver_nodo(ruta, usuario, True)
            if nodo.tipo != "archivo":
                raise ErrorSistema(f"'{ruta}' no es un archivo regular.")
            self._comprobar_permiso(nodo, usuario, "w")
            contenido_nuevo = nodo.contenido + contenido if agregar else contenido
        except ErrorNoExiste:
            self.fs_crear_archivo(ruta, nombre_usuario)
            archivo_creado = True
            nodo, _ = self._resolver_nodo(ruta, usuario, True)
            contenido_nuevo = contenido

        bloques_necesarios = self._cantidad_bloques(contenido_nuevo)
        bloques_actuales = len(nodo.bloques)
        diferencia = bloques_necesarios - bloques_actuales

        # Primero se reserva el espacio adicional
        if diferencia > 0:
            try:
                nuevos_bloques = self.asignador.asignar(diferencia)
            except ErrorSistema:
                if archivo_creado:
                    padre, nombre, _ = self._obtener_padre(ruta, usuario)
                    padre.hijos.pop(nombre, None)
                raise
            nodo.bloques.extend(nuevos_bloques)
        elif diferencia < 0:
            liberados = nodo.bloques[bloques_necesarios:]
            self.asignador.liberar(liberados)
            nodo.bloques = nodo.bloques[:bloques_necesarios]

        nodo.contenido = contenido_nuevo
        return len(contenido.encode("utf-8"))

    def fs_leer(self, ruta: str, nombre_usuario: str) -> str:
        usuario = self._usuario(nombre_usuario)
        nodo, _ = self._resolver_nodo(ruta, usuario, True)
        if nodo.tipo != "archivo":
            raise ErrorSistema(f"'{ruta}' no es un archivo regular.")
        self._comprobar_permiso(nodo, usuario, "r")
        return nodo.contenido

    def fs_listar(self, ruta: str, nombre_usuario: str) -> list[str]:
        usuario = self._usuario(nombre_usuario)
        nodo, ruta_real = self._resolver_nodo(ruta, usuario, True)
        if nodo.tipo == "directorio":
            self._comprobar_permiso(nodo, usuario, "rx")
            return sorted(nodo.hijos)
        self._comprobar_permiso(nodo, usuario, "r")
        nombre_mostrado = self._normalizar_ruta(ruta).rstrip("/").split("/")[-1]
        return [nombre_mostrado]

    def _validar_permisos_eliminacion(
        self, nodo: NodoArchivo, usuario: UsuarioSistema
    ) -> None:
        """Comprueba permisos wx en cada directorio recorrido por rm -r."""
        if nodo.tipo != "directorio":
            return
        self._comprobar_permiso(nodo, usuario, "wx")
        for hijo in nodo.hijos.values():
            if hijo.tipo == "directorio":
                self._validar_permisos_eliminacion(hijo, usuario)

    def _liberar_subarbol(self, nodo: NodoArchivo) -> None:
        if nodo.tipo == "directorio":
            for hijo in list(nodo.hijos.values()):
                self._liberar_subarbol(hijo)
        if nodo.bloques:
            self.asignador.liberar(nodo.bloques)
            nodo.bloques.clear()

    def fs_eliminar(
        self, ruta: str, nombre_usuario: str, recursivo: bool = False
    ) -> None:
        usuario = self._usuario(nombre_usuario)
        if not isinstance(recursivo, bool):
            raise ValueError("El parámetro 'recursivo' debe ser booleano.")
        padre, nombre, ruta_normalizada = self._obtener_padre(ruta, usuario)
        nodo = padre.hijos.get(nombre)
        if nodo is None:
            raise ErrorNoExiste(f"la ruta '{ruta_normalizada}' no existe.")

        if nodo.tipo == "directorio" and nodo.hijos and not recursivo:
            raise ErrorSistema(
                f"el directorio '{ruta_normalizada}' no está vacío; use rm -r."
            )
        if nodo.tipo == "directorio" and recursivo:
            self._validar_permisos_eliminacion(nodo, usuario)

        self._liberar_subarbol(nodo)
        del padre.hijos[nombre]

    def fs_chmod(self, ruta: str, modo: str, nombre_usuario: str) -> None:
        usuario = self._usuario(nombre_usuario)
        if not isinstance(modo, str) or re.fullmatch(r"[0-7]{3}", modo) is None:
            raise ValueError(
                "El modo debe contener tres dígitos octales, por ejemplo 640."
            )

        nodo, _ = self._resolver_nodo(ruta, usuario, True)
        if usuario.nombre != "admin" and usuario.nombre != nodo.propietario:
            raise ErrorPermiso(
                "solo el propietario o admin puede cambiar los permisos."
            )
        nodo.modo = modo

    def fs_enlace_simbolico(
        self, destino: str, ruta_enlace: str, nombre_usuario: str
    ) -> None:
        usuario = self._usuario(nombre_usuario)
        if not isinstance(destino, str) or not destino:
            raise ValueError("El destino del enlace no puede estar vacío.")
        padre, nombre, ruta_normalizada = self._obtener_padre(ruta_enlace, usuario)
        if nombre in padre.hijos:
            raise ErrorYaExiste(f"la ruta '{ruta_normalizada}' ya existe.")
        padre.hijos[nombre] = NodoArchivo(
            nombre,
            "enlace",
            usuario.nombre,
            usuario.grupo,
            "777",
            destino=destino,
        )

    def fs_info(self, ruta: str) -> dict:
        nodo, _ = self._resolver_nodo(ruta, None, False)
        if nodo.tipo == "archivo":
            tamano = len(nodo.contenido.encode("utf-8"))
        elif nodo.tipo == "enlace":
            tamano = len((nodo.destino or "").encode("utf-8"))
        else:
            tamano = 0
        return {
            "tipo": nodo.tipo,
            "tamano": tamano,
            "propietario": nodo.propietario,
            "grupo": nodo.grupo,
            "modo": nodo.modo,
            "bloques": list(nodo.bloques),
        }

    def fs_estado_disco(self) -> dict:
        return self.asignador.estado()

    def politica_asignacion_archivos(self) -> str:
        return "Asignación indexada"


_sistema = SistemaArchivos()


def _configurar(bloques_totales: int, tam_bloque: int) -> None:
    """Configura y reinicia el sistema de archivos desde el kernel."""
    _sistema.configurar(bloques_totales, tam_bloque)


def formatear_disco() -> None:
    _sistema.formatear_disco()


def crear_usuario(nombre: str, grupo: str = "usuarios") -> None:
    _sistema.crear_usuario(nombre, grupo)


def fs_mkdir(ruta: str, usuario: str) -> None:
    _sistema.fs_mkdir(ruta, usuario)


def fs_escribir(ruta: str, contenido: str, usuario: str, agregar: bool = False) -> int:
    return _sistema.fs_escribir(ruta, contenido, usuario, agregar)


def fs_leer(ruta: str, usuario: str) -> str:
    return _sistema.fs_leer(ruta, usuario)


def fs_listar(ruta: str, usuario: str) -> list[str]:
    return _sistema.fs_listar(ruta, usuario)


def fs_eliminar(ruta: str, usuario: str, recursivo: bool = False) -> None:
    _sistema.fs_eliminar(ruta, usuario, recursivo)


def fs_chmod(ruta: str, modo: str, usuario: str) -> None:
    _sistema.fs_chmod(ruta, modo, usuario)


def fs_enlace_simbolico(destino: str, ruta_enlace: str, usuario: str) -> None:
    _sistema.fs_enlace_simbolico(destino, ruta_enlace, usuario)


def fs_info(ruta: str) -> dict:
    return _sistema.fs_info(ruta)


def fs_estado_disco() -> dict:
    return _sistema.fs_estado_disco()


def politica_asignacion_archivos() -> str:
    return _sistema.politica_asignacion_archivos()


def fs_crear_archivo(ruta: str, usuario: str) -> None:
    """Operación auxiliar usada por el comando touch."""
    _sistema.fs_crear_archivo(ruta, usuario)


def fs_acceder_directorio(ruta: str, usuario: str) -> str:
    """Operación auxiliar para validar el comando cd."""
    return _sistema.fs_acceder_directorio(ruta, usuario)
