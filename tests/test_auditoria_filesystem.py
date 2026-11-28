"""Auditoría de caja negra del sistema de archivos y permisos."""
from __future__ import annotations

import pytest

from minidc import archivos
from minidc.errores import ErrorPermiso, ErrorYaExiste, ErrorNoExiste, ErrorSistema


def _crear_usuarios_y_directorio():
    archivos.crear_usuario("alice", "equipo")
    archivos.crear_usuario("bob", "equipo")
    archivos.crear_usuario("carol", "externos")
    archivos.fs_mkdir("/data", "admin")
    archivos.fs_chmod("/data", "777", "admin")


def _verificar_bloques_efectivos(rutas_archivo):
    """Compara espacio libre con bloques observados a través de fs_info()."""
    estado = archivos.fs_estado_disco()
    asignados = set()
    for ruta in rutas_archivo:
        try:
            info = archivos.fs_info(ruta)
        except ErrorNoExiste:
            continue
        if info.get("tipo") == "archivo":
            asignados.update(info.get("bloques", []))
    usados_observables = estado["bloques_totales"] - estado["bloques_libres"]
    assert usados_observables == len(asignados), (
        "El espacio libre no coincide con los bloques visibles en fs_info()"
    )
    assert estado["bloques_libres"] + len(asignados) == estado["bloques_totales"]


def test_crear_escribir_agregar_reemplazar_y_eliminar_conserva_bloques(sistema_limpio):
    _crear_usuarios_y_directorio()
    rutas = ["/data/a", "/data/b"]
    _verificar_bloques_efectivos(rutas)

    archivos.fs_escribir(rutas[0], "x" * 100, "alice")
    _verificar_bloques_efectivos(rutas)
    archivos.fs_escribir(rutas[0], "y" * 64, "alice", agregar=True)
    _verificar_bloques_efectivos(rutas)
    archivos.fs_escribir(rutas[0], "z", "alice")
    _verificar_bloques_efectivos(rutas)
    archivos.fs_escribir(rutas[1], "b" * 130, "bob")
    _verificar_bloques_efectivos(rutas)

    assert archivos.fs_leer(rutas[0], "alice") == "z"
    assert archivos.fs_leer(rutas[1], "bob") == "b" * 130
    archivos.fs_eliminar(rutas[0], "alice")
    _verificar_bloques_efectivos(rutas)
    archivos.fs_eliminar(rutas[1], "bob")
    _verificar_bloques_efectivos(rutas)


def test_permisos_de_propietario_grupo_y_otros(sistema_limpio):
    _crear_usuarios_y_directorio()
    archivos.fs_escribir("/data/secreto", "privado", "alice")
    archivos.fs_chmod("/data/secreto", "640", "alice")

    assert archivos.fs_leer("/data/secreto", "alice") == "privado"
    assert archivos.fs_leer("/data/secreto", "bob") == "privado"
    with pytest.raises(ErrorPermiso):
        archivos.fs_escribir("/data/secreto", "x", "bob")
    with pytest.raises(ErrorPermiso):
        archivos.fs_leer("/data/secreto", "carol")
    with pytest.raises(ErrorPermiso):
        archivos.fs_escribir("/data/secreto", "x", "carol")
    assert archivos.fs_leer("/data/secreto", "admin") == "privado"


def test_directorios_listado_enlaces_y_eliminacion_recursiva(sistema_limpio):
    _crear_usuarios_y_directorio()
    archivos.fs_mkdir("/data/docs", "alice")
    archivos.fs_escribir("/data/docs/nota.txt", "contenido", "alice")
    archivos.fs_enlace_simbolico("/data/docs/nota.txt", "/data/docs/acceso", "alice")

    assert "docs" in archivos.fs_listar("/data", "admin")
    assert archivos.fs_info("/data/docs")["tipo"] == "directorio"
    assert archivos.fs_info("/data/docs/acceso")["tipo"] == "enlace"
    assert archivos.fs_leer("/data/docs/acceso", "alice") == "contenido"

    with pytest.raises(ErrorSistema):
        archivos.fs_eliminar("/data/docs", "alice")
    archivos.fs_eliminar("/data/docs", "admin", recursivo=True)
    with pytest.raises(ErrorNoExiste):
        archivos.fs_info("/data/docs")
    assert archivos.fs_estado_disco()["bloques_libres"] == archivos.fs_estado_disco()["bloques_totales"]


def test_duplicados_y_rutas_inexistentes_se_reportan(sistema_limpio):
    _crear_usuarios_y_directorio()
    with pytest.raises(ErrorYaExiste):
        archivos.crear_usuario("alice", "equipo")
    archivos.fs_mkdir("/data/docs", "admin")
    with pytest.raises(ErrorYaExiste):
        archivos.fs_mkdir("/data/docs", "admin")
    with pytest.raises(ErrorNoExiste):
        archivos.fs_info("/ruta/no-existente")
