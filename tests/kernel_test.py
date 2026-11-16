import json

import pytest

from minidc import kernel, procesos


CONFIG = {
    "num_cpus": 1,
    "marcos_fisicos": 16,
    "tam_pagina": 256,
    "bloques_disco": 200,
    "tam_bloque": 512,
    "cache_bloques": 8,
}


def test_iniciar_sistema_reinicia_reloj_procesos_y_recursos():
    kernel.iniciar_sistema(CONFIG)
    procesos.crear_proceso("web", "cliente_a", [("CPU", 1)])
    kernel.tick()
    assert kernel.resumen_sistema()["procesos_activos"] == 0

    kernel.iniciar_sistema(CONFIG)

    assert kernel.reloj_actual() == 0
    assert kernel.resumen_sistema() == {
        "reloj": 0,
        "procesos_activos": 0,
        "marcos_libres": 16,
        "bloques_libres": 200,
    }
    assert procesos.listar_procesos() == []


def test_cargar_escenario_programa_llegada_y_ejecuta_ticks(tmp_path):
    escenario = {
        "config": CONFIG,
        "catalogo": {
            "web": {
                "memoria_bytes": 1024,
                "cuota_marcos": 3,
                "prioridad": 1,
                "programa": [["CPU", 2]],
            }
        },
        "llegadas": [
            {"tick": 0, "programa": "web", "usuario": "cliente_a"},
        ],
    }
    ruta = tmp_path / "escenario.json"
    ruta.write_text(json.dumps(escenario), encoding="utf-8")

    kernel.cargar_escenario(str(ruta))
    kernel.tick()

    proceso = procesos.listar_procesos()[0]
    assert proceso["nombre"] == "web"
    assert proceso["usuario"] == "cliente_a"
    assert proceso["estado"] == "EJECUTANDO"
    assert kernel.resumen_sistema()["procesos_activos"] == 1

    kernel.ejecutar_ticks(1)

    assert procesos.estado_proceso(proceso["pid"]) == "TERMINADO"
    assert kernel.apagar_sistema() == {
        "reloj": 2,
        "procesos_activos": 0,
        "marcos_libres": 16,
        "bloques_libres": 200,
    }


def test_iniciar_sistema_valida_configuracion_sin_borrar_estado():
    kernel.iniciar_sistema(CONFIG)
    kernel.ejecutar_ticks(2)

    with pytest.raises(ValueError):
        kernel.iniciar_sistema({"num_cpus": 0})

    assert kernel.reloj_actual() == 2


def test_ejecutar_ticks_rechaza_cantidades_invalidas():
    kernel.iniciar_sistema(CONFIG)

    with pytest.raises(ValueError):
        kernel.ejecutar_ticks(-1)