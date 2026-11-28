"""Auditoría de caja negra de los comandos públicos de consola."""
from __future__ import annotations

from minidc import archivos, consola, procesos


def test_ps_cabecera_y_comandos_de_recursos(sistema_limpio):
    salida_ps = consola.ejecutar_comando("ps")
    assert salida_ps.splitlines()[0] == "PID NOMBRE USUARIO ESTADO"
    assert not consola.ejecutar_comando("free").startswith("Error:")
    assert not consola.ejecutar_comando("df").startswith("Error:")
    assert consola.ejecutar_comando("whoami") == "admin"


def test_comandos_filesystem_producen_efectos_observables(sistema_limpio):
    assert not consola.ejecutar_comando("mkdir /datos").startswith("Error:")
    assert not consola.ejecutar_comando("touch /datos/nota.txt").startswith("Error:")
    assert not consola.ejecutar_comando('echo "hola mundo" > /datos/nota.txt').startswith("Error:")
    assert archivos.fs_leer("/datos/nota.txt", "admin") == "hola mundo"
    assert "nota.txt" in consola.ejecutar_comando("ls /datos")
    assert not consola.ejecutar_comando("chmod 600 /datos/nota.txt").startswith("Error:")
    assert archivos.fs_info("/datos/nota.txt")["modo"] == "600"
    assert not consola.ejecutar_comando("rm /datos/nota.txt").startswith("Error:")


def test_cd_pwd_y_historial_son_coherentes(sistema_limpio):
    consola.ejecutar_comando("mkdir /trabajo")
    assert not consola.ejecutar_comando("cd /trabajo").startswith("Error:")
    assert consola.directorio_actual() == "/trabajo"
    assert consola.ejecutar_comando("pwd") == "/trabajo"
    assert consola.historial()[:3] == ["mkdir /trabajo", "cd /trabajo", "pwd"]


def test_comandos_de_procesos_actuan_sobre_procesos(sistema_limpio):
    pid = procesos.crear_proceso("desde-api", "admin", [["CPU", 5]])
    salida_ps = consola.ejecutar_comando("ps")
    assert salida_ps.splitlines()[0] == "PID NOMBRE USUARIO ESTADO"
    assert any(line.split()[0] == str(pid) for line in salida_ps.splitlines()[1:])
    assert not consola.ejecutar_comando("top").startswith("Error:")
    salida_kill = consola.ejecutar_comando(f"kill {pid}")
    assert not salida_kill.startswith("Error:")
    assert procesos.estado_proceso(pid) == "TERMINADO"


def test_los_errores_de_consola_comienzan_por_prefijo_documentado(sistema_limpio):
    for comando in ("comando_inexistente", "kill", "run", "cd /no-existe", "tick -1"):
        salida = consola.ejecutar_comando(comando)
        assert salida.startswith("Error:"), (comando, salida)
