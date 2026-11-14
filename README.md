# NimbusDC — Simulador de Sistema Operativo (`minidc`)

Implementación en Python de un núcleo de sistema operativo simulado para **NimbusDC**, un mini centro de datos multiusuario que ejecuta cargas de trabajo heterogéneas bajo un modelo de simulación de tiempo discreto.

**Asignatura:** Sistemas Operativos 1 (IS734) — Universidad Tecnológica de Pereira  
**Realizado por:** Sebatian Peñuela, Víctor Rojas & Juan Jose Posada

---

## Arquitectura y Diseño

El paquete `minidc` sigue una separación por capas diseñada para desacoplar las estructuras de datos y los algoritmos de la interfaz requerida por el sistema y las pruebas automatizadas:

1. **API Pública / Fachada (`minidc/*.py`):**  
   Los módulos ubicados en la raíz de `minidc/` exponen exactamente las firmas, funciones y excepciones requeridas por la especificación del proyecto (`from minidc import kernel, procesos, ...`). Actúan como punto de entrada único, validan parámetros, gestionan el estado global de cada subsistema y delegan la lógica interna.
2. **Entidades del Dominio (`minidc/entidades/`):**  
   Contiene las clases y estructuras de datos que modelan los elementos fundamentales del sistema operativo: bloques de control de procesos (PCB), hilos (TCB), tablas de páginas, marcos físicos, solicitudes de E/S, inodos/archivos, usuarios y primitivas de sincronización.
3. **Políticas y Algoritmos (`minidc/politicas/`):**  
   Encapsula de forma modular los algoritmos de toma de decisiones del SO (planificación de CPU, reemplazo de páginas, planificación del cabezal de disco y asignación de bloques de archivos). Esto permite intercambiar estrategias y comparar métricas sin alterar la API pública ni las entidades.

---

## Estructura del Repositorio

```text
ProyectoOS/
├── informe/                 
│   └── example.txt
├── minidc/                  
│   ├── entidades/           
│   ├── politicas/           
│   ├── __init__.py
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
