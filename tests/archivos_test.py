import pytest

from minidc import archivos, kernel
from minidc.errores import ErrorNoExiste, ErrorPermiso, ErrorSistema, ErrorYaExiste


CONFIG = {
    "num_cpus": 1,
    "marcos_fisicos": 8,
    "tam_pagina": 256,
    "bloques_disco": 12,
    "tam_bloque": 4,
    "cache_bloques": 2,
}


@pytest.fixture(autouse=True)
def sistema_inicializado():
    kernel.iniciar_sistema(CONFIG)
    yield
    kernel.iniciar_sistema(CONFIG)


def test_formatear_disco_crea_admin_y_directorio_raiz():
    archivos.formatear_disco()

    assert archivos.fs_info("/") == {
        "tipo": "directorio",
        "tamano": 0,
        "propietario": "admin",
        "grupo": "admin",
        "modo": "755",
        "bloques": [],
    }
    assert archivos.fs_estado_disco()["bloques_libres"] == CONFIG["bloques_disco"]


def test_crear_usuario_y_rechazar_duplicados():
    archivos.crear_usuario("ana", "equipo")

    with pytest.raises(ErrorYaExiste):
        archivos.crear_usuario("ana", "equipo")


def test_escribir_leer_anexar_y_sobrescribir():
    archivos.fs_mkdir("/datos", "admin")
    assert archivos.fs_escribir("/datos/a.txt", "hola", "admin") == 4
    assert archivos.fs_escribir("/datos/a.txt", "!", "admin", agregar=True) == 1
    assert archivos.fs_leer("/datos/a.txt", "admin") == "hola!"

    archivos.fs_escribir("/datos/a.txt", "x", "admin")
    assert archivos.fs_leer("/datos/a.txt", "admin") == "x"
    assert archivos.fs_info("/datos/a.txt")["tamano"] == 1
    assert archivos.fs_info("/datos/a.txt")["bloques"] == [0]


def test_eliminar_libera_bloques_y_mantiene_contabilidad():
    archivos.fs_escribir("/a.txt", "abcdefghij", "admin")
    estado = archivos.fs_estado_disco()
    assert estado["bloques_totales"] - estado["bloques_libres"] == 3

    archivos.fs_eliminar("/a.txt", "admin")
    estado = archivos.fs_estado_disco()
    assert (estado["bloques_totales"] - estado["bloques_libres"]) == 0
    assert estado["bloques_libres"] == estado["bloques_totales"]
    usados = estado["bloques_totales"] - estado["bloques_libres"]
    assert usados + estado["bloques_libres"] == estado["bloques_totales"]


def test_sobrescritura_libera_bloques_sobrantes():
    archivos.fs_escribir("/a.txt", "abcdefghij", "admin")
    archivos.fs_escribir("/a.txt", "x", "admin")

    estado = archivos.fs_estado_disco()
    assert (estado["bloques_totales"] - estado["bloques_libres"]) == 1
    assert estado["bloques_libres"] == 11
    assert (estado["bloques_totales"] - estado["bloques_libres"]) + estado[
        "bloques_libres"
    ] == 12


def test_eliminar_directorio_no_vacio_requiere_recursivo():
    archivos.fs_mkdir("/datos", "admin")
    archivos.fs_escribir("/datos/a.txt", "x", "admin")

    with pytest.raises(ErrorSistema):
        archivos.fs_eliminar("/datos", "admin")

    archivos.fs_eliminar("/datos", "admin", recursivo=True)
    with pytest.raises(ErrorNoExiste):
        archivos.fs_info("/datos")
    estado = archivos.fs_estado_disco()
    assert estado["bloques_totales"] - estado["bloques_libres"] == 0


def test_permisos_unix_se_aplican_a_otros_usuarios():
    archivos.crear_usuario("ana", "ventas")
    archivos.crear_usuario("luis", "soporte")
    archivos.fs_mkdir("/compartido", "admin")
    archivos.fs_chmod("/compartido", "777", "admin")
    archivos.fs_escribir("/compartido/privado.txt", "secreto", "ana")
    archivos.fs_chmod("/compartido/privado.txt", "600", "ana")

    with pytest.raises(ErrorPermiso):
        archivos.fs_leer("/compartido/privado.txt", "luis")

    assert archivos.fs_leer("/compartido/privado.txt", "admin") == "secreto"


def test_permisos_de_grupo_se_aplican_antes_que_los_de_otros():
    archivos.crear_usuario("ana", "ventas")
    archivos.crear_usuario("luis", "ventas")
    archivos.crear_usuario("marta", "soporte")
    archivos.fs_mkdir("/compartido", "admin")
    archivos.fs_chmod("/compartido", "777", "admin")
    archivos.fs_escribir("/compartido/reporte.txt", "reporte", "ana")
    archivos.fs_chmod("/compartido/reporte.txt", "640", "ana")

    assert archivos.fs_leer("/compartido/reporte.txt", "luis") == "reporte"
    with pytest.raises(ErrorPermiso):
        archivos.fs_escribir("/compartido/reporte.txt", "cambio", "luis")
    with pytest.raises(ErrorPermiso):
        archivos.fs_leer("/compartido/reporte.txt", "marta")


