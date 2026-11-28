import pytest

from minidc import kernel, memoria, procesos
from minidc.errores import ErrorMemoria


CONFIG = {
    "num_cpus": 1,
    "marcos_fisicos": 2,
    "tam_pagina": 256,
    "bloques_disco": 200,
    "tam_bloque": 512,
    "cache_bloques": 8,
}


def pid_con_memoria():
    kernel.iniciar_sistema(CONFIG)
    memoria.inicializar_memoria(CONFIG)
    pid = procesos.crear_proceso(
        nombre="prueba",
        usuario="usuario_prueba",
        programa=[("CPU", 1)],
        memoria_bytes=768,  # Tres páginas de 256 bytes
        cuota_marcos=2,
    )
    memoria.registrar_proceso(
        pid=pid,
        memoria_bytes=768,
        cuota_marcos=2,
    )
    return pid


def test_acceder_memoria_fallo_acierto_escritura_y_lru():
    pid = pid_con_memoria()

    # Primera referencia a la página 0: fallo.
    primera = memoria.acceder_memoria(pid, 0)
    assert primera["fallo_pagina"] is True
    assert primera["pagina_reemplazada"] is None

    # Dirección distinta, pero de la misma página: acierto y escritura.
    segunda = memoria.acceder_memoria(pid, 10, escritura=True)
    assert segunda["marco"] == primera["marco"]
    assert segunda["fallo_pagina"] is False

    # Cargar página 1 y volver a usar página 0 para hacerla más reciente.
    memoria.acceder_memoria(pid, 256)
    memoria.acceder_memoria(pid, 0)

    # Al cargar página 2 se debe reemplazar la página 1, menos reciente.
    resultado = memoria.acceder_memoria(pid, 512)

    assert resultado["fallo_pagina"] is True
    assert resultado["pagina_reemplazada"] == (pid, 1)


def test_acceder_memoria_direccion_invalida_no_cambia_metricas():
    pid = pid_con_memoria()
    metricas_antes = memoria.metricas_memoria()

    with pytest.raises(ErrorMemoria):
        memoria.acceder_memoria(pid, 768)

    assert memoria.metricas_memoria() == metricas_antes


def test_tabla_paginas_refleja_accesos():
    pid = pid_con_memoria()

    memoria.acceder_memoria(pid, 0, escritura=True)
    tabla = memoria.tabla_paginas(pid)

    assert set(tabla) == {0, 1, 2}
    assert tabla[0]["presente"] is True
    assert isinstance(tabla[0]["marco"], int)
    assert tabla[0]["modificada"] is True
    assert tabla[0]["referenciada"] is True

    assert tabla[1] == {
        "marco": None,
        "presente": False,
        "modificada": False,
        "referenciada": False,
    }


def test_liberar_memoria_devuelve_marcos_liberados():
    pid = pid_con_memoria()

    memoria.acceder_memoria(pid, 0)
    memoria.acceder_memoria(pid, 256)

    liberados = memoria.liberar_memoria(pid)

    assert liberados == 2
    assert memoria.estado_memoria()["marcos_libres"] == 2
    assert memoria.tabla_paginas(pid) == {}


def test_estado_memoria_informa_marcos_y_fragmentacion():
    pid = pid_con_memoria()

    memoria.acceder_memoria(pid, 0)
    estado = memoria.estado_memoria()

    assert estado == {
        "marcos_totales": 2,
        "marcos_libres": 1,
        "marcos_por_proceso": {pid: 1},
        "fragmentacion_interna_bytes": 0,
    }


def test_metricas_memoria_cuenta_fallos_aciertos_y_reemplazos():
    pid = pid_con_memoria()

    memoria.acceder_memoria(pid, 0)  # Fallo
    memoria.acceder_memoria(pid, 0)  # Acierto
    memoria.acceder_memoria(pid, 256)  # Fallo
    memoria.acceder_memoria(pid, 512)  # Fallo y reemplazo

    metricas = memoria.metricas_memoria()

    assert metricas["accesos"] == 4
    assert metricas["fallos_pagina"] == 3
    assert metricas["tasa_fallos"] == pytest.approx(1 / 4)
    assert metricas["reemplazos"] == 1
    assert metricas["escrituras_a_swap"] == 0


def test_detectar_hiperpaginacion():
    pid = pid_con_memoria()

    assert memoria.detectar_hiperpaginacion() is False

    # Tres páginas virtuales y solo dos marcos: la secuencia cíclica
    # debe provocar al menos cinco fallos en los últimos diez accesos.
    direcciones = [0, 256, 512] * 4
    for direccion in direcciones:
        memoria.acceder_memoria(pid, direccion)

    assert memoria.detectar_hiperpaginacion() is True


def test_politica_reemplazo_devuelve_nombre():
    kernel.iniciar_sistema(CONFIG)

    assert memoria.politica_reemplazo() == "LRU"
