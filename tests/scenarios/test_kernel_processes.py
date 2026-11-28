"""Pruebas de caja negra para kernel, tiempo, procesos y planificación."""

from __future__ import annotations

import threading

import pytest

from minidc import archivos, consola, disco, kernel, memoria, procesos
from minidc.errores import ErrorNoExiste


def _todos_terminados(pids):
    return all(procesos.estado_proceso(pid) == "TERMINADO" for pid in pids)


def _ejecutar_hasta_terminar(pids, limite=5000):
    for _ in range(limite):
        kernel.tick()
        if _todos_terminados(pids):
            return
    pytest.fail(f"Los procesos {pids} no terminaron dentro de {limite} ticks")


# ---------------------------------------------------------------------------
# Kernel y modelo de tiempo
# ---------------------------------------------------------------------------


def test_iniciar_sistema_inicializa_todos_los_subsistemas():
    assert kernel.reloj_actual() == 0
    assert procesos.listar_procesos() == []
    assert procesos.cola_listos() == []

    resumen = kernel.resumen_sistema()
    assert set(resumen) == {"reloj", "procesos_activos", "marcos_libres", "bloques_libres"}
    assert resumen["reloj"] == 0
    assert resumen["procesos_activos"] == 0
    assert resumen["marcos_libres"] == 16
    assert resumen["bloques_libres"] == 200

    estado_mem = memoria.estado_memoria()
    assert estado_mem["marcos_totales"] == 16
    assert estado_mem["marcos_libres"] == 16

    assert disco.cola_disco() == []
    assert archivos.fs_estado_disco()["bloques_libres"] == 200


def test_reiniciar_sistema_elimina_el_estado_anterior():
    pid = procesos.crear_proceso("p", "u", [["CPU", 5]], memoria_bytes=1024, cuota_marcos=2)
    memoria.acceder_memoria(pid, 0)
    archivos.fs_escribir("/archivo.txt", "contenido", "admin")
    disco.encolar_solicitud_disco(pid, 10, "L")
    kernel.tick()
    assert kernel.reloj_actual() == 1

    kernel.iniciar_sistema(
        {
            "num_cpus": 2,
            "marcos_fisicos": 16,
            "tam_pagina": 256,
            "bloques_disco": 200,
            "tam_bloque": 512,
            "cache_bloques": 8,
        }
    )

    assert kernel.reloj_actual() == 0
    assert procesos.listar_procesos() == []
    assert memoria.estado_memoria()["marcos_libres"] == 16
    assert disco.cola_disco() == []
    assert disco.metricas_disco()["solicitudes_atendidas"] == 0
    assert archivos.fs_estado_disco()["bloques_libres"] == 200


def test_tick_incrementa_el_reloj_exactamente_una_unidad():
    for esperado in range(1, 6):
        kernel.tick()
        assert kernel.reloj_actual() == esperado


def test_ejecutar_ticks_ejecuta_la_cantidad_solicitada():
    kernel.ejecutar_ticks(7)
    assert kernel.reloj_actual() == 7
    kernel.ejecutar_ticks(0)
    assert kernel.reloj_actual() == 7


def test_ejecutar_ticks_rechaza_cantidades_negativas():
    with pytest.raises(ValueError):
        kernel.ejecutar_ticks(-1)
    assert kernel.reloj_actual() == 0


def test_resumen_sistema_refleja_el_estado_actual():
    procesos.crear_proceso("p", "u", [["CPU", 10]], memoria_bytes=512, cuota_marcos=2)
    kernel.tick()
    resumen = kernel.resumen_sistema()
    assert resumen["reloj"] == 1
    assert resumen["procesos_activos"] == 1
    assert resumen["marcos_libres"] <= 16
    assert resumen["bloques_libres"] == 200


def test_apagar_sistema_devuelve_resumen_del_estado_final():
    procesos.crear_proceso("p", "u", [["CPU", 1]], memoria_bytes=512, cuota_marcos=2)
    kernel.ejecutar_ticks(2)
    resumen = kernel.apagar_sistema()
    assert resumen["reloj"] == 2
    assert resumen["procesos_activos"] == 0
    assert set(resumen) == {"reloj", "procesos_activos", "marcos_libres", "bloques_libres"}


def test_las_llegadas_del_escenario_ocurren_en_su_tick(cargar_escenario):
    cargar_escenario(
        usuarios=["u"],
        catalogo={
            "web": {
                "memoria_bytes": 512,
                "cuota_marcos": 2,
                "prioridad": 1,
                "programa": [["CPU", 2]],
            }
        },
        llegadas=[
            {"tick": 2, "programa": "web", "usuario": "u"},
            {"tick": 4, "programa": "web", "usuario": "u"},
        ],
    )

    assert procesos.listar_procesos() == []
    kernel.tick()
    assert procesos.listar_procesos() == []
    kernel.tick()
    assert procesos.estado_proceso(0) in {"EJECUTANDO", "LISTO"}
    kernel.tick()
    with pytest.raises(ErrorNoExiste):
        procesos.estado_proceso(1)
    kernel.tick()
    assert procesos.estado_proceso(1) in {"EJECUTANDO", "LISTO"}


