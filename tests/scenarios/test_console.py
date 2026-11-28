"""Pruebas de caja negra para la consola de comandos."""

from __future__ import annotations

import pytest

from minidc import archivos, consola, kernel, memoria, procesos


def _preparar_usuarios(usuarios_base):
    archivos.fs_mkdir("/data", "admin")
    archivos.fs_chmod("/data", "777", "admin")


def _cargar_catalogo(cargar_escenario):
    cargar_escenario(
        usuarios=["alice"],
        catalogo={
            "web": {
                "memoria_bytes": 512,
                "cuota_marcos": 2,
                "prioridad": 1,
                "programa": [["CPU", 3]],
            }
        },
        llegadas=[],
    )


def test_comandos_de_archivos_pwd_cd_ls_mkdir_touch_echo_cat_rm_tree(usuarios_base):
    _preparar_usuarios(usuarios_base)
    assert consola.ejecutar_comando("pwd") == "/"
    assert "creado" in consola.ejecutar_comando("mkdir /data/docs").lower()
    assert consola.ejecutar_comando("cd /data/docs") == ""
    assert consola.directorio_actual() == "/data/docs"
    assert "preparado" in consola.ejecutar_comando("touch /data/docs/a.txt").lower()
    assert consola.ejecutar_comando("ls") == "a.txt"
    assert "4 bytes" in consola.ejecutar_comando("echo hola > /data/docs/a.txt")
    assert consola.ejecutar_comando("cat /data/docs/a.txt") == "hola"
    assert "5 bytes" in consola.ejecutar_comando("echo mundo >> /data/docs/a.txt")
    assert consola.ejecutar_comando("cat /data/docs/a.txt") == "holamundo"
    arbol = consola.ejecutar_comando("tree /data")
    assert "docs" in arbol
    assert "a.txt" in arbol
    assert "Eliminado" in consola.ejecutar_comando("rm /data/docs/a.txt")
    assert consola.ejecutar_comando("ls /data/docs") == "(directorio vacío)"
    assert "Eliminado" in consola.ejecutar_comando("rm -r /data/docs")
    assert consola.ejecutar_comando("ls /data") == "(directorio vacío)"


def test_comando_ls_l_muestra_modo_propietario_grupo_y_tamano(usuarios_base):
    _preparar_usuarios(usuarios_base)
    archivos.fs_escribir("/data/f", "hola", "admin")
    salida = consola.ejecutar_comando("ls -l /data")
    lineas = salida.splitlines()
    assert lineas[0].startswith("MODO PROPIETARIO GRUPO")
    assert "NOMBRE" in lineas[0]
    assert any("admin" in linea and "f" in linea for linea in lineas[1:])


def test_comandos_chmod_y_enlace_simbolico(usuarios_base):
    _preparar_usuarios(usuarios_base)
    archivos.fs_escribir("/data/f", "contenido", "alice")
    assert "600" in consola.ejecutar_comando("chmod 600 /data/f", "admin")
    assert consola.ejecutar_comando("cat /data/f", "bob").startswith("Error:")
    assert "Enlace" in consola.ejecutar_comando("ln -s /data/f /data/link", "admin")
    assert consola.ejecutar_comando("cat /data/link", "admin") == "contenido"


def test_comandos_de_procesos_run_ps_kill_tick_top(cargar_escenario):
    _cargar_catalogo(cargar_escenario)
    salida_ps = consola.ejecutar_comando("ps")
    assert salida_ps.splitlines()[0] == "PID NOMBRE USUARIO ESTADO"

    salida_run = consola.ejecutar_comando("run web")
    assert "PID 0" in salida_run
    salida_ps = consola.ejecutar_comando("ps")
    assert salida_ps.splitlines()[0] == "PID NOMBRE USUARIO ESTADO"
    assert "0 web admin NUEVO" in salida_ps

    assert consola.ejecutar_comando("tick 2") == "Reloj actual: 2"
    salida_top = consola.ejecutar_comando("top")
    assert "Reloj:" in salida_top
    assert "PID NOMBRE USUARIO ESTADO" in salida_top

    assert "terminado" in consola.ejecutar_comando("kill 0").lower()
    assert procesos.estado_proceso(0) == "TERMINADO"

    assert "PID 1" in consola.ejecutar_comando("run web", "alice")
    assert "1 web alice NUEVO" in consola.ejecutar_comando("ps")
    assert "terminado" in consola.ejecutar_comando("kill 1").lower()


