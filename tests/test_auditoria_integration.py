"""Escenarios de integración evaluados desde las interfaces públicas."""
from __future__ import annotations

import pytest

from minidc import archivos, disco, kernel, memoria, procesos


def _proceso_por_nombre(nombre):
    coincidencias = [e for e in procesos.listar_procesos() if e["nombre"] == nombre]
    assert coincidencias, f"No se encontró el proceso {nombre!r}"
    return coincidencias[0]["pid"]


def _esperar_estado(pid, estado, limite=1000):
    for _ in range(limite):
        if procesos.estado_proceso(pid) == estado:
            return
        kernel.tick()
    pytest.fail(f"PID {pid} no alcanzó {estado} en {limite} ticks")


def test_servicio_web_cpu_memoria_es_y_finalizacion(crear_escenario):
    crear_escenario(
        config={
            "num_cpus": 2, "marcos_fisicos": 8, "tam_pagina": 256,
            "bloques_disco": 50, "tam_bloque": 64, "cache_bloques": 4,
        },
        usuarios=["webuser"],
        catalogo={"servicio": {
            "memoria_bytes": 512, "cuota_marcos": 2,
            "programa": [["CPU", 2], ["MEM", 0], ["ES", 5], ["CPU", 1]],
        }},
        llegadas=[{"tick": 1, "programa": "servicio", "usuario": "webuser"}],
    )
    kernel.tick()
    pid = _proceso_por_nombre("servicio")
    estados = set()
    for _ in range(100):
        estados.add(procesos.estado_proceso(pid))
        if procesos.estado_proceso(pid) == "TERMINADO":
            break
        kernel.tick()
    assert procesos.estado_proceso(pid) == "TERMINADO"
    assert "BLOQUEADO" in estados
    assert pid not in memoria.estado_memoria()["marcos_por_proceso"]
    assert disco.cola_disco() == []
    assert disco.metricas_disco()["solicitudes_atendidas"] == 1
    assert memoria.metricas_memoria()["accesos"] >= 1


def test_terminacion_libera_memoria_y_cancela_io_pendiente(sistema_limpio):
    kernel.iniciar_sistema({
        "num_cpus": 1, "marcos_fisicos": 8, "tam_pagina": 256,
        "bloques_disco": 100, "tam_bloque": 512, "cache_bloques": 4,
    })
    pid = procesos.crear_proceso(
        "cancelar-io", "u", [["MEM", 0], ["ES", 50], ["CPU", 10]],
        memoria_bytes=512, cuota_marcos=2,
    )
    for _ in range(50):
        if disco.cola_disco():
            break
        kernel.tick()
    assert procesos.estado_proceso(pid) == "BLOQUEADO"
    assert disco.cola_disco()
    procesos.terminar_proceso(pid)
    assert procesos.estado_proceso(pid) == "TERMINADO"
    assert pid not in memoria.estado_memoria()["marcos_por_proceso"]
    assert memoria.estado_memoria()["marcos_libres"] == 8
    assert disco.cola_disco() == []


def test_recurso_compartido_con_mutex(api_sincronizacion_disponible, sistema_limpio):
    sync = api_sincronizacion_disponible
    p0 = procesos.crear_proceso("db0", "u", [["CPU", 10]])
    p1 = procesos.crear_proceso("db1", "u", [["CPU", 10]])
    sync.crear_mutex("db")
    sync.mutex_lock("db", p0)
    sync.mutex_lock("db", p1)
    assert procesos.estado_proceso(p1) == "BLOQUEADO"
    sync.mutex_unlock("db", p0)
    assert procesos.estado_proceso(p1) in {"LISTO", "EJECUTANDO"}


def test_terminacion_libera_mutex_y_recurso_de_semaforo(api_sincronizacion_disponible, sistema_limpio):
    sync = api_sincronizacion_disponible
    propietario = procesos.crear_proceso("propietario", "u", [["CPU", 10]])
    esperando = procesos.crear_proceso("esperando", "u", [["CPU", 10]])
    sync.crear_mutex("m")
    sync.crear_semaforo("s", 1)
    sync.mutex_lock("m", propietario)
    sync.semaforo_wait("s", propietario)
    procesos.terminar_proceso(propietario)
    # La especificación exige liberar los recursos al finalizar el proceso.
    sync.mutex_lock("m", esperando)
    assert procesos.estado_proceso(esperando) != "BLOQUEADO"
    sync.semaforo_wait("s", esperando)
    assert procesos.estado_proceso(esperando) != "BLOQUEADO"
    estado_sem = sync.estado_semaforo("s")
    assert estado_sem["valor"] >= 0