def test_propietario_puede_cambiar_permisos_y_otro_usuario_no():
    archivos.crear_usuario("ana")
    archivos.crear_usuario("luis")
    archivos.fs_mkdir("/datos", "admin")
    archivos.fs_chmod("/datos", "777", "admin")
    archivos.fs_escribir("/datos/a.txt", "x", "ana")

    with pytest.raises(ErrorPermiso):
        archivos.fs_chmod("/datos/a.txt", "644", "luis")

    archivos.fs_chmod("/datos/a.txt", "640", "ana")
    assert archivos.fs_info("/datos/a.txt")["modo"] == "640"


def test_enlace_simbolico_se_sigue_al_leer_y_se_elimina_sin_borrar_destino():
    archivos.fs_escribir("/original.txt", "contenido", "admin")
    archivos.fs_enlace_simbolico("original.txt", "/alias.txt", "admin")

    assert archivos.fs_leer("/alias.txt", "admin") == "contenido"
    assert archivos.fs_info("/alias.txt")["tipo"] == "enlace"
    archivos.fs_eliminar("/alias.txt", "admin")
    assert archivos.fs_leer("/original.txt", "admin") == "contenido"


def test_ruta_inexistente_y_eliminacion_de_raiz_generan_error():
    with pytest.raises(ErrorNoExiste):
        archivos.fs_leer("/no-existe", "admin")
    with pytest.raises(ErrorPermiso):
        archivos.fs_eliminar("/", "admin", recursivo=True)


def test_error_por_falta_de_espacio_no_rompe_contabilidad():
    tamano_maximo = CONFIG["bloques_disco"] * CONFIG["tam_bloque"]
    archivos.fs_escribir("/grande.txt", "x" * tamano_maximo, "admin")
    with pytest.raises(ErrorSistema):
        archivos.fs_escribir("/otro.txt", "x", "admin")

    estado = archivos.fs_estado_disco()
    usados = estado["bloques_totales"] - estado["bloques_libres"]
    assert usados + estado["bloques_libres"] == estado["bloques_totales"]


def test_reiniciar_kernel_limpia_archivos_y_usuarios():
    archivos.crear_usuario("ana")
    archivos.fs_escribir("/a.txt", "dato", "admin")

    kernel.iniciar_sistema(CONFIG)

    estado = archivos.fs_estado_disco()
    assert estado["bloques_totales"] - estado["bloques_libres"] == 0
    with pytest.raises(ErrorNoExiste):
        archivos.fs_info("/a.txt")
    with pytest.raises(ErrorNoExiste):
        archivos.fs_mkdir("/datos", "ana")


def test_conteo_de_bloques_usa_bytes_utf8():
    archivos.fs_escribir("/acentos.txt", "áéí", "admin")

    info = archivos.fs_info("/acentos.txt")
    estado = archivos.fs_estado_disco()

    assert info["tamano"] == 6
    assert info["bloques"] == [0, 1]
    assert estado["bloques_libres"] == CONFIG["bloques_disco"] - 2


def test_escritura_sin_espacio_no_deja_un_archivo_vacio():
    contenido = "x" * (CONFIG["bloques_disco"] * CONFIG["tam_bloque"] + 1)
    bloques_antes = archivos.fs_estado_disco()["bloques_libres"]

    with pytest.raises(ErrorSistema):
        archivos.fs_escribir("/sin_espacio.txt", contenido, "admin")

    with pytest.raises(ErrorNoExiste):
        archivos.fs_info("/sin_espacio.txt")
    assert archivos.fs_estado_disco()["bloques_libres"] == bloques_antes


def test_chmod_respeta_permisos_de_travesia():
    archivos.crear_usuario("ana")
    archivos.fs_mkdir("/privado", "admin")
    archivos.fs_chmod("/privado", "700", "admin")
    archivos.fs_escribir("/privado/dato.txt", "dato", "admin")

    with pytest.raises(ErrorPermiso):
        archivos.fs_chmod("/privado/dato.txt", "600", "ana")


def test_permiso_de_ejecucion_en_directorio_raiz():
    archivos.crear_usuario("ana")
    archivos.fs_chmod("/", "700", "admin")

    with pytest.raises(ErrorPermiso):
        archivos.fs_acceder_directorio("/", "ana")


def test_fallo_de_escritura_conserva_el_contenido_anterior():
    contenido_original = "a" * (10 * CONFIG["tam_bloque"])
    archivos.fs_escribir("/estable.txt", contenido_original, "admin")
    bloques_antes = archivos.fs_estado_disco()["bloques_libres"]

    with pytest.raises(ErrorSistema):
        archivos.fs_escribir(
            "/estable.txt", "b" * (3 * CONFIG["tam_bloque"]), "admin", agregar=True
        )

    assert archivos.fs_leer("/estable.txt", "admin") == contenido_original
    assert archivos.fs_estado_disco()["bloques_libres"] == bloques_antes
