"""Pruebas de integración de caja negra entre subsistemas."""

from __future__ import annotations

import pytest

from minidc import archivos, disco, kernel, memoria, procesos, sincronizacion


def _ejecutar_hasta(condicion, limite=1000):
    for _ in range(limite):
        kernel.tick()
        if condicion():
            return
    pytest.fail(f"La condición no se cumplió en {limite} ticks")


def test_escenario_web_cpu_memoria_es_y_liberacion(cargar_escenario):
    cargar_escenario(
        config={
            "num_cpus": 2,
            "marcos_fisicos": 8,
            "tam_pagina": 256,
            "bloques_disco": 50,
            "tam_bloque": 64,
            "cache_bloques": 4,
        },
        usuarios=["u"],
        catalogo={
            "web": {
                "memoria_bytes": 512,
                "cuota_marcos": 2,
                "prioridad": 1,
                "programa": [["CPU", 2], ["MEM", 0], ["ES", 5], ["CPU", 1]],
            }
        },
        llegadas=[{"tick": 1, "programa": "web", "usuario": "u"}],
    )
    pid = 0
    estados = set()
    for _ in range(100):
        kernel.tick()
        estados.add(procesos.estado_proceso(pid))
        if procesos.estado_proceso(pid) == "TERMINADO":
            break

    assert procesos.estado_proceso(pid) == "TERMINADO"
    assert "BLOQUEADO" in estados
    assert pid not in memoria.estado_memoria()["marcos_por_proceso"]
    assert disco.cola_disco() == []
    assert disco.metricas_disco()["solicitudes_atendidas"] == 1
    assert memoria.metricas_memoria()["accesos"] >= 1
    assert memoria.metricas_memoria()["fallos_pagina"] >= 1
    assert kernel.resumen_sistema()["procesos_activos"] == 0
    assert procesos.metricas_planificacion()["procesos_terminados"] == 1


def test_escenario_analitica_paginas_reemplazos_y_cpu():
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
    programa = [["CPU", 5]]
    for pagina in range(4):
        for _ in range(10):
            programa.append(["MEM", pagina * 256])
    programa.append(["CPU", 5])
    pid = procesos.crear_proceso(
        "analitica", "u", programa, memoria_bytes=4096, cuota_marcos=2, prioridad=0
    )
    _ejecutar_hasta(lambda: procesos.estado_proceso(pid) == "TERMINADO", limite=1000)

    metricas_mem = memoria.metricas_memoria()
    assert metricas_mem["accesos"] == 40
    assert metricas_mem["reemplazos"] > 0
    assert memoria.estado_memoria()["marcos_libres"] == 8
    assert pid not in memoria.estado_memoria()["marcos_por_proceso"]
    assert procesos.metricas_planificacion()["procesos_terminados"] == 1


def test_escenario_respaldo_competencia_por_disco():
    kernel.iniciar_sistema(
        {
            "num_cpus": 1,
            "marcos_fisicos": 8,
            "tam_pagina": 256,
            "bloques_disco": 100,
            "tam_bloque": 512,
            "cache_bloques": 0,
        }
    )
    bloques = [50, 10, 90]
    pids = [
        procesos.crear_proceso(
            f"respaldo{i}", "u", [["ES", bloque], ["CPU", 1]], memoria_bytes=256, cuota_marcos=1
        )
        for i, bloque in enumerate(bloques)
    ]
    _ejecutar_hasta(lambda: all(procesos.estado_proceso(pid) == "TERMINADO" for pid in pids))
    assert all(procesos.estado_proceso(pid) == "TERMINADO" for pid in pids)
    assert disco.cola_disco() == []

    metricas = disco.metricas_disco()
    posicion = 0
    fifo = 0
    for bloque in bloques:
        fifo += abs(bloque - posicion)
        posicion = bloque
    assert metricas["solicitudes_atendidas"] == 3
    assert metricas["desplazamiento_total"] <= fifo * 0.70
    assert metricas["espera_maxima"] <= 200


def test_escenario_base_de_datos_compartida_requiere_sincronizacion():
    p0 = procesos.crear_proceso("db0", "u", [["CPU", 10]])
    p1 = procesos.crear_proceso("db1", "u", [["CPU", 10]])
    sincronizacion.crear_mutex("db")
    sincronizacion.mutex_lock("db", p0)
    sincronizacion.mutex_lock("db", p1)
    assert procesos.estado_proceso(p1) == "BLOQUEADO"
    sincronizacion.mutex_unlock("db", p0)
    assert procesos.estado_proceso(p1) in {"LISTO", "EJECUTANDO"}


def test_terminacion_libera_memoria_y_cancela_es_pendiente():
    kernel.iniciar_sistema(
        {
            "num_cpus": 1,
            "marcos_fisicos": 8,
            "tam_pagina": 256,
            "bloques_disco": 100,
            "tam_bloque": 512,
            "cache_bloques": 4,
        }
    )
    pid = procesos.crear_proceso(
        "p", "u", [["MEM", 0], ["ES", 50], ["CPU", 10]], memoria_bytes=512, cuota_marcos=2
    )
    _ejecutar_hasta(lambda: bool(disco.cola_disco()), limite=50)
    assert procesos.estado_proceso(pid) == "BLOQUEADO"
    assert memoria.estado_memoria()["marcos_por_proceso"][pid] >= 1
    assert disco.cola_disco() != []

    procesos.terminar_proceso(pid)

    assert procesos.estado_proceso(pid) == "TERMINADO"
    assert pid not in memoria.estado_memoria()["marcos_por_proceso"]
    assert memoria.estado_memoria()["marcos_libres"] == 8
    assert disco.cola_disco() == []


def test_no_quedan_recursos_ocupados_sin_proceso_tras_una_ejecucion():
    pids = [
        procesos.crear_proceso(f"p{i}", "u", [["CPU", 3], ["MEM", 0]], memoria_bytes=512, cuota_marcos=2)
        for i in range(3)
    ]
    _ejecutar_hasta(lambda: all(procesos.estado_proceso(pid) == "TERMINADO" for pid in pids))
    assert kernel.resumen_sistema()["procesos_activos"] == 0
    assert memoria.estado_memoria()["marcos_libres"] == 16
    assert memoria.estado_memoria()["marcos_por_proceso"] == {}
    assert disco.cola_disco() == []
    estado_fs = archivos.fs_estado_disco()
    usados = estado_fs["bloques_totales"] - estado_fs["bloques_libres"]
    assert usados + estado_fs["bloques_libres"] == estado_fs["bloques_totales"]
