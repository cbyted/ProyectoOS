"""
Algoritmo LRU para el remplazo de páginas.
Elimina la página que no se ha usado en más tiempo
"""


class LRU:
    def datos_marco(self, marco):
        return (marco.ultimo_uso, marco.numero)

    def pagina_menos_usada(self, marcos: list) -> None:
        # Guardar los marcos que estan en uso
        marcos_en_uso = [marco for marco in marcos if not marco.libre()]

        if len(marcos_en_uso) == 0:
            raise ValueError("No hay marcos en uso")

        pagina_menos_usada = min(marcos_en_uso, key=self.datos_marco)

        return pagina_menos_usada.numero
