"""Auditoría de caja negra de memoria virtual paginada."""
from __future__ import annotations

import pytest

from minidc import kernel, memoria, procesos
from minidc.errores import ErrorMemoria


def _reset(frames=16):
    kernel.iniciar_sistema({
        "num_cpus": 2, "marcos_fisicos": frames, "tam_pagina": 256,
        "bloques_disco": 200, "tam_bloque": 512, "cache_bloques": 4,
    })


def test_acceso_valido_fallo_inicial_y_acierto_posterior(sistema_limpio):
    pid = procesos.crear_proceso("mem", "u", [["CPU", 10]], memoria_bytes=1024, cuota_marcos=4)
    primera = memoria.acceder_memoria(pid, 0)
    segunda = memoria.acceder_memoria(pid, 20)
    assert primera["fallo_pagina"] is True
    assert segunda["fallo_pagina"] is False
    assert primera["marco"] == segunda["marco"]
    metricas = memoria.metricas_memoria()
    assert metricas["accesos"] == 2
    assert metricas["fallos_pagina"] == 1


def test_limite_de_memoria_y_aislamiento_de_otro_proceso(sistema_limpio):
    p0 = procesos.crear_proceso("fuera", "u", [["CPU", 10]], memoria_bytes=512, cuota_marcos=2)
    p1 = procesos.crear_proceso("sano", "u", [["CPU", 10]], memoria_bytes=512, cuota_marcos=2)
    memoria.acceder_memoria(p1, 0)
    tabla_antes = memoria.tabla_paginas(p1)
    metricas_antes = memoria.metricas_memoria()
    for direccion in (-1, 512):
        with pytest.raises(ErrorMemoria):
            memoria.acceder_memoria(p0, direccion)
    assert memoria.tabla_paginas(p1) == tabla_antes
    assert memoria.metricas_memoria() == metricas_antes


def test_cuota_por_proceso_y_liberacion_de_marcos(sistema_limpio):
    pid = procesos.crear_proceso("cuota", "u", [["CPU", 10]], memoria_bytes=2048, cuota_marcos=2)
    for pagina in range(8):
        memoria.acceder_memoria(pid, pagina * 256)
    estado = memoria.estado_memoria()
    assert estado["marcos_por_proceso"][pid] <= 2
    assert sum(1 for e in memoria.tabla_paginas(pid).values() if e["presente"]) <= 2
    procesos.terminar_proceso(pid)
    assert pid not in memoria.estado_memoria()["marcos_por_proceso"]


def test_RM1_tasa_de_fallos_no_supera_25_por_ciento(sistema_limpio):
    pid = procesos.crear_proceso("localidad", "u", [["CPU", 100]], memoria_bytes=1024, cuota_marcos=4)
    for _ in range(10):
        for pagina in range(4):
            memoria.acceder_memoria(pid, pagina * 256)
    metricas = memoria.metricas_memoria()
    assert metricas["accesos"] == 40
    assert metricas["tasa_fallos"] == pytest.approx(metricas["fallos_pagina"] / metricas["accesos"])
    assert metricas["tasa_fallos"] <= 0.25


def test_deteccion_de_hiperpaginacion_con_carga_de_fallos(sistema_limpio):
    _reset(frames=4)
    pid = procesos.crear_proceso("thrash", "u", [["CPU", 100]], memoria_bytes=40 * 256, cuota_marcos=2)
    for pagina in range(10):
        memoria.acceder_memoria(pid, pagina * 256)
    assert memoria.detectar_hiperpaginacion() is True
    assert memoria.fallos_recientes()


def test_RM2_reaccion_y_tasa_de_fallos_durante_50_ticks(sistema_limpio):
    """Prepara tráfico real posterior al disparo; no usa solo CPU vacía."""
    _reset(frames=8)
    patron = [["MEM", pagina * 256] for _ in range(8) for pagina in range(10)]
    pid_thrashing = procesos.crear_proceso(
        "thrashing", "u", [["CPU", 1], *patron], memoria_bytes=40 * 256, cuota_marcos=2
    )
    procesos.crear_proceso(
        "estable", "u", [["MEM", 0] for _ in range(100)], memoria_bytes=256, cuota_marcos=1
    )
    kernel.tick()
    for pagina in range(10):
        memoria.acceder_memoria(pid_thrashing, pagina * 256)
    assert memoria.detectar_hiperpaginacion() is True

    antes = memoria.metricas_memoria()
    for _ in range(50):
        kernel.tick()
    despues = memoria.metricas_memoria()

    accesos = despues["accesos"] - antes["accesos"]
    fallos = despues["fallos_pagina"] - antes["fallos_pagina"]
    assert accesos > 0, "No hubo accesos suficientes para evaluar la recuperación"
    assert fallos / accesos < antes["tasa_fallos"]


def test_politica_y_metricas_publicas_de_memoria(sistema_limpio):
    politica = memoria.politica_reemplazo()
    metricas = memoria.metricas_memoria()
    claves = {"accesos", "fallos_pagina", "tasa_fallos", "reemplazos", "escrituras_a_swap"}
    assert isinstance(politica, str) and politica.strip()
    assert claves <= set(metricas)