def test_la_llegada_se_procesa_antes_de_ejecutar_cpu(cargar_escenario):
    cargar_escenario(
        config={
            "num_cpus": 1,
            "marcos_fisicos": 8,
            "tam_pagina": 256,
            "bloques_disco": 50,
            "tam_bloque": 64,
            "cache_bloques": 4,
        },
        usuarios=["u"],
        catalogo={
            "job": {
                "memoria_bytes": 256,
                "cuota_marcos": 1,
                "prioridad": 0,
                "programa": [["CPU", 2]],
            }
        },
        llegadas=[
            {"tick": 1, "programa": "job", "usuario": "u"},
            {"tick": 1, "programa": "job", "usuario": "u"},
        ],
    )
    kernel.tick()
    assert procesos.estado_proceso(0) == "EJECUTANDO"
    assert procesos.estado_proceso(1) == "LISTO"


def test_la_es_terminada_se_atiende_antes_de_ejecutar_cpu(cargar_escenario):
    cargar_escenario(
        config={
            "num_cpus": 1,
            "marcos_fisicos": 8,
            "tam_pagina": 256,
            "bloques_disco": 50,
            "tam_bloque": 64,
            "cache_bloques": 4,
        },
        usuarios=["u"],
        catalogo={
            "io": {
                "memoria_bytes": 256,
                "cuota_marcos": 1,
                "prioridad": 0,
                "programa": [["ES", 5], ["CPU", 1]],
            }
        },
        llegadas=[{"tick": 1, "programa": "io", "usuario": "u"}],
    )
    kernel.tick()
    assert procesos.estado_proceso(0) == "BLOQUEADO"
    kernel.tick()
    assert procesos.estado_proceso(0) == "TERMINADO"


def test_los_procesos_simulados_no_son_hilos_del_anfitrion():
    hilos_antes = {hilo.ident for hilo in threading.enumerate()}
    pids = [
        procesos.crear_proceso(f"p{i}", "u", [["CPU", 5]], memoria_bytes=256, cuota_marcos=1)
        for i in range(5)
    ]
    kernel.ejecutar_ticks(3)
    hilos_despues = {hilo.ident for hilo in threading.enumerate()}
    assert hilos_despues - hilos_antes == set()
    assert all(procesos.estado_proceso(pid) in {"EJECUTANDO", "LISTO", "TERMINADO"} for pid in pids)


def test_configuracion_invalida_no_borra_el_estado_anterior():
    pid = procesos.crear_proceso("p", "u", [["CPU", 5]])
    with pytest.raises(ValueError):
        kernel.iniciar_sistema({"num_cpus": 0})
    assert kernel.reloj_actual() == 0
    assert procesos.estado_proceso(pid) == "NUEVO"


# ---------------------------------------------------------------------------
# Procesos y planificación
# ---------------------------------------------------------------------------


def test_crear_proceso_asigna_pid_unico_y_estado_nuevo():
    pids = [
        procesos.crear_proceso(f"p{i}", "u", [["CPU", 2]], memoria_bytes=512, cuota_marcos=2)
        for i in range(5)
    ]
    assert len(set(pids)) == 5
    assert all(procesos.estado_proceso(pid) == "NUEVO" for pid in pids)


def test_listar_procesos_no_duplica_entradas():
    pid = procesos.crear_proceso("p", "u", [["CPU", 2]])
    listado = procesos.listar_procesos()
    assert len(listado) == 1
    assert listado[0]["pid"] == pid
    assert listado[0]["nombre"] == "p"


def test_crear_hilo_asociado_a_un_proceso():
    pid = procesos.crear_proceso("p", "u", [["CPU", 2]])
    tid = procesos.crear_hilo(pid, [["CPU", 1]])
    assert isinstance(tid, int)
    assert tid >= 0


def test_transiciones_nuevo_ejecutando_terminado():
    pid = procesos.crear_proceso("p", "u", [["CPU", 2]])
    assert procesos.estado_proceso(pid) == "NUEVO"
    kernel.tick()
    assert procesos.estado_proceso(pid) == "EJECUTANDO"
    kernel.tick()
    assert procesos.estado_proceso(pid) == "TERMINADO"


def test_transicion_bloqueado_por_fallo_de_pagina():
    pid = procesos.crear_proceso(
        "p", "u", [["MEM", 0], ["CPU", 1]], memoria_bytes=512, cuota_marcos=2
    )
    kernel.tick()
    assert procesos.estado_proceso(pid) == "BLOQUEADO"


def test_transicion_bloqueado_por_es_y_reanudacion():
    pid = procesos.crear_proceso(
        "p", "u", [["ES", 5], ["CPU", 1]], memoria_bytes=256, cuota_marcos=1
    )
    kernel.tick()
    assert procesos.estado_proceso(pid) == "BLOQUEADO"
    kernel.tick()
    assert procesos.estado_proceso(pid) == "TERMINADO"


