"""Pruebas de caja negra para administración de disco y caché."""

from __future__ import annotations

import pytest

from minidc import disco, kernel, procesos


def _reiniciar(cache=0, bloques=100):
    kernel.iniciar_sistema(
        {
            "num_cpus": 1,
            "marcos_fisicos": 8,
            "tam_pagina": 256,
            "bloques_disco": bloques,
            "tam_bloque": 512,
            "cache_bloques": cache,
        }
    )


def _proceso():
    return procesos.crear_proceso("p", "u", [["CPU", 100]], memoria_bytes=256, cuota_marcos=1)


def test_las_solicitudes_se_encolan_y_la_cola_refleja_el_orden_de_atención():
    _reiniciar()
    pid = _proceso()
    for bloque in [50, 10, 90, 20]:
        disco.encolar_solicitud_disco(pid, bloque, "L")
    assert disco.cola_disco() == [10, 20, 50, 90]


def test_procesar_disco_atiende_en_el_orden_anunciado_por_la_cola():
    _reiniciar()
    pid = _proceso()
    for bloque in [50, 10, 90, 20]:
        disco.encolar_solicitud_disco(pid, bloque, "L")
    orden_anunciado = list(disco.cola_disco())
    atendidos = disco.procesar_disco()
    assert atendidos == orden_anunciado
    assert disco.cola_disco() == []


def test_posicion_y_desplazamiento_del_cabezal_son_coherentes():
    _reiniciar()
    pid = _proceso()
    for bloque in [50, 10, 90, 20]:
        disco.encolar_solicitud_disco(pid, bloque, "L")
    disco.procesar_disco()
    metricas = disco.metricas_disco()
    assert metricas["solicitudes_atendidas"] == 4
    assert metricas["posicion_cabezal"] == 90
    assert metricas["desplazamiento_total"] == 90


def test_RD1_desplazamiento_menor_o_igual_al_70_por_ciento_del_fifo():
    _reiniciar(cache=0)
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
    assert metricas["desplazamiento_total"] == 90
    assert metricas["desplazamiento_total"] <= fifo * 0.70
    assert metricas["espera_maxima"] <= 200


def test_la_cache_registra_aciertos_fallos_y_respeta_su_capacidad():
    _reiniciar(cache=2)
    pid = _proceso()
    for bloque in [10, 20, 30, 40]:
        disco.encolar_solicitud_disco(pid, bloque, "L")
    disco.procesar_disco()
    cache_inicial = disco.info_cache()
    assert cache_inicial["capacidad_bloques"] == 2
    assert cache_inicial["fallos"] == 4
    assert cache_inicial["aciertos"] == 0

    for bloque in [40, 30, 20]:
        disco.encolar_solicitud_disco(pid, bloque, "L")
    disco.procesar_disco()
    cache_final = disco.info_cache()
    assert cache_final["capacidad_bloques"] == 2
    assert cache_final["aciertos"] >= 2
    assert cache_final["fallos"] >= 5


def test_un_proceso_queda_bloqueado_hasta_que_termina_su_es():
    _reiniciar()
    pid = procesos.crear_proceso(
        "p", "u", [["ES", 50], ["CPU", 1]], memoria_bytes=256, cuota_marcos=1
    )
    for _ in range(6):
        kernel.tick()
        assert procesos.estado_proceso(pid) == "BLOQUEADO"
    kernel.tick()
    assert procesos.estado_proceso(pid) == "TERMINADO"
    assert disco.cola_disco() == []
    assert disco.metricas_disco()["solicitudes_atendidas"] == 1


@pytest.mark.parametrize(
    ("bloque", "ticks_servicio"),
    [(5, 1), (9, 1), (10, 2), (11, 2), (25, 3), (50, 6)],
)
def test_tiempo_de_servicio_respeta_la_formula(bloque, ticks_servicio):
    _reiniciar()
    pid = procesos.crear_proceso(
        "p", "u", [["ES", bloque], ["CPU", 1]], memoria_bytes=256, cuota_marcos=1
    )
    ticks_bloqueado = 0
    for _ in range(30):
        kernel.tick()
        if procesos.estado_proceso(pid) == "BLOQUEADO":
            ticks_bloqueado += 1
        if procesos.estado_proceso(pid) == "TERMINADO":
            break
    assert ticks_bloqueado == 1 + abs(bloque) // 10


def test_procesar_disco_sin_solicitudes_devuelve_lista_vacia_y_no_cambia_el_reloj():
    _reiniciar()
    reloj_antes = kernel.reloj_actual()
    assert disco.procesar_disco() == []
    assert kernel.reloj_actual() == reloj_antes


def test_metricas_e_info_de_cache_incluyen_las_claves_documentadas():
    _reiniciar(cache=4)
    metricas = disco.metricas_disco()
    assert set(metricas) == {
        "solicitudes_atendidas",
        "desplazamiento_total",
        "posicion_cabezal",
        "espera_maxima",
    }
    cache = disco.info_cache()
    assert set(cache) == {"capacidad_bloques", "aciertos", "fallos", "tasa_aciertos"}
    assert cache["capacidad_bloques"] == 4


def test_politica_de_disco_es_informada():
    _reiniciar()
    politica = disco.politica_disco()
    assert isinstance(politica, str)
    assert politica.strip() != ""


def test_solicitud_con_operacion_invalida_lanza_error():
    _reiniciar()
    pid = _proceso()
    with pytest.raises(ValueError):
        disco.encolar_solicitud_disco(pid, 10, "LECTURA")


@pytest.mark.parametrize("bloque", [-1, 100, 999])
def test_solicitud_con_bloque_fuera_de_rango_lanza_error(bloque):
    _reiniciar(bloques=100)
    pid = _proceso()
    with pytest.raises(ValueError):
        disco.encolar_solicitud_disco(pid, bloque, "L")


def test_solicitud_con_bloque_no_entero_lanza_error():
    _reiniciar()
    pid = _proceso()
    with pytest.raises(TypeError):
        disco.encolar_solicitud_disco(pid, 1.5, "L")
