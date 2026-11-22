from dataclasses import dataclass, field


@dataclass
class NodoArchivo:
    """Representa un archivo, directorio o enlace simbólico."""

    nombre: str
    tipo: str
    propietario: str
    grupo: str
    modo: str
    contenido: str = ""
    destino: str | None = None
    bloques: list[int] = field(default_factory=list)
    hijos: dict[str, "NodoArchivo"] = field(default_factory=dict)


@dataclass(frozen=True)
class UsuarioSistema:
    """Información para permisos Unix."""

    nombre: str
    grupo: str