def test_cola_listos_y_proceso_en_ejecucion():
    kernel.iniciar_sistema(
        {
            "num_cpus": 1,
            "marcos_fisicos": 16,
            "tam_pagina": 256,
            "bloques_disco": 200,
            "tam_bloque": 512,
            "cache_bloques": 8,
        }
    )
    pids = [
        procesos.crear_proceso(f"p{i}", "u", [["CPU", 2]], memoria_bytes=256, cuota_marcos=1)
        for i in range(3)
    ]
    kernel.tick()
    assert procesos.proceso_en_ejecucion(0) == pids[0]
    assert procesos.cola_listos() == pids[1:]


def test_terminar_proceso_libera_sus_marcos():
    pid = procesos.crear_proceso("p", "u", [["CPU", 10]], memoria_bytes=1024, cuota_marcos=2)
    memoria.acceder_memoria(pid, 0)
    assert memoria.estado_memoria()["marcos_por_proceso"][pid] == 1
    procesos.terminar_proceso(pid)
    assert procesos.estado_proceso(pid) == "TERMINADO"
    assert pid not in memoria.estado_memoria()["marcos_por_proceso"]
    assert memoria.tabla_paginas(pid) == {}


def test_metricas_de_planificacion_incluyen_todas_las_claves():
    pids = [
        procesos.crear_proceso(f"p{i}", "u", [["CPU", 3]], memoria_bytes=256, cuota_marcos=1)
        for i in range(4)
    ]
    _ejecutar_hasta_terminar(pids)
    metricas = procesos.metricas_planificacion()
    assert set(metricas) == {
        "espera_promedio",
        "respuesta_promedio",
        "retorno_promedio",
        "espera_maxima",
        "utilizacion_cpu",
        "cambios_contexto",
        "procesos_terminados",
    }
    assert metricas["procesos_terminados"] == 4
    assert metricas["espera_promedio"] >= 0
    assert metricas["respuesta_promedio"] >= 0
    assert metricas["retorno_promedio"] >= 0
    assert 0 <= metricas["utilizacion_cpu"] <= 1
    assert metricas["cambios_contexto"] >= 1


def test_politica_de_planificacion_es_informada():
    politica = procesos.politica_planificacion()
    assert isinstance(politica, str)
    assert politica.strip() != ""


def test_crear_proceso_rechaza_programa_vacio():
    with pytest.raises(ValueError):
        procesos.crear_proceso("vacio", "u", [])


def test_crear_proceso_rechaza_instruccion_invalida():
    with pytest.raises(ValueError):
        procesos.crear_proceso("malo", "u", [["INSTRUCCION", 1]])


def test_consultar_y_terminar_pid_inexistente():
    with pytest.raises(ErrorNoExiste):
        procesos.estado_proceso(999)
    with pytest.raises(ErrorNoExiste):
        procesos.terminar_proceso(999)


# ---------------------------------------------------------------------------
# Requisitos medibles de planificación
# ---------------------------------------------------------------------------


def test_RP1_respuesta_promedio_web_menor_o_igual_a_10(cargar_escenario):
    catalogo = {
        "web": {
            "memoria_bytes": 512,
            "cuota_marcos": 2,
            "prioridad": 1,
            "programa": [["CPU", 5]],
        }
    }
    cargar_escenario(
        config={
            "num_cpus": 2,
            "marcos_fisicos": 64,
            "tam_pagina": 256,
            "bloques_disco": 200,
            "tam_bloque": 512,
            "cache_bloques": 8,
        },
        usuarios=["u"],
        catalogo=catalogo,
        llegadas=[{"tick": 0, "programa": "web", "usuario": "u"} for _ in range(10)],
    )
    pids = sorted({p["pid"] for p in procesos.listar_procesos()})
    _ejecutar_hasta_terminar(pids)
    assert procesos.metricas_planificacion()["respuesta_promedio"] <= 10


def test_RP2_ningun_proceso_espera_mas_de_150_ticks_consecutivos():
    kernel.iniciar_sistema(
        {
            "num_cpus": 1,
            "marcos_fisicos": 256,
            "tam_pagina": 256,
            "bloques_disco": 200,
            "tam_bloque": 512,
            "cache_bloques": 8,
        }
    )
    pids = [
        procesos.crear_proceso(
            f"p{i}", "u", [["CPU", 10]], memoria_bytes=256, cuota_marcos=1, prioridad=i % 3
        )
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
            if estado == "TERMINADO":
                terminados += 1
        if terminados == len(pids):
            break
    assert max(espera_maxima.values()) <= 150


def test_RP3_utilizacion_de_cpu_al_menos_85_por_ciento():
    kernel.iniciar_sistema(
        {
            "num_cpus": 2,
            "marcos_fisicos": 64,
            "tam_pagina": 256,
            "bloques_disco": 200,
            "tam_bloque": 512,
            "cache_bloques": 8,
        }
    )
    pids = [
        procesos.crear_proceso(f"p{i}", "u", [["CPU", 20]], memoria_bytes=256, cuota_marcos=1)
        for i in range(10)
    ]
    _ejecutar_hasta_terminar(pids)
    assert procesos.metricas_planificacion()["utilizacion_cpu"] >= 0.85
