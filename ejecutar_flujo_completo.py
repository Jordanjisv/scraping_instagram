"""Pipeline en un comando: opcionalmente actualiza enlaces, visita el lote y enriquece.
Guardar en la raíz del proyecto. Requiere autorización de uso del sitio.
"""
import argparse
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent


def ejecutar(script: str, argumentos=()):
    ruta = BASE / script
    if not ruta.exists():
        raise FileNotFoundError(f"Falta {ruta}")
    print(f"\n=== EJECUTANDO {script} ===", flush=True)
    subprocess.run([sys.executable, str(ruta), *argumentos], cwd=BASE, check=True)


def main():
    parser = argparse.ArgumentParser(description="Flujo autorizado de extracción y análisis")
    parser.add_argument("--actualizar-perfil", action="store_true", help="Obtiene perfil público visible en HTML")
    parser.add_argument("--actualizar-enlaces", action="store_true", help="Obtiene enlaces nuevamente antes del procesamiento")
    parser.add_argument("--limite", type=int, default=3, help="Cantidad máxima de publicaciones nuevas, 0=todas")
    args = parser.parse_args()
    if args.limite < 0:
        parser.error("--limite debe ser >= 0")

    if args.actualizar_perfil:
        ejecutar("inspeccionar_perfil.py")

    if args.actualizar_enlaces:
        candidato = (
            "inspeccionar_sesion_actualizado.py"
            if (BASE / "inspeccionar_sesion_actualizado.py").exists()
            else "inspeccionar_sesion.py"
        )
        ejecutar(candidato)

    ejecutar("procesar_publicaciones_lote.py", ["--limite", str(args.limite)])

    ejecutar("consolidar_resultados_lote.py")

    print("\nFLUJO FINALIZADO. Revisa resultados/ y el dashboard.")


if __name__ == "__main__":
    main()
