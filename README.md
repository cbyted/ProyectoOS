# NimbusDC — Simulador de Sistema Operativo (`minidc`)

Implementación en Python 3.14 de un núcleo de sistema operativo simulado para **NimbusDC**, un mini centro de datos multiusuario que ejecuta cargas de trabajo heterogéneas bajo un modelo de simulación de tiempo discreto.

**Asignatura:** Sistemas Operativos 1 (IS734) — Universidad Tecnológica de Pereira  
**Realizado por:** Sebatian Peñuela, Víctor Rojas & Juan Jose Posada
---

## Arquitectura

El paquete `minidc` separa la interfaz pública del modelo interno y de las políticas de administración:

1. **Módulos del sistema (`minidc/*.py`):** exponen las funciones requeridas para kernel, procesos, memoria, disco, archivos, sincronización y consola.
2. **Entidades (`minidc/entidades/`):** representan procesos, marcos, páginas, espacios de direcciones, nodos del sistema de archivos y usuarios.
3. **Políticas (`minidc/politicas/`):** encapsulan algoritmos como MLFQ, LRU y asignación indexada de bloques.
4. **Pruebas (`tests/`):** contienen pruebas automatizadas de comportamiento por módulo.
5. **Escenario de demostración (`examples/`):** proporciona una configuración lista para probar la consola sin tener que crear un JSON desde cero.

El kernel inicializa conjuntamente los subsistemas. En particular, `kernel.iniciar_sistema(config)` reinicia memoria, disco, sistema de archivos, procesos y sesiones de consola; esto evita que el estado de una ejecución contamine la siguiente.

---

## Requisitos

Instalar pytest:

```bash
python -m pip install pytest
```

## Iniciar la consola

Desde la carpeta raíz del repositorio:

```bash
python -m minidc
```

Por defecto se carga `examples/escenario_demo.json`, que crea los usuarios `cliente_a` y `cliente_b` y deja disponibles los programas `web`, `analitica` y `respaldo` para el comando `run`.

También se puede seleccionar otro escenario y un usuario inicial:

```bash
python -m minidc --escenario ruta/al/escenario.json
python -m minidc --escenario ruta/al/escenario.json --usuario cliente_a
```

En la consola, `help` muestra los comandos disponibles y `exit` o `quit` cierra la sesión.

## Pruebas y auditoría

Instala `pytest` con el siguiente comando:

```bash
python -m pip install pytest
```

Ejecutar únicamente las pruebas añadidas para la auditoría:

```bash
python -m pytest tests -k auditoria -v
```

Ejecutar unicamente pruebas unitarias de los modulos del proyecto:

```bash
python -m pytest tests/scenarios -v
```

Ejecutar todo, incluyendo auditoría y pruebas previas:

```bash
python -m pytest -v
```

Los escenarios JSON preparados para la auditoría están en `examples/` y se pueden cargar desde la consola con:

```bash
python -m minidc --escenario examples/escenario_auditoria_carga_web.json
python -m minidc --escenario examples/escenario_auditoria_web_integracion.json
```

---

## Estructura del repositorio

```text
ProyectoOS/
├── .venv/
├── docs/
│   ├── Diagrama_de_NimbusDC.md
│   └── Informe.pdf
├── examples/
│   ├── escenario_auditoria_carga_web.json
│   ├── escenario_auditoria_web_integracion.json
│   └── escenario_demo.json
├── minidc/
│   ├── entidades/
│   │   ├── archivo.py
│   │   ├── espacio_direcciones.py
│   │   ├── marco.py
│   │   ├── pagina.py
│   │   └── proceso.py
│   ├── politicas/
│   │   ├── asignacion_archivos.py
│   │   ├── lru.py
│   │   └── mlfq.py
│   ├── __init__.py
│   ├── __main__.py
│   ├── archivos.py
│   ├── consola.py
│   ├── disco.py
│   ├── errores.py
│   ├── kernel.py
│   ├── memoria.py
│   ├── procesos.py
│   └── sincronizacion.py
├── tests/
│   ├── scenarios/
│   │   ├── conftest.py
│   │   ├── test_console.py
│   │   ├── test_disk.py
│   │   ├── test_filesystem.py
│   │   ├── test_integration.py
│   │   ├── test_kernel_processes.py
│   │   ├── test_memory.py
│   │   └── test_synchronization.py
│   ├── archivos_test.py
│   ├── conftest.py
│   ├── consola_test.py
│   ├── disco_test.py
│   ├── kernel_test.py
│   ├── memoria_test.py
│   ├── procesos_test.py
│   ├── sincronizacion_test.py
│   ├── test_auditoria_console.py
│   ├── test_auditoria_disk.py
│   ├── test_auditoria_filesystem.py
│   ├── test_auditoria_integration.py
│   ├── test_auditoria_kernel_processes.py
│   ├── test_auditoria_memory.py
│   └── test_auditoria_synchronization.py
├── .gitignore
└── README.md
```