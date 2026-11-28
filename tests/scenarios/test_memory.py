"""Pruebas de caja negra para memoria virtual paginada."""

from __future__ import annotations

import pytest

from minidc import kernel, memoria, procesos
from minidc.errores import ErrorMemoria


CONFIG_MEMORIA = {
    "num_cpus": 1,
    "marcos_fisicos": 16,
    "tam_pagina": 256,
    "bloques_disco": 200,
    "tam_bloque": 512,
    "cache_bloques": 4,
}


def _reiniciar(frames=16, pagina=256):
    kernel.iniciar_sistema(
        {
            "num_cpus": 1,
            "marcos_fisicos": frames,
            "tam_pagina": pagina,
            "bloques_disco": 200,
            "tam_bloque": 512,
            "cache_bloques": 4,
        }
    )


def test_acceso_valido_genera_fallo_y_luego_acierto():
    _reiniciar()
    pid = procesos.crear_proceso("p", "u", [["CPU", 10]], memoria_bytes=1024, cuota_marcos=4)
    primero = memoria.acceder_memoria(pid, 0)
    segundo = memoria.acceder_memoria(pid, 10)
    assert primero["fallo_pagina"] is True
    assert segundo["fallo_pagina"] is False
    assert primero["marco"] == segundo["marco"]
    metricas = memoria.metricas_memoria()
    assert metricas["accesos"] == 2
    assert metricas["fallos_pagina"] == 1


def test_fallo_de_pagina_bloquea_el_proceso_cinco_ticks():
    _reiniciar()
    pid = procesos.crear_proceso(
        "p", "u", [["MEM", 0], ["CPU", 1]], memoria_bytes=512, cuota_marcos=2
    )
    for tick in range(1, 6):
        kernel.tick()
        assert procesos.estado_proceso(pid) == "BLOQUEADO", f"tick {tick}"
    kernel.tick()
    assert procesos.estado_proceso(pid) == "TERMINADO"


def test_se_respeta_la_cuota_maxima_de_marcos_por_proceso():
    _reiniciar(frames=16)
    pid = procesos.crear_proceso("p", "u", [["CPU", 10]], memoria_bytes=2048, cuota_marcos=2)
    for pagina in range(8):
        memoria.acceder_memoria(pid, pagina * 256)
    estado = memoria.estado_memoria()
    assert estado["marcos_por_proceso"][pid] <= 2
    tabla = memoria.tabla_paginas(pid)
    assert sum(1 for entrada in tabla.values() if entrada["presente"]) <= 2


def test_liberar_memoria_devuelve_los_marcos_y_limpia_la_tabla():
    _reiniciar()
    pid = procesos.crear_proceso("p", "u", [["CPU", 10]], memoria_bytes=1024, cuota_marcos=2)
    memoria.acceder_memoria(pid, 0)
    memoria.acceder_memoria(pid, 256)
    liberados = memoria.liberar_memoria(pid)
    assert liberados == 2
    assert memoria.tabla_paginas(pid) == {}
    assert pid not in memoria.estado_memoria()["marcos_por_proceso"]
    assert memoria.estado_memoria()["marcos_libres"] == 16


def test_la_tabla_de_paginas_es_coherente():
    _reiniciar()
    pid = procesos.crear_proceso("p", "u", [["CPU", 10]], memoria_bytes=1024, cuota_marcos=2)
    memoria.acceder_memoria(pid, 0)
    memoria.acceder_memoria(pid, 300)
    tabla = memoria.tabla_paginas(pid)
    assert set(tabla) == {0, 1, 2, 3}
    for entrada in tabla.values():
        if entrada["presente"]:
            assert isinstance(entrada["marco"], int)
            assert entrada["marco"] >= 0
        else:
            assert entrada["marco"] is None


def test_metricas_de_memoria_son_coherentes():
    _reiniciar()
    pid = procesos.crear_proceso("p", "u", [["CPU", 10]], memoria_bytes=1024, cuota_marcos=2)
    for direccion in [0, 10, 256, 300, 512, 600]:
        memoria.acceder_memoria(pid, direccion)
    metricas = memoria.metricas_memoria()
    assert set(metricas) == {
        "accesos",
        "fallos_pagina",
        "tasa_fallos",
        "reemplazos",
        "escrituras_a_swap",
    }
    assert metricas["accesos"] == 6
    assert metricas["fallos_pagina"] >= 1
    assert metricas["tasa_fallos"] == pytest.approx(
        metricas["fallos_pagina"] / metricas["accesos"]
    )
    assert metricas["reemplazos"] <= metricas["fallos_pagina"]


def test_escritura_a_swap_al_reemplazar_pagina_modificada():
    _reiniciar(frames=4)
    pid = procesos.crear_proceso("p", "u", [["CPU", 10]], memoria_bytes=1024, cuota_marcos=2)
    for pagina in range(4):
        memoria.acceder_memoria(pid, pagina * 256, escritura=True)
    metricas = memoria.metricas_memoria()
    assert metricas["reemplazos"] >= 2
    assert metricas["escrituras_a_swap"] >= 2


def test_direccion_invalida_lanza_error_memoria_sin_afectar_a_otros():
    _reiniciar()
    p0 = procesos.crear_proceso("p0", "u", [["CPU", 10]], memoria_bytes=512, cuota_marcos=2)
    p1 = procesos.crear_proceso("p1", "u", [["CPU", 10]], memoria_bytes=512, cuota_marcos=2)
    memoria.acceder_memoria(p1, 0)
    tabla_antes = memoria.tabla_paginas(p1)
    estado_antes = procesos.estado_proceso(p1)
    metricas_antes = memoria.metricas_memoria()

    with pytest.raises(ErrorMemoria):
        memoria.acceder_memoria(p0, 512)
    with pytest.raises(ErrorMemoria):
        memoria.acceder_memoria(p0, -1)

    assert memoria.tabla_paginas(p1) == tabla_antes
    assert procesos.estado_proceso(p1) == estado_antes
    assert memoria.metricas_memoria() == metricas_antes


def test_RM3_un_acceso_fuera_del_espacio_lanza_ErrorMemoria():
    _reiniciar()
    pid = procesos.crear_proceso("p", "u", [["CPU", 10]], memoria_bytes=512, cuota_marcos=2)
    with pytest.raises(ErrorMemoria):
        memoria.acceder_memoria(pid, 512)


def test_se_detecta_hiperpaginacion_con_fallos_recientes():
    _reiniciar(frames=4)
    pid = procesos.crear_proceso("p", "u", [["CPU", 100]], memoria_bytes=40 * 256, cuota_marcos=2)
    for pagina in range(10):
        memoria.acceder_memoria(pid, pagina * 256)
    assert memoria.detectar_hiperpaginacion() is True
    assert memoria.fallos_recientes()


def test_RM1_tasa_de_fallos_menor_o_igual_a_25_por_ciento():
    _reiniciar()
    pid = procesos.crear_proceso("p", "u", [["CPU", 100]], memoria_bytes=1024, cuota_marcos=4)
    for _ in range(10):
        for pagina in range(4):
            memoria.acceder_memoria(pid, pagina * 256)
    metricas = memoria.metricas_memoria()
    assert metricas["accesos"] == 40
    assert metricas["tasa_fallos"] <= 0.25


def test_RM2_el_sistema_reacciona_y_reduce_fallos_tras_hiperpaginacion():
    _reiniciar(frames=8)
    pid = procesos.crear_proceso("p", "u", [["CPU", 1000]], memoria_bytes=40 * 256, cuota_marcos=2)
    kernel.tick()
    assert procesos.estado_proceso(pid) == "EJECUTANDO"

    for pagina in range(10):
        memoria.acceder_memoria(pid, pagina * 256)
    assert memoria.detectar_hiperpaginacion() is True
    antes = memoria.metricas_memoria()

    for _ in range(50):
        kernel.tick()

    despues = memoria.metricas_memoria()
    accesos = despues["accesos"] - antes["accesos"]
    fallos = despues["fallos_pagina"] - antes["fallos_pagina"]
    assert accesos > 0
    tasa_despues = fallos / accesos
    tasa_antes = antes["tasa_fallos"]
    assert tasa_despues < tasa_antes


def test_estado_memoria_y_politica_de_reemplazo():
    _reiniciar()
    estado = memoria.estado_memoria()
    assert set(estado) == {
        "marcos_totales",
        "marcos_libres",
        "marcos_por_proceso",
        "fragmentacion_interna_bytes",
    }
    assert estado["marcos_totales"] == 16
    assert estado["marcos_libres"] == 16
    politica = memoria.politica_reemplazo()
    assert isinstance(politica, str)
    assert politica.strip() != ""


def test_acceder_memoria_de_un_proceso_no_registrado_lanza_ErrorMemoria():
    _reiniciar()
    with pytest.raises(ErrorMemoria):
        memoria.acceder_memoria(999, 0)
