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

## Ejecutar las pruebas

Desde la carpeta raíz del repositorio:

```bash
python -m pytest
```

---

## Estructura del repositorio

```text
ProyectoOS/
├── docs/
│   ├── Diagrama_de_NimbusDC.md
│   └── Informe.pdf
├── examples/
│   └── escenario_demo.json
├── minidc/
│   ├── entidades/
│   ├── politicas/
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
│   ├── archivos_test.py
│   ├── consola_test.py
│   ├── disco_test.py
│   ├── kernel_test.py
│   ├── memoria_test.py
│   ├── procesos_test.py
│   └── sincronizacion_test.py
└── README.md
```