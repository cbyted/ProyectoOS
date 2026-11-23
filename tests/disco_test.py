import pytest

from minidc import disco, kernel


CONFIG = {
    "num_cpus": 1,
    "marcos_fisicos": 8,
    "tam_pagina": 256,
    "bloques_disco": 200,
    "tam_bloque": 512,
    "cache_bloques": 2,
}


@pytest.fixture(autouse=True)
def sistema_inicializado():
    kernel.iniciar_sistema(CONFIG)


def test_cscan_atiende_hacia_arriba_y_luego_envuelve_al_inicio():
    disco._configurar(200, 512, 0)
    disco.encolar_solicitud_disco(1, 50, "L")
    assert disco.procesar_disco() == [50]

    disco.encolar_solicitud_disco(1, 120, "L")
    disco.encolar_solicitud_disco(2, 10, "E")
    disco.encolar_solicitud_disco(3, 90, "L")

    assert disco.cola_disco() == [90, 120, 10]
    assert disco.procesar_disco() == [90, 120, 10]
    assert disco.metricas_disco() == {
        "solicitudes_atendidas": 4,
        "desplazamiento_total": 408,
        "posicion_cabezal": 10,
    }


def test_cache_lru_cuenta_aciertos_fallos_y_tasa():
    disco.encolar_solicitud_disco(1, 5, "L")
    disco.encolar_solicitud_disco(1, 6, "L")
    assert disco.procesar_disco() == [5, 6]

    # El acceso a 5 lo mantiene en caché y desplaza a 6 como menos reciente.
    disco.encolar_solicitud_disco(1, 5, "L")
    disco.procesar_disco()
    disco.encolar_solicitud_disco(1, 7, "L")
    disco.procesar_disco()
    disco.encolar_solicitud_disco(1, 6, "L")
    disco.procesar_disco()

    assert disco.info_cache() == {
        "capacidad_bloques": 2,
        "aciertos": 1,
        "fallos": 4,
        "tasa_aciertos": 0.2,
    }


def test_validacion_de_solicitudes_no_consume_identificadores():
    with pytest.raises(ValueError):
        disco.encolar_solicitud_disco(1, CONFIG["bloques_disco"], "L")
    with pytest.raises(ValueError):
        disco.encolar_solicitud_disco(1, 0, "X")

    assert disco.encolar_solicitud_disco(1, 0, "l") == 0


def test_reiniciar_kernel_reinicia_cabezal_metricas_y_cache():
    disco.encolar_solicitud_disco(1, 10, "L")
    disco.procesar_disco()
    kernel.iniciar_sistema(CONFIG)

    assert disco.cola_disco() == []
    assert disco.metricas_disco() == {
        "solicitudes_atendidas": 0,
        "desplazamiento_total": 0,
        "posicion_cabezal": 0,
    }
    assert disco.info_cache() == {
        "capacidad_bloques": 2,
        "aciertos": 0,
        "fallos": 0,
        "tasa_aciertos": 0.0,
    }
    assert disco.politica_disco() == "C-SCAN"