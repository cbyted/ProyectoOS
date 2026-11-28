"""Auditoría de caja negra de semáforos, mutex e interbloqueos."""
from __future__ import annotations

from minidc import procesos, sincronizacion


API_REQUERIDA = {
    "crear_semaforo", "semaforo_wait", "semaforo_signal", "estado_semaforo",
    "crear_mutex", "mutex_lock", "mutex_unlock", "detectar_interbloqueo",
    "resolver_interbloqueo", "demo_condicion_carrera",
}


def test_el_modulo_expone_la_api_publica_requerida():
    faltantes = sorted(
        nombre for nombre in API_REQUERIDA
        if not callable(getattr(sincronizacion, nombre, None))
    )
    assert not faltantes, "Faltan operaciones públicas: " + ", ".join(faltantes)


def test_semaforo_bloquea_y_despierta_procesos(sistema_limpio, api_sincronizacion_disponible):
    sync = api_sincronizacion_disponible
    sync.crear_semaforo("recurso", 1)
    p0 = procesos.crear_proceso("p0", "u", [["CPU", 10]])
    p1 = procesos.crear_proceso("p1", "u", [["CPU", 10]])
    sync.semaforo_wait("recurso", p0)
    sync.semaforo_wait("recurso", p1)
    estado = sync.estado_semaforo("recurso")
    assert estado["valor"] == 0
    assert p1 in estado["cola"]
    assert procesos.estado_proceso(p1) == "BLOQUEADO"
    sync.semaforo_signal("recurso")
    assert procesos.estado_proceso(p1) in {"LISTO", "EJECUTANDO"}


def test_mutex_solo_puede_liberarlo_su_propietario(sistema_limpio, api_sincronizacion_disponible):
    sync = api_sincronizacion_disponible
    from minidc.errores import ErrorSincronizacion
    sync.crear_mutex("m")
    p0 = procesos.crear_proceso("p0", "u", [["CPU", 10]])
    p1 = procesos.crear_proceso("p1", "u", [["CPU", 10]])
    sync.mutex_lock("m", p0)
    sync.mutex_lock("m", p1)
    assert procesos.estado_proceso(p1) == "BLOQUEADO"
    try:
        sync.mutex_unlock("m", p1)
    except ErrorSincronizacion:
        pass
    else:
        raise AssertionError("Un proceso no propietario liberó el mutex")
    sync.mutex_unlock("m", p0)
    assert procesos.estado_proceso(p1) in {"LISTO", "EJECUTANDO"}


def test_detectar_y_resolver_interbloqueo(sistema_limpio, api_sincronizacion_disponible):
    sync = api_sincronizacion_disponible
    p0 = procesos.crear_proceso("p0", "u", [["CPU", 10]])
    p1 = procesos.crear_proceso("p1", "u", [["CPU", 10]])
    sync.crear_mutex("A")
    sync.crear_mutex("B")
    sync.mutex_lock("A", p0)
    sync.mutex_lock("B", p1)
    sync.mutex_lock("B", p0)
    sync.mutex_lock("A", p1)
    implicados = sync.detectar_interbloqueo()
    assert {p0, p1} <= set(implicados)
    resueltos = sync.resolver_interbloqueo()
    assert {p0, p1} <= set(resueltos)
    assert sync.detectar_interbloqueo() == []


def test_condicion_de_carrera_con_sincronizacion_no_pierde_actualizaciones(
    sistema_limpio, api_sincronizacion_disponible
):
    resultado = api_sincronizacion_disponible.demo_condicion_carrera(
        usar_sincronizacion=True, num_hilos=10, iteraciones=1000
    )
    assert resultado == 10000
