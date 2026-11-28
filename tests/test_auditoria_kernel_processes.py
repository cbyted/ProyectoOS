"""Auditoría de caja negra del kernel y la gestión de procesos."""
from __future__ import annotations

import threading

import pytest

from minidc import kernel, procesos
from minidc.errores import ErrorNoExiste


METRICAS_PLANIFICACION = {
    "espera_promedio",
    "respuesta_promedio",
    "retorno_promedio",
    "espera_maxima",
    "utilizacion_cpu",
    "cambios_contexto",
    "procesos_terminados",
}


def _entradas_unicas_por_pid():
    entradas = procesos.listar_procesos()
    return entradas, {entrada["pid"] for entrada in entradas}


def _esperar_terminacion(pids, limite=5000):
    for _ in range(limite):
        if all(procesos.estado_proceso(pid) == "TERMINADO" for pid in pids):
            return
        kernel.tick()
    pytest.fail(f"Los procesos no finalizaron dentro de {limite} ticks: {pids}")


def test_reloj_inicializa_avanza_y_ejecuta_ticks(sistema_limpio):
    assert kernel.reloj_actual() == 0
    kernel.tick()
    assert kernel.reloj_actual() == 1
    kernel.ejecutar_ticks(7)
    assert kernel.reloj_actual() == 8
    kernel.ejecutar_ticks(0)
    assert kernel.reloj_actual() == 8


def test_reinicio_elimina_procesos_y_reinicia_reloj(sistema_limpio):
    pid = procesos.crear_proceso("anterior", "u", [["CPU", 10]])
    kernel.ejecutar_ticks(2)
    kernel.iniciar_sistema(dict(sistema_limpio))
    assert kernel.reloj_actual() == 0
    assert procesos.listar_procesos() == []
    assert procesos.cola_listos() == []
    with pytest.raises(ErrorNoExiste):
        procesos.estado_proceso(pid)


def test_pids_unicos_y_listado_sin_duplicados(sistema_limpio):
    creados = [
        procesos.crear_proceso(f"p{i}", "u", [["CPU", 3]])
        for i in range(4)
    ]
    entradas, pids_listados = _entradas_unicas_por_pid()
    pids_en_entradas = [entrada["pid"] for entrada in entradas]

    assert len(set(creados)) == len(creados)
    assert set(creados) == pids_listados
    assert len(pids_en_entradas) == len(set(pids_en_entradas)), (
        "listar_procesos() devuelve más de una entrada para un mismo PID"
    )


def test_resumen_activos_coincide_con_pids_activos_observables(sistema_limpio):
    procesos.crear_proceso("activo", "u", [["CPU", 10]])
    entradas, _ = _entradas_unicas_por_pid()
    activos = {e["pid"] for e in entradas if e["estado"] != "TERMINADO"}
    resumen = kernel.resumen_sistema()
    assert resumen["procesos_activos"] == len(activos)


def test_crear_hilo_devuelve_identificador_publico(sistema_limpio):
    pid = procesos.crear_proceso("proceso", "u", [["CPU", 5]])
    tid = procesos.crear_hilo(pid, [["CPU", 2]])
    assert isinstance(tid, int)


def test_proceso_finaliza_y_metricas_contienen_requisitos(sistema_limpio):
    pids = [
        procesos.crear_proceso(f"p{i}", "u", [["CPU", 3]])
        for i in range(3)
    ]
    _esperar_terminacion(pids)
    assert all(procesos.estado_proceso(pid) == "TERMINADO" for pid in pids)

    metricas = procesos.metricas_planificacion()
    assert METRICAS_PLANIFICACION <= set(metricas)
    assert metricas["procesos_terminados"] == len(pids)
    assert metricas["espera_promedio"] >= 0
    assert metricas["respuesta_promedio"] >= 0
    assert metricas["retorno_promedio"] >= 0
    assert 0 <= metricas["utilizacion_cpu"] <= 1


def test_llegadas_se_producen_en_los_ticks_configurados(crear_escenario):
    crear_escenario(
        usuarios=["u"],
        catalogo={"web": {"memoria_bytes": 512, "cuota_marcos": 2, "programa": [["CPU", 5]]}},
        llegadas=[{"tick": 2, "programa": "web", "usuario": "u"}],
    )
    assert procesos.listar_procesos() == []
    kernel.ejecutar_ticks(1)
    assert procesos.listar_procesos() == []
    kernel.tick()
    entradas, _ = _entradas_unicas_por_pid()
    assert any(e["nombre"] == "web" for e in entradas)


def test_procesos_simulados_no_crean_hilos_del_anfitrion(sistema_limpio):
    antes = {h.ident for h in threading.enumerate()}
    pids = [procesos.crear_proceso(f"p{i}", "u", [["CPU", 4]]) for i in range(4)]
    kernel.ejecutar_ticks(3)
    despues = {h.ident for h in threading.enumerate()}
    assert despues - antes == set()
    assert all(procesos.estado_proceso(pid) in {"NUEVO", "LISTO", "EJECUTANDO", "TERMINADO"} for pid in pids)


def test_RP1_respuesta_promedio_de_carga_web(crear_escenario):
    crear_escenario(
        config={"num_cpus": 2, "marcos_fisicos": 64, "tam_pagina": 256,
                "bloques_disco": 200, "tam_bloque": 512, "cache_bloques": 8},
        usuarios=["u"],
        catalogo={"web": {"memoria_bytes": 512, "cuota_marcos": 2, "prioridad": 1, "programa": [["CPU", 8]]}},
        llegadas=[{"tick": 0, "programa": "web", "usuario": "u"} for _ in range(10)],
    )
    pids = {e["pid"] for e in procesos.listar_procesos() if e["nombre"] == "web"}
    _esperar_terminacion(pids)
    assert procesos.metricas_planificacion()["respuesta_promedio"] <= 10


def test_RP2_espera_consecutiva_no_supera_150_ticks(sistema_limpio):
    kernel.iniciar_sistema({
        "num_cpus": 1, "marcos_fisicos": 256, "tam_pagina": 256,
        "bloques_disco": 200, "tam_bloque": 512, "cache_bloques": 8,
    })
    pids = [
        procesos.crear_proceso(f"carga{i}", "u", [["CPU", 10]], prioridad=i % 3)
        for i in range(50)
    ]
    espera_actual = {pid: 0 for pid in pids}
    espera_maxima = {pid: 0 for pid in pids}
    for _ in range(5000):
        kernel.tick()
        terminados = 0
        for pid in pids:
            estado = procesos.estado_proceso(pid)
            if estado == "LISTO":
                espera_actual[pid] += 1
                espera_maxima[pid] = max(espera_maxima[pid], espera_actual[pid])
            else:
                espera_actual[pid] = 0
            terminados += estado == "TERMINADO"
        if terminados == len(pids):
            break
    assert max(espera_maxima.values(), default=0) <= 150


def test_RP3_utilizacion_cpu_con_carga_suficiente(sistema_limpio):
    kernel.iniciar_sistema({
        "num_cpus": 2, "marcos_fisicos": 64, "tam_pagina": 256,
        "bloques_disco": 200, "tam_bloque": 512, "cache_bloques": 8,
    })
    pids = [
        procesos.crear_proceso(f"cpu{i}", "u", [["CPU", 20]])
        for i in range(10)
    ]
    _esperar_terminacion(pids)
    assert procesos.metricas_planificacion()["utilizacion_cpu"] >= 0.85
