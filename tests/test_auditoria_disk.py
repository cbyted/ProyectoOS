"""Auditoría de disco y caché sin imponer una política de planificación."""
from __future__ import annotations

import pytest

from minidc import disco, kernel, procesos


def _reset(cache=0, bloques=100):
    kernel.iniciar_sistema({
        "num_cpus": 1, "marcos_fisicos": 8, "tam_pagina": 256,
        "bloques_disco": bloques, "tam_bloque": 512, "cache_bloques": cache,
    })


def _proceso():
    return procesos.crear_proceso("io", "u", [["CPU", 100]], memoria_bytes=256, cuota_marcos=1)


def test_cola_y_servicio_conservan_todas_las_solicitudes(sistema_limpio):
    _reset()
    pid = _proceso()
    solicitudes = [50, 10, 90, 20, 10]
    for bloque in solicitudes:
        disco.encolar_solicitud_disco(pid, bloque, "L")

    cola_anunciada = list(disco.cola_disco())
    assert sorted(cola_anunciada) == sorted(solicitudes)
    atendidos = disco.procesar_disco()
    assert atendidos == cola_anunciada
    assert sorted(atendidos) == sorted(solicitudes)
    assert disco.cola_disco() == []


def test_cabezal_y_desplazamiento_coinciden_con_el_orden_real(sistema_limpio):
    _reset()
    pid = _proceso()
    for bloque in [50, 10, 90, 20]:
        disco.encolar_solicitud_disco(pid, bloque, "L")
    atendidos = disco.procesar_disco()

    posicion = 0
    desplazamiento_calculado = 0
    for bloque in atendidos:
        desplazamiento_calculado += abs(bloque - posicion)
        posicion = bloque

    metricas = disco.metricas_disco()
    assert metricas["solicitudes_atendidas"] == len(atendidos)
    assert metricas["posicion_cabezal"] == posicion
    assert metricas["desplazamiento_total"] == desplazamiento_calculado


def test_RD1_reduccion_de_desplazamiento_frente_a_fifo(sistema_limpio):
    _reset(cache=0)
    pid = _proceso()
    llegada = [90, 10, 80, 20, 70, 30, 60, 40, 50]
    for bloque in llegada:
        disco.encolar_solicitud_disco(pid, bloque, "L")
    disco.procesar_disco()

    posicion = 0
    fifo = 0
    for bloque in llegada:
        fifo += abs(bloque - posicion)
        posicion = bloque
    metricas = disco.metricas_disco()
    assert metricas["desplazamiento_total"] <= fifo * 0.70
    assert metricas["espera_maxima"] <= 200


def test_cache_marca_fallo_y_acierto_sin_asumir_orden_de_reemplazo(sistema_limpio):
    _reset(cache=2)
    pid = _proceso()
    disco.encolar_solicitud_disco(pid, 10, "L")
    disco.procesar_disco()
    tras_fallo = disco.info_cache()
    assert tras_fallo["fallos"] >= 1

    disco.encolar_solicitud_disco(pid, 10, "L")
    disco.procesar_disco()
    tras_acierto = disco.info_cache()
    assert tras_acierto["aciertos"] >= 1
    assert tras_acierto["capacidad_bloques"] == 2


def test_una_solicitud_de_es_bloquea_y_luego_reanuda_el_proceso(sistema_limpio):
    _reset()
    pid = procesos.crear_proceso("io", "u", [["ES", 50], ["CPU", 1]], memoria_bytes=256, cuota_marcos=1)
    for _ in range(6):
        kernel.tick()
        assert procesos.estado_proceso(pid) == "BLOQUEADO"
    kernel.tick()
    assert procesos.estado_proceso(pid) == "TERMINADO"
    assert disco.cola_disco() == []
    assert disco.metricas_disco()["solicitudes_atendidas"] == 1


@pytest.mark.parametrize(("bloque", "ticks_servicio"), [(5, 1), (10, 2), (25, 3), (50, 6)])
def test_formula_de_tiempo_de_servicio(bloque, ticks_servicio, sistema_limpio):
    _reset()
    pid = procesos.crear_proceso("io", "u", [["ES", bloque], ["CPU", 1]], memoria_bytes=256, cuota_marcos=1)
    bloqueado = 0
    for _ in range(30):
        kernel.tick()
        bloqueado += procesos.estado_proceso(pid) == "BLOQUEADO"
        if procesos.estado_proceso(pid) == "TERMINADO":
            break
    assert bloqueado == ticks_servicio


def test_politica_y_metricas_publicas_del_disco(sistema_limpio):
    assert isinstance(disco.politica_disco(), str) and disco.politica_disco().strip()
    metricas = disco.metricas_disco()
    assert {"solicitudes_atendidas", "desplazamiento_total", "posicion_cabezal", "espera_maxima"} <= set(metricas)
    cache = disco.info_cache()
    assert {"capacidad_bloques", "aciertos", "fallos", "tasa_aciertos"} <= set(cache)
