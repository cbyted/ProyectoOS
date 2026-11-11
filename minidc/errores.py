"""
Excepciones propias para errores de permisos,
recursos, memoria y sincronización del sistema
NimbusDC.
"""


class ErrorSistema(Exception):
    pass


class ErrorPermiso(ErrorSistema):
    pass


class ErrorNoExiste(ErrorSistema):
    pass


class ErrorYaExiste(ErrorSistema):
    pass


class ErrorMemoria(ErrorSistema):
    pass


class ErrorSincronizacion(ErrorSistema):
    pass
