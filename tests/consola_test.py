import json

import pytest

from minidc import consola, kernel, procesos
from minidc.errores import ErrorPermiso, ErrorSistema


CONFIG = {
    "num_cpus": 1,
    "marcos_fisicos": 16,
    "tam_pagina": 256,
    "bloques_disco": 200,
    "tam_bloque": 512,
    "cache_bloques": 8,
}

@pytest.fixture(autouse=True)
def sistema_inicializado():
    """Reinicia kernel, procesos y sesiones antes de cada prueba."""
    kernel.iniciar_sistema(CONFIG)
    yield
    kernel.iniciar_sistema(CONFIG)


def cargar_catalogo(tmp_path, catalogo=None):
    """Carga un escenario mínimo con los programas indicados."""
    escenario = {
        "config": CONFIG,
        "catalogo": catalogo or {
            "web": {
                "memoria_bytes": 1024,
                "cuota_marcos": 3,
                "prioridad": 1,
                "programa": [["CPU", 2]],
            },
            "analitica": {
                "programa": [["CPU", 5]],
            },
        },
        "llegadas": [],
    }
    ruta = tmp_path / "escenario.json"
    ruta.write_text(json.dumps(escenario), encoding="utf-8")
    kernel.cargar_escenario(str(ruta))


def test_run_crea_proceso_desde_catalogo(tmp_path):
    """run utiliza las instrucciones y parámetros del escenario cargado."""
    cargar_catalogo(tmp_path)

    resultado = consola.ejecutar_comando("run web", "cliente_a")
    lista = procesos.listar_procesos()

    assert resultado == "Proceso 'web' iniciado con PID 0."
    assert len(lista) == 1
    assert lista[0]["nombre"] == "web"
    assert lista[0]["usuario"] == "cliente_a"
    assert lista[0]["estado"] == "NUEVO"


def test_run_requiere_un_nombre():
    """run exige exactamente un nombre de programa."""
    resultado_sin_nombre = consola.ejecutar_comando("run")
    resultado_dos_nombres = consola.ejecutar_comando("run web backup")

    assert resultado_sin_nombre.startswith("Error:")
    assert resultado_dos_nombres.startswith("Error:")


def test_run_respeta_nombre_entre_comillas(tmp_path):
    """shlex permite utilizar nombres de catálogo que contienen espacios."""
    cargar_catalogo(
        tmp_path,
        {"web service": {"programa": [["CPU", 2]]}},
    )

    resultado = consola.ejecutar_comando('run "web service"')

    assert resultado == "Proceso 'web service' iniciado con PID 0."
    assert procesos.listar_procesos()[0]["nombre"] == "web service"


def test_kill_termina_proceso_con_pid_cero():
    """PID 0 es válido porque la implementación actual comienza en cero."""
    pid = procesos.crear_proceso("web", "cliente_a", [("CPU", 2)])

    resultado = consola.ejecutar_comando(f"kill {pid}")

    assert pid == 0
    assert resultado == "Proceso 0 terminado."
    assert procesos.estado_proceso(pid) == "TERMINADO"


def test_kill_requiere_un_pid():
    """kill exige exactamente un argumento."""
    assert consola.ejecutar_comando("kill").startswith("Error:")
    assert consola.ejecutar_comando("kill 1 2").startswith("Error:")


def test_tick_avanza_el_reloj():
    """tick N delega el avance del tiempo al kernel."""
    resultado = consola.ejecutar_comando("tick 4")

    assert resultado == "Reloj actual: 4"
    assert kernel.reloj_actual() == 4


def test_tick_rechaza_cantidades_invalidas():
    """tick requiere un entero positivo."""
    for comando in ("tick", "tick 0", "tick -2", "tick abc", "tick 1 2"):
        resultado = consola.ejecutar_comando(comando)
        assert resultado.startswith("Error:"), comando


def test_top_muestra_resumen_del_kernel_y_procesos():
    """top presenta el resumen general y termina con el listado de procesos."""
    procesos.crear_proceso("web", "cliente_a", [("CPU", 2)])
    kernel.ejecutar_ticks(1)

    resultado = consola.ejecutar_comando("top")

    assert "Reloj: 1" in resultado
    assert "Procesos activos: 1" in resultado
    assert "Marcos libres: 16" in resultado
    assert "Bloques libres: 200" in resultado
    assert "PID NOMBRE USUARIO ESTADO" in resultado
    assert "web cliente_a" in resultado


def test_top_rechaza_argumentos():
    """top se ejecuta sin argumentos."""
    resultado = consola.ejecutar_comando("top extra")

    assert resultado.startswith("Error:")
    assert "Uso: top" in resultado


def test_consola_convierte_excepciones_del_sistema_en_texto(monkeypatch):
    """Las excepciones derivadas de ErrorSistema se presentan como Error:."""
    def lanzar_error():
        raise ErrorPermiso("operación no permitida")

    monkeypatch.setattr(procesos, "listar_procesos", lanzar_error)
    resultado = consola.ejecutar_comando("ps")

    assert resultado == "Error: operación no permitida"
    assert issubclass(ErrorPermiso, ErrorSistema)


def test_historial_separa_comandos_por_usuario():
    """Cada usuario conserva su historial de forma independiente."""
    consola.ejecutar_comando("ps", "admin")
    consola.ejecutar_comando("tick 2", "cliente_a")

    assert consola.historial("admin") == ["ps"]
    assert consola.historial("cliente_a") == ["tick 2"]


def test_reiniciar_kernel_limpia_sesiones():
    """La inicialización del kernel también reinicia el estado de consola."""
    consola.ejecutar_comando("ps", "cliente_a")
    assert consola.historial("cliente_a") == ["ps"]

    kernel.iniciar_sistema(CONFIG)

    assert consola.historial("cliente_a") == []
    assert consola.directorio_actual("cliente_a") == "/"
