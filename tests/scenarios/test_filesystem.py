"""Pruebas de caja negra para el sistema de archivos y permisos."""

from __future__ import annotations

import pytest

from minidc import archivos, kernel
from minidc.errores import ErrorNoExiste, ErrorPermiso, ErrorSistema, ErrorYaExiste


def _reiniciar():
    kernel.iniciar_sistema(
        {
            "num_cpus": 1,
            "marcos_fisicos": 8,
            "tam_pagina": 256,
            "bloques_disco": 50,
            "tam_bloque": 64,
            "cache_bloques": 4,
        }
    )


def _preparar(usuarios_base):
    archivos.fs_mkdir("/data", "admin")
    archivos.fs_chmod("/data", "777", "admin")


def _assert_conservacion():
    estado = archivos.fs_estado_disco()
    usados = estado["bloques_totales"] - estado["bloques_libres"]
    assert usados >= 0
    assert estado["bloques_libres"] >= 0
    assert usados + estado["bloques_libres"] == estado["bloques_totales"]


def test_formatear_disco_reinicia_arbol_usuarios_y_bloques(usuarios_base):
    archivos.fs_escribir("/archivo", "datos", "admin")
    assert archivos.fs_estado_disco()["bloques_libres"] == 199
    archivos.formatear_disco()
    info_raiz = archivos.fs_info("/")
    assert info_raiz["tipo"] == "directorio"
    assert info_raiz["propietario"] == "admin"
    assert archivos.fs_estado_disco()["bloques_libres"] == 200
    archivos.crear_usuario("alice", "g1")


def test_mkdir_listar_e_info_de_archivos_y_directorios(usuarios_base):
    _preparar(usuarios_base)
    archivos.fs_mkdir("/data/docs", "admin")
    archivos.fs_escribir("/data/docs/nota.txt", "hola", "admin")
    assert archivos.fs_listar("/data", "admin") == ["docs"]
    assert archivos.fs_listar("/data/docs", "admin") == ["nota.txt"]
    info_dir = archivos.fs_info("/data/docs")
    assert info_dir["tipo"] == "directorio"
    info_archivo = archivos.fs_info("/data/docs/nota.txt")
    assert info_archivo["tipo"] == "archivo"
    assert info_archivo["tamano"] == 4
    assert info_archivo["propietario"] == "admin"
    assert isinstance(info_archivo["bloques"], list)


def test_escribir_leer_agregar_y_reemplazar(usuarios_base):
    _preparar(usuarios_base)
    assert archivos.fs_escribir("/data/f", "hola", "alice") == 4
    assert archivos.fs_leer("/data/f", "alice") == "hola"
    assert archivos.fs_escribir("/data/f", " mundo", "alice", agregar=True) == 6
    assert archivos.fs_leer("/data/f", "alice") == "hola mundo"
    assert archivos.fs_escribir("/data/f", "adios", "alice") == 5
    assert archivos.fs_leer("/data/f", "alice") == "adios"
    assert archivos.fs_info("/data/f")["tamano"] == 5


def test_eliminar_archivo_y_directorio_recursivo(usuarios_base):
    _preparar(usuarios_base)
    archivos.fs_mkdir("/data/a", "admin")
    archivos.fs_escribir("/data/a/f", "x", "admin")
    assert archivos.fs_estado_disco()["bloques_libres"] == 199
    with pytest.raises(ErrorSistema):
        archivos.fs_eliminar("/data/a", "admin")
    archivos.fs_eliminar("/data/a", "admin", recursivo=True)
    assert archivos.fs_estado_disco()["bloques_libres"] == 200
    with pytest.raises(ErrorNoExiste):
        archivos.fs_listar("/data/a", "admin")


def test_permisos_de_propietario_grupo_y_otros(usuarios_base):
    _preparar(usuarios_base)
    archivos.fs_escribir("/data/f", "secreto", "alice")
    archivos.fs_chmod("/data/f", "640", "alice")

    assert archivos.fs_leer("/data/f", "alice") == "secreto"
    assert archivos.fs_escribir("/data/f", "x", "alice") == 1
    assert archivos.fs_leer("/data/f", "bob") == "x"
    with pytest.raises(ErrorPermiso):
        archivos.fs_escribir("/data/f", "y", "bob")
    with pytest.raises(ErrorPermiso):
        archivos.fs_leer("/data/f", "carol")
    with pytest.raises(ErrorPermiso):
        archivos.fs_escribir("/data/f", "z", "carol")