def test_comandos_de_recursos_free_df_whoami(usuarios_base):
    _preparar_usuarios(usuarios_base)
    archivos.fs_escribir("/data/f", "x", "admin")
    salida_df = consola.ejecutar_comando("df")
    assert "Bloques totales: 200" in salida_df
    assert "Bloques usados: 1" in salida_df
    assert "Bloques libres: 199" in salida_df

    pid = procesos.crear_proceso(
        "p", "u", [["MEM", 0], ["CPU", 1]], memoria_bytes=512, cuota_marcos=2
    )
    kernel.tick()
    salida_free = consola.ejecutar_comando("free")
    assert "Marcos totales: 16" in salida_free
    assert "Marcos usados: 1" in salida_free
    assert "Marcos libres: 15" in salida_free
    assert memoria.estado_memoria()["marcos_por_proceso"][pid] == 1

    assert consola.ejecutar_comando("whoami", "alice") == "alice"
    assert consola.ejecutar_comando("whoami") == "admin"


def test_la_consola_respeta_permisos(usuarios_base):
    _preparar_usuarios(usuarios_base)
    archivos.fs_escribir("/data/f", "x", "alice")
    archivos.fs_chmod("/data/f", "600", "alice")
    assert consola.ejecutar_comando("cat /data/f", "bob").startswith("Error:")
    assert consola.ejecutar_comando("cat /data/f", "admin") == "x"
    assert consola.ejecutar_comando("mkdir /nuevo", "alice").startswith("Error:")


def test_historial_y_directorio_actual_son_por_usuario(usuarios_base):
    _preparar_usuarios(usuarios_base)
    consola.ejecutar_comando("pwd", "admin")
    consola.ejecutar_comando("mkdir /data/admin", "admin")
    consola.ejecutar_comando("cd /data/admin", "admin")
    consola.ejecutar_comando("pwd", "alice")

    assert consola.directorio_actual("admin") == "/data/admin"
    assert consola.directorio_actual("alice") == "/"
    assert consola.historial("admin") == ["pwd", "mkdir /data/admin", "cd /data/admin"]
    assert consola.historial("alice") == ["pwd"]


def test_historial_registra_tambien_los_comandos_con_error():
    consola.ejecutar_comando("comando_inexistente")
    assert consola.historial("admin") == ["comando_inexistente"]


def test_ps_siempre_comienza_con_la_cabecera_obligatoria(cargar_escenario):
    _cargar_catalogo(cargar_escenario)
    assert consola.ejecutar_comando("ps").splitlines()[0] == "PID NOMBRE USUARIO ESTADO"
    consola.ejecutar_comando("run web")
    assert consola.ejecutar_comando("ps").splitlines()[0] == "PID NOMBRE USUARIO ESTADO"


def test_top_no_duplica_el_numero_de_procesos_activos(cargar_escenario):
    _cargar_catalogo(cargar_escenario)
    consola.ejecutar_comando("run web")
    consola.ejecutar_comando("run web")
    salida = consola.ejecutar_comando("top")
    assert "Procesos activos: 2" in salida


@pytest.mark.parametrize(
    "comando",
    [
        "kill",
        "kill 999",
        "run",
        "run nope",
        "top x",
        "tick",
        "tick 0",
        "tick -1",
        "tick abc",
        "ls -z",
        "foobar",
        "cd /nope",
        "cat /nope",
        "rm /noexiste",
        "chmod 999 /data",
    ],
)
def test_los_errores_de_consola_comienzan_por_Error(comando, usuarios_base):
    _preparar_usuarios(usuarios_base)
    archivos.fs_escribir("/data/f", "x", "admin")
    salida = consola.ejecutar_comando(comando)
    assert salida.startswith("Error:"), salida


def test_errores_de_comandos_incompletos_y_duplicados(usuarios_base):
    _preparar_usuarios(usuarios_base)
    archivos.fs_escribir("/data/f", "x", "admin")
    assert consola.ejecutar_comando("mkdir /data").startswith("Error:")
    assert consola.ejecutar_comando("touch /data").startswith("Error:")
    assert consola.ejecutar_comando("rm /data").startswith("Error:")
    assert consola.ejecutar_comando("ln -s /data/f /data/f").startswith("Error:")
