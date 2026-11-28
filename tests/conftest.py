"""Fixtures de la auditoría independiente de caja negra.

Todas las interacciones se realizan mediante funciones públicas de NimbusDC.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from minidc import kernel


CONFIG = {
    "num_cpus": 2,
    "marcos_fisicos": 16,
    "tam_pagina": 256,
    "bloques_disco": 200,
    "tam_bloque": 512,
    "cache_bloques": 8,
}


@pytest.fixture
def sistema_limpio():
    """Inicia una simulación nueva con valores conocidos."""
    kernel.iniciar_sistema(dict(CONFIG))
    return dict(CONFIG)


@pytest.fixture

def crear_escenario(tmp_path: Path):
    """Escribe y carga un escenario JSON temporal y reproducible."""
    def _crear(*, config=None, usuarios=(), catalogo=None, llegadas=(), semaforos=None):
        datos = {
            "config": dict(config or CONFIG),
            "usuarios": list(usuarios),
            "catalogo": dict(catalogo or {}),
            "llegadas": list(llegadas),
            "semaforos": dict(semaforos or {}),
        }
        ruta = tmp_path / "escenario_auditoria.json"
        ruta.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
        kernel.cargar_escenario(str(ruta))
        return datos
    return _crear


@pytest.fixture
def api_sincronizacion_disponible():
    """Omite pruebas dependientes si el módulo no expone la API requerida."""
    from minidc import sincronizacion

    requeridas = (
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
    )
    faltantes = [nombre for nombre in requeridas if not callable(getattr(sincronizacion, nombre, None))]
    if faltantes:
        pytest.skip("API de sincronización no disponible: " + ", ".join(faltantes))
    return sincronizacion
