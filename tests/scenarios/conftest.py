"""Fixtures comunes para la auditoría de caja negra de NimbusDC.

Solo se utilizan funciones públicas documentadas. Ninguna prueba lee
atributos privados ni inspecciona el código de la implementación.
"""

from __future__ import annotations

import json
import uuid

import pytest

from minidc import archivos, kernel, procesos


CONFIG_BASE = {
    "num_cpus": 2,
    "marcos_fisicos": 16,
    "tam_pagina": 256,
    "bloques_disco": 200,
    "tam_bloque": 512,
    "cache_bloques": 8,
}


@pytest.fixture(autouse=True)
def reiniciar_sistema():
    """Deja un sistema limpio antes y después de cada prueba."""
    kernel.iniciar_sistema(dict(CONFIG_BASE))
    yield
    kernel.iniciar_sistema(dict(CONFIG_BASE))


@pytest.fixture
def config():
    return dict(CONFIG_BASE)


@pytest.fixture
def cargar_escenario(tmp_path):
    """Carga un escenario JSON construido por la prueba."""

    def _cargar(config=None, usuarios=None, catalogo=None, llegadas=None, semaforos=None):
        datos = {
            "config": dict(config or CONFIG_BASE),
            "usuarios": list(usuarios or []),
            "semaforos": dict(semaforos or {}),
            "catalogo": dict(catalogo or {}),
            "llegadas": list(llegadas or []),
        }
        ruta = tmp_path / f"escenario_{uuid.uuid4().hex}.json"
        ruta.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
        kernel.cargar_escenario(str(ruta))
        return datos

    return _cargar


@pytest.fixture
def usuarios_base():
    """Crea tres usuarios con dos grupos distintos."""
    archivos.crear_usuario("alice", "g1")
    archivos.crear_usuario("bob", "g1")
    archivos.crear_usuario("carol", "g2")


def pids_unicos():
    """PIDs observables sin depender de posibles duplicados del listado."""
    return sorted({p["pid"] for p in procesos.listar_procesos()})


@pytest.fixture
def pids():
    return pids_unicos
