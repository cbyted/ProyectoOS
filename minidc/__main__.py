"""Punto de entrada interactivo: ejecutar con ``python -m minidc``."""

import argparse
from pathlib import Path

from . import consola, kernel


_RUTA_ESCENARIO_DEMO = (
    Path(__file__).resolve().parent.parent / "examples" / "escenario_demo.json"
)

_AYUDA = """Comandos disponibles

Archivos:
  pwd | cd [RUTA] | ls [-l] [RUTA] | mkdir RUTA | touch ARCHIVO
  cat ARCHIVO | echo "texto" > ARCHIVO | echo "texto" >> ARCHIVO
  rm RUTA | rm -r RUTA | chmod MODO RUTA | ln -s DESTINO ENLACE | tree [RUTA]

Procesos y recursos:
  ps | run NOMBRE | kill PID | top | tick N
  free | df | whoami

Sesión:
  help | exit | quit

En el escenario de demostración están disponibles: web, analitica y respaldo.
"""


def _argumentos(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m minidc",
        description="Inicia la consola interactiva del sistema simulado NimbusDC.",
    )
    parser.add_argument(
        "--escenario",
        type=Path,
        help="ruta a un escenario JSON propio; por defecto se usa el escenario de demostración",
    )
    parser.add_argument(
        "--usuario",
        default="admin",
        help="usuario con el que inicia la consola (por defecto: admin)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    argumentos = _argumentos(argv)
    ruta_escenario = argumentos.escenario or _RUTA_ESCENARIO_DEMO

    try:
        kernel.cargar_escenario(str(ruta_escenario))
    except (OSError, ValueError) as error:
        print(f"No se pudo iniciar NimbusDC: {error}")
        return 1

    print("NimbusDC - consola del sistema simulado")
    print(f"Escenario: {ruta_escenario}")
    print(f"Usuario: {argumentos.usuario}")
    print("Escriba 'help' para consultar los comandos o 'exit' para salir.\n")

    try:
        while True:
            ruta_actual = consola.directorio_actual(argumentos.usuario)
            try:
                linea = input(f"{argumentos.usuario}@NimbusDC:{ruta_actual}$ ")
            except EOFError:
                print()
                break

            comando = linea.strip()
            if comando in ("exit", "quit"):
                break
            if comando == "help":
                print(_AYUDA)
                continue
            if not comando:
                continue

            resultado = consola.ejecutar_comando(comando, argumentos.usuario)
            if resultado:
                print(resultado)
    except KeyboardInterrupt:
        print("\nCierre solicitado por el usuario.")

    resumen = kernel.apagar_sistema()
    print(
        "NimbusDC finalizado. "
        f"Reloj: {resumen['reloj']} | "
        f"Procesos activos: {resumen['procesos_activos']} | "
        f"Marcos libres: {resumen['marcos_libres']} | "
        f"Bloques libres: {resumen['bloques_libres']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
