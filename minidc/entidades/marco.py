class Marco:
    """Un marco físico; está libre si pid y pagina son None."""

    def __init__(
        self,
        numero: int,
        pid: int | None = None,
        pagina: int | None = None,
        referenciada: bool = False,
        modificada: bool = False,
        ultimo_uso: int = -1,
    ):
        self.numero = numero
        self.pid = pid
        self.pagina = pagina
        self.referenciada = referenciada
        self.modificada = modificada
        self.ultimo_uso = ultimo_uso

    def libre(self) -> bool:
        return self.pid is None

    def asignar(self, pid: int, pagina: int, tick: int) -> None:
        self.pid = pid
        self.pagina = pagina
        self.referenciada = True
        self.modificada = False
        self.ultimo_uso = tick

    def registrar_uso(self, tick: int, escritura: bool = False) -> None:
        self.referenciada = True
        self.ultimo_uso = tick
        if escritura:
            self.modificada = True

    def liberar(self) -> None:
        self.pid = None
        self.pagina = None
        self.referenciada = False
        self.modificada = False
        self.ultimo_uso = -1
