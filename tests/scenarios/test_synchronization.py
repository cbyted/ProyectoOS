"""Pruebas de caja negra para sincronización e interbloqueos."""

from __future__ import annotations

import pytest

from minidc import kernel, procesos, sincronizacion
from minidc.errores import ErrorSincronizacion


NOMBRES_REQUERIDOS = {
    "crear_semaforo",
    "semaforo_wait",
    "semaforo_signal",
    "estado_semaforo",
    "crear_mutex",
    "mutex_lock",
    "mutex_unlock",
    "detectar_interbloqueo",
    "resolver_interbloqueo",
    "demo_condicion_carrera",
}


def test_la_api_publica_de_sincronizacion_esta_disponible():
    faltantes = sorted(nombre for nombre in NOMBRES_REQUERIDOS if not hasattr(sincronizacion, nombre))
    assert faltantes == []


def test_semaforo_inicializacion_wait_signal_y_cola_de_espera():
    sincronizacion.crear_semaforo("s", 1)
    estado = sincronizacion.estado_semaforo("s")
    assert estado["valor"] == 1
    assert estado["cola"] == []

    p0 = procesos.crear_proceso("p0", "u", [["CPU", 10]])
    p1 = procesos.crear_proceso("p1", "u", [["CPU", 10]])

    sincronizacion.semaforo_wait("s", p0)
    assert sincronizacion.estado_semaforo("s")["valor"] == 0

    sincronizacion.semaforo_wait("s", p1)
    estado = sincronizacion.estado_semaforo("s")
    assert estado["valor"] == 0
    assert estado["cola"] == [p1]
    assert procesos.estado_proceso(p1) == "BLOQUEADO"

    sincronizacion.semaforo_signal("s")
    estado = sincronizacion.estado_semaforo("s")
    assert estado["cola"] == []
    assert procesos.estado_proceso(p1) in {"LISTO", "EJECUTANDO"}


def test_mutex_exclusion_mutua_y_liberacion_por_propietario():
    sincronizacion.crear_mutex("m")
    p0 = procesos.crear_proceso("p0", "u", [["CPU", 10]])
    p1 = procesos.crear_proceso("p1", "u", [["CPU", 10]])

    sincronizacion.mutex_lock("m", p0)
    sincronizacion.mutex_lock("m", p1)
    assert procesos.estado_proceso(p1) == "BLOQUEADO"

    with pytest.raises(ErrorSincronizacion):
        sincronizacion.mutex_unlock("m", p1)

    sincronizacion.mutex_unlock("m", p0)
    assert procesos.estado_proceso(p1) in {"LISTO", "EJECUTANDO"}


def test_deteccion_y_resolucion_de_interbloqueo_con_dos_mutex():
    p0 = procesos.crear_proceso("p0", "u", [["CPU", 10]])
    p1 = procesos.crear_proceso("p1", "u", [["CPU", 10]])
    sincronizacion.crear_mutex("A")
    sincronizacion.crear_mutex("B")

    sincronizacion.mutex_lock("A", p0)
    sincronizacion.mutex_lock("B", p1)
    sincronizacion.mutex_lock("B", p0)
    sincronizacion.mutex_lock("A", p1)

    detectados = sincronizacion.detectar_interbloqueo()
    assert p0 in detectados
    assert p1 in detectados

    resueltos = sincronizacion.resolver_interbloqueo()
    assert set(resueltos) >= {p0, p1}
    assert sincronizacion.detectar_interbloqueo() == []


def test_RS1_la_demostracion_sincronizada_no_pierde_actualizaciones():
    resultado = sincronizacion.demo_condicion_carrera(
        usar_sincronizacion=True,
        num_hilos=10,
        iteraciones=1000,
    )
    assert resultado == 10000


def test_RS2_despues_de_resolver_no_quedan_interbloqueos():
    p0 = procesos.crear_proceso("p0", "u", [["CPU", 10]])
    p1 = procesos.crear_proceso("p1", "u", [["CPU", 10]])
    sincronizacion.crear_mutex("A")
    sincronizacion.crear_mutex("B")
    sincronizacion.mutex_lock("A", p0)
    sincronizacion.mutex_lock("B", p1)
    sincronizacion.mutex_lock("B", p0)
    sincronizacion.mutex_lock("A", p1)
    sincronizacion.resolver_interbloqueo()
    assert sincronizacion.detectar_interbloqueo() == []
