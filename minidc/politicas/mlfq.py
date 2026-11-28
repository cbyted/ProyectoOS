from collections import deque
from ..entidades.proceso import Proceso
from ..errores import ErrorSistema

"""
MLFQ de 3 colas con envejecimiento.
  Nivel 0 y 1: Round Robin (quantums[0], quantums[1]).
  Nivel 2: FCFS.
Requisitos: RP1 (respuesta web <= 10 ticks), RP2 (espera consecutiva <= 150),
RP3 (utilización CPU >= 85 %).

Convención de prioridad: un valor MENOR es MÁS urgente (cámbialo en _encolar
si el escenario usa la convención contraria).
"""


class MLFQ:
    ENVEJECIMIENTO = 50  # ticks esperando para subir un nivel
    TICKS_FALLO_PAGINA = 5

    def __init__(self, quantums: list[int], num_cpus: int) -> None:
        self.num_colas = 3
        self.num_cpus = num_cpus
        self.quantums = quantums
        self.espera_maxima = 150
        self.margen_emergencia = 120

        self.colas = [deque() for _ in range(self.num_colas)]
        self.terminados: deque[Proceso] = deque()
        self.bloqueados: list[Proceso] = []

        self.proceso_actual = [None] * num_cpus
        self.nivel_actual = [None] * num_cpus
        self.quantum_restante = [0] * num_cpus
        self.ultimo_pid = [None] * num_cpus

        self.suspendidos: list[Proceso] = []

        # Métricas globales
        self.ticks_ocupados = [0] * num_cpus
        self.ticks_totales = 0
        self.cambios_contexto = 0
        self.espera_max_consecutiva = 0

        # Los hooks conectan con memoria, disco y sincronización sin
        # importaciones circulares. Los asigna procesos._configurar.
        #   "ES": fn(proceso, bloque)        -> encola solicitud de disco
        #   "MEM": fn(proceso, direccion)    -> True si hubo fallo de página
        #   "WAIT"/"SIGNAL": fn(proceso, nombre) -> False si queda bloqueado
        #   "LIBERAR": fn(proceso)           -> libera memoria, semáforos, mutex
        self.hooks = {}
        self.verbose = False

    # ------------------------------------------------------------------
    # Colas
    # ------------------------------------------------------------------
    def _encolar(self, nivel, proceso, frente=False, por_prioridad=False):
        proceso.nivel = nivel
        cola = self.colas[nivel]
        if frente:
            cola.appendleft(proceso)
        elif por_prioridad:
            pos = len(cola)
            for i, actual in enumerate(cola):
                if proceso.prioridad < actual.prioridad:
                    pos = i
                    break
            cola.insert(pos, proceso)
        else:
            cola.append(proceso)

    def nuevo(self, proceso: Proceso) -> None:
        self._encolar(0, proceso, por_prioridad=True)

    # ------------------------------------------------------------------
    # CPU
    # ------------------------------------------------------------------
    def _cpu_libre(self):
        return next((c for c, p in enumerate(self.proceso_actual) if p is None), None)

    def _liberar_cpu(self, cpu):
        self.proceso_actual[cpu] = None
        self.nivel_actual[cpu] = None
        self.quantum_restante[cpu] = 0

    def _despachar(self, cpu, proceso, reloj):
        proceso.cambiar_estado("EJECUTANDO")
        self.proceso_actual[cpu] = proceso
        self.nivel_actual[cpu] = proceso.nivel
        if proceso.nivel < self.num_colas - 1:
            self.quantum_restante[cpu] = self.quantums[proceso.nivel]
        else:
            self.quantum_restante[cpu] = 0  # FCFS

        self.espera_max_consecutiva = max(
            self.espera_max_consecutiva, proceso.espera_consecutiva
        )
        proceso.espera_consecutiva = 0
        if proceso.tiempo_primera_ejecucion is None:
            proceso.tiempo_primera_ejecucion = reloj
        if self.ultimo_pid[cpu] != proceso.pid:
            self.cambios_contexto += 1
            self.ultimo_pid[cpu] = proceso.pid

    def _elegir(self, cpu, reloj) -> bool:
        for cola in self.colas:
            if cola:
                self._despachar(cpu, cola.popleft(), reloj)
                return True
        return False

    def _desalojar(self, cpu):
        """Saca el proceso de la CPU y lo deja al frente de su misma cola."""
        proceso = self.proceso_actual[cpu]
        proceso.cambiar_estado("LISTO")
        self._encolar(proceso.nivel, proceso, frente=True)
        self._liberar_cpu(cpu)

    # ------------------------------------------------------------------
    # Bloqueo y desbloqueo
    # ------------------------------------------------------------------
    def _bloquear(self, cpu, proceso, motivo, hasta=None):
        proceso.cambiar_estado("BLOQUEADO")
        proceso.motivo_bloqueo = motivo
        proceso.bloqueado_hasta = hasta
        self.bloqueados.append(proceso)
        self._liberar_cpu(cpu)

    def desbloquear(self, pid: int) -> bool:
        """Interrupción de E/S terminada (o signal): el proceso pasa a LISTO."""
        for proceso in self.bloqueados:
            if proceso.pid == pid:
                self.bloqueados.remove(proceso)
                proceso.motivo_bloqueo = None
                proceso.bloqueado_hasta = None
                proceso.cambiar_estado("LISTO")
                proceso.espera_consecutiva = 0
                self._encolar(max(0, proceso.nivel - 1), proceso)
                return True
        return False

    def _despertar_por_tiempo(self, reloj):
        for proceso in list(self.bloqueados):
            if proceso.bloqueado_hasta is not None and reloj >= proceso.bloqueado_hasta:
                self.desbloquear(proceso.pid)

    def suspender(self, proceso: Proceso) -> bool:
        """Swap-out por hiperpaginación. No suspende a quien espera disco o semáforo."""
        if proceso.estado in ("NUEVO", "TERMINADO") or proceso.suspendido:
            return False
        if proceso.motivo_bloqueo in ("DISCO", "SEMAFORO"):
            return False
        self.retirar(proceso)
        proceso.suspendido = True
        proceso.cambiar_estado("BLOQUEADO")
        proceso.motivo_bloqueo = "SUSPENDIDO"
        proceso.bloqueado_hasta = None
        self.suspendidos.append(proceso)
        return True

    def reanudar(self, proceso: Proceso) -> bool:
        if proceso not in self.suspendidos:
            return False
        self.suspendidos.remove(proceso)
        proceso.suspendido = False
        proceso.motivo_bloqueo = None
        proceso.cambiar_estado("LISTO")
        proceso.espera_consecutiva = 0
        self._encolar(proceso.nivel, proceso)
        return True

    # ------------------------------------------------------------------
    # Fin de proceso
    # ------------------------------------------------------------------
    def retirar(self, proceso):
        if proceso in self.suspendidos:
            self.suspendidos.remove(proceso)

        for cpu, actual in enumerate(self.proceso_actual):
            if actual is proceso:
                self._liberar_cpu(cpu)
        for cola in self.colas:
            if proceso in cola:
                cola.remove(proceso)
        if proceso in self.bloqueados:
            self.bloqueados.remove(proceso)

    def finalizar(self, proceso, reloj):
        if proceso.estado == "TERMINADO":
            return
        self.retirar(proceso)
        proceso.cambiar_estado("TERMINADO")
        proceso.motivo_bloqueo = None
        proceso.bloqueado_hasta = None
        proceso.tiempo_finalizacion = reloj
        proceso.tiempo_retorno = reloj - proceso.tiempo_llegada
        self.terminados.append(proceso)
        liberar = self.hooks.get("LIBERAR")
        if liberar:
            liberar(proceso)

    # ------------------------------------------------------------------
    # Ejecución de instrucciones
    # ------------------------------------------------------------------
    @staticmethod
    def _avanzar_instruccion(proceso):
        proceso.indice_instruccion += 1
        proceso.restante_instr = None

    def _preparar(self, cpu, reloj) -> bool:
        """Ejecuta instrucciones instantáneas (ES, MEM, WAIT, SIGNAL).

        True: el proceso sigue en la CPU y está listo para gastar 1 tick.
        False: el proceso salió de la CPU (bloqueado o terminado).
        """
        proceso = self.proceso_actual[cpu]
        try:
            while proceso.indice_instruccion < len(proceso.programa):
                tipo, valor = proceso.programa[proceso.indice_instruccion]

                if tipo == "CPU":
                    if proceso.restante_instr is None:
                        proceso.restante_instr = valor
                    if proceso.restante_instr > 0:
                        return True
                    self._avanzar_instruccion(proceso)
                    continue

                self._avanzar_instruccion(proceso)
                hook = self.hooks.get(tipo)

                if tipo == "ES":
                    if hook:
                        hook(proceso, valor)
                    self._bloquear(cpu, proceso, "DISCO")
                    return False

                if tipo == "MEM":
                    if hook and hook(proceso, valor):
                        self._bloquear(
                            cpu,
                            proceso,
                            "FALLO_PAGINA",
                            reloj + self.TICKS_FALLO_PAGINA,
                        )
                        return False

                elif tipo in ("WAIT", "SIGNAL"):
                    if hook and hook(proceso, valor) is False:
                        self._bloquear(cpu, proceso, "SEMAFORO")
                        return False
        except ErrorSistema:
            # Acceso inválido: Matar proceso
            self.finalizar(proceso, reloj)
            return False

        self.finalizar(proceso, reloj)
        return False

    def _consumir_tick(self, cpu, reloj):
        proceso = self.proceso_actual[cpu]
        proceso.restante_instr -= 1
        proceso.rafaga_cpu -= 1
        proceso.cpu_usada += 1
        self.ticks_ocupados[cpu] += 1

        if proceso.restante_instr == 0:
            self._avanzar_instruccion(proceso)
        if proceso.indice_instruccion >= len(proceso.programa):
            self.finalizar(proceso, reloj)
            return

        nivel = self.nivel_actual[cpu]
        if nivel < self.num_colas - 1:
            self.quantum_restante[cpu] -= 1
            if self.quantum_restante[cpu] == 0:
                # Quantum agotado: baja de nivel.
                proceso.cambiar_estado("LISTO")
                self._encolar(nivel + 1, proceso)
                self._liberar_cpu(cpu)

    def _ejecutar_cpu(self, cpu, reloj):
        while True:
            if self.proceso_actual[cpu] is None and not self._elegir(cpu, reloj):
                return  # CPU ociosa
            if not self._preparar(cpu, reloj):
                continue  # el proceso se fue; otro puede usar el tick
            self._consumir_tick(cpu, reloj)
            return

    # ------------------------------------------------------------------
    # Expropiación y envejecimiento
    # ------------------------------------------------------------------
    def _expropiar_por_nivel0(self):
        """Los procesos de nivel 0 (llegadas/interactivos) expropian a niveles bajos."""
        libres = sum(p is None for p in self.proceso_actual)
        while len(self.colas[0]) > libres:
            candidatas = [
                c
                for c, p in enumerate(self.proceso_actual)
                if p is not None and self.nivel_actual[c] > 0
            ]
            if not candidatas:
                return
            self._desalojar(max(candidatas, key=lambda c: self.nivel_actual[c]))
            libres += 1

    def _atender_inanicion(self, reloj):
        """Garantía dura de RP2: nadie supera `espera_maxima` ticks esperando."""
        urgentes = sorted(
            (
                p
                for cola in self.colas
                for p in cola
                if p.espera_consecutiva >= self.margen_emergencia
            ),
            key=lambda p: -p.espera_consecutiva,
        )
        protegidas = set()
        for proceso in urgentes:
            cpu = self._cpu_libre()
            if cpu is None:
                candidatas = [
                    c
                    for c, p in enumerate(self.proceso_actual)
                    if p is not None and c not in protegidas
                ]
                if not candidatas:
                    break
                cpu = max(candidatas, key=lambda c: self.nivel_actual[c])
                self._desalojar(cpu)
            self.colas[proceso.nivel].remove(proceso)
            self._despachar(cpu, proceso, reloj)
            protegidas.add(cpu)

    def _actualizar_metricas(self):
        self.ticks_totales += 1
        for nivel, cola in enumerate(self.colas):
            for proceso in list(cola):
                proceso.tiempo_espera += 1
                proceso.espera_consecutiva += 1
                self.espera_max_consecutiva = max(
                    self.espera_max_consecutiva, proceso.espera_consecutiva
                )
                # Envejecimiento: sube un nivel cada ENVEJECIMIENTO ticks.
                if nivel > 0 and proceso.espera_consecutiva % self.ENVEJECIMIENTO == 0:
                    cola.remove(proceso)
                    self._encolar(nivel - 1, proceso)

    # ------------------------------------------------------------------
    # Tick
    # ------------------------------------------------------------------
    def ejecutar_tick(self, procesos: list[Proceso], reloj_actual: int) -> None:
        for proceso in procesos:
            if proceso.estado == "NUEVO" and proceso.tiempo_llegada <= reloj_actual:
                proceso.cambiar_estado("LISTO")
                self.nuevo(proceso)

        self._despertar_por_tiempo(reloj_actual)
        self._atender_inanicion(reloj_actual)
        self._expropiar_por_nivel0()

        for cpu in range(self.num_cpus):
            self._ejecutar_cpu(cpu, reloj_actual)

        self._actualizar_metricas()
        if self.verbose:
            self.mostrar_resultado(reloj_actual)

    # ------------------------------------------------------------------
    # Métricas
    # ------------------------------------------------------------------
    def metricas(self, procesos: list[Proceso]) -> dict:
        admitidos = [p for p in procesos if p.estado != "NUEVO"]
        iniciados = [p for p in procesos if p.tiempo_primera_ejecucion is not None]
        terminados = list(self.terminados)

        def promedio(valores):
            valores = list(valores)
            return sum(valores) / len(valores) if valores else 0.0

        espera_max = max(
            [self.espera_max_consecutiva]
            + [p.espera_consecutiva for cola in self.colas for p in cola]
        )
        capacidad = self.ticks_totales * self.num_cpus
        return {
            "espera_promedio": promedio(p.tiempo_espera for p in admitidos),
            "respuesta_promedio": promedio(
                p.tiempo_primera_ejecucion - p.tiempo_llegada for p in iniciados
            ),
            "retorno_promedio": promedio(p.tiempo_retorno for p in terminados),
            "espera_maxima": espera_max,
            "utilizacion_cpu": (sum(self.ticks_ocupados) / capacidad)
            if capacidad
            else 0.0,
            "cambios_contexto": self.cambios_contexto,
            "procesos_terminados": len(terminados),
        }

    def mostrar_resultado(self, reloj_actual: int) -> None:
        print(f"\nRELOJ ACTUAL: {reloj_actual}")
        for cpu, proceso in enumerate(self.proceso_actual):
            if proceso is None:
                print(f"CPU {cpu}: libre")
            else:
                print(
                    f"CPU {cpu}: {proceso.nombre}, nivel: {self.nivel_actual[cpu]}, "
                    f"cpu_usada: {proceso.cpu_usada}"
                )
        for nivel, cola in enumerate(self.colas):
            print(f"Nivel {nivel}: [{', '.join(p.nombre for p in cola)}]")
        print(f"Bloqueados: [{', '.join(p.nombre for p in self.bloqueados)}]")