def test_chmod_solo_lo_puede_hacer_el_propietario_o_admin(usuarios_base):
    _preparar(usuarios_base)
    archivos.fs_escribir("/data/f", "x", "alice")
    with pytest.raises(ErrorPermiso):
        archivos.fs_chmod("/data/f", "600", "bob")
    archivos.fs_chmod("/data/f", "600", "alice")
    assert archivos.fs_info("/data/f")["modo"] == "600"
    archivos.fs_chmod("/data/f", "644", "admin")
    assert archivos.fs_info("/data/f")["modo"] == "644"


def test_acceso_administrativo_ignora_permisos(usuarios_base):
    _preparar(usuarios_base)
    archivos.fs_escribir("/data/f", "x", "alice")
    archivos.fs_chmod("/data/f", "000", "alice")
    with pytest.raises(ErrorPermiso):
        archivos.fs_leer("/data/f", "alice")
    assert archivos.fs_leer("/data/f", "admin") == "x"
    assert archivos.fs_escribir("/data/f", "y", "admin") == 1


def test_enlace_simbolico_y_lectura_a_traves_del_enlace(usuarios_base):
    _preparar(usuarios_base)
    archivos.fs_escribir("/data/f", "contenido", "alice")
    archivos.fs_enlace_simbolico("/data/f", "/data/link", "alice")
    info = archivos.fs_info("/data/link")
    assert info["tipo"] == "enlace"
    assert set(archivos.fs_listar("/data", "admin")) == {"f", "link"}
    assert archivos.fs_leer("/data/link", "alice") == "contenido"


def test_conservacion_de_bloques_durante_operaciones_intermedias(usuarios_base):
    _preparar(usuarios_base)
    _assert_conservacion()
    archivos.fs_mkdir("/data/docs", "admin")
    archivos.fs_chmod("/data/docs", "777", "admin")
    _assert_conservacion()
    archivos.fs_escribir("/data/docs/a", "x" * 100, "alice")
    _assert_conservacion()
    archivos.fs_escribir("/data/docs/a", "y", "alice")
    _assert_conservacion()
    archivos.fs_enlace_simbolico("/data/docs/a", "/data/docs/link", "alice")
    _assert_conservacion()
    archivos.fs_eliminar("/data/docs/a", "alice")
    _assert_conservacion()
    archivos.fs_eliminar("/data/docs", "admin", recursivo=True)
    _assert_conservacion()
    assert archivos.fs_estado_disco()["bloques_libres"] == 200


def test_RF1_sin_permisos_toda_operacion_lanza_ErrorPermiso(usuarios_base):
    _preparar(usuarios_base)
    archivos.fs_escribir("/data/f", "x", "alice")
    archivos.fs_chmod("/data/f", "600", "alice")
    operaciones = [
        lambda: archivos.fs_leer("/data/f", "bob"),
        lambda: archivos.fs_escribir("/data/f", "y", "bob"),
    ]
    for operacion in operaciones:
        with pytest.raises(ErrorPermiso):
            operacion()
    _assert_conservacion()


def test_errores_de_duplicados_y_recursos_inexistentes(usuarios_base):
    _preparar(usuarios_base)
    with pytest.raises(ErrorYaExiste):
        archivos.crear_usuario("alice", "g1")
    archivos.fs_mkdir("/data/docs", "admin")
    with pytest.raises(ErrorYaExiste):
        archivos.fs_mkdir("/data/docs", "admin")
    with pytest.raises(ErrorNoExiste):
        archivos.fs_mkdir("/data/no/existe", "admin")
    with pytest.raises(ErrorNoExiste):
        archivos.fs_leer("/data/no.txt", "admin")
    with pytest.raises(ValueError):
        archivos.fs_chmod("/data/docs", "9999", "admin")
    with pytest.raises(ErrorSistema):
        archivos.fs_leer("/data/docs", "admin")


def test_politica_y_estado_del_sistema_de_archivos():
    politica = archivos.politica_asignacion_archivos()
    assert isinstance(politica, str)
    assert politica.strip() != ""
    estado = archivos.fs_estado_disco()
    assert set(estado) == {"bloques_totales", "bloques_libres", "huecos_libres"}
    assert estado["bloques_totales"] == 200
