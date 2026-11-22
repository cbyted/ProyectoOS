class Pagina:
    """Información de una página de un proceso."""

    def __init__(
        self,
        marco: int | None = None,
        presente: bool = False,
        modificada: bool = False,
        referenciada: bool = False,
    ):
        self.marco = marco
        self.presente = presente
        self.modificada = modificada
        self.referenciada = referenciada
