from .pagina import Pagina

"""
Espacio de direcciones lógicas de un proceso
"""


class EspacioDirecciones:
    def __init__(self, pid: int, memoria_bytes: int, tam_pagina: int):
        if memoria_bytes <= 0:
            raise ValueError("memoria_bytes debe ser mayor que cero")
        if tam_pagina <= 0:
            raise ValueError("tam_pagina debe ser mayor que cero")

        self.pid = pid
        self.memoria_bytes = memoria_bytes
        self.tam_pagina = tam_pagina

        cantidad_paginas = (memoria_bytes + tam_pagina - 1) // tam_pagina
        self.paginas = {numero: Pagina() for numero in range(cantidad_paginas)}

    def direccion_valida(self, direccion: int) -> bool:
        return 0 <= direccion < self.memoria_bytes

    def obtener_pagina(self, direccion: int) -> int:
        if not self.direccion_valida(direccion):
            raise ValueError("Dirección virtual fuera del espacio")
        return direccion // self.tam_pagina
