"""Punto de entrada: python main.py. No carga datos automaticamente."""
from pathlib import Path
import subprocess
import sys
from scouts_menu_utils import run_menu

BASE_DIR = Path(__file__).resolve().parent


def run_script(folder_name, script_name, arguments=()):
    script_path = BASE_DIR / folder_name / script_name
    if not script_path.is_file():
        print(f"No se encontro el archivo: {script_path}")
        return False
    command = [sys.executable, "-B", "-X", "utf8", str(script_path), *arguments]
    print(f"\n--- {folder_name}/{script_name} ---", flush=True)
    try:
        result = subprocess.run(command, cwd=str(script_path.parent), check=False)
    except OSError as exc:
        print(f"No se pudo iniciar el programa: {exc}")
        return False
    if result.returncode != 0:
        print(f"La operacion de {folder_name} fallo (codigo {result.returncode}).")
        return False
    return True


def populate(selected):
    scripts = {
        "Mongo": ("Mongo", "mongo_setup.py"),
        "Cassandra": ("Cassandra", "populate.py"),
        "Dgraph": ("Dgraph", "populate.py"),
    }
    print("\nSe usaran los JSON de data/ y las conexiones configuradas en cada base.")
    if "Mongo" in selected:
        print("MongoDB: agrega o actualiza documentos por ID; no elimina registros sobrantes.")
    destructive = [name for name in selected if name in ("Cassandra", "Dgraph")]
    if destructive:
        print("ATENCION: los cargadores existentes reinician los datos de " + ", ".join(destructive) + ".")
        print("Cassandra reinicia el keyspace scouts; Dgraph vacia la instancia configurada.")
        answer = input("Escribe REINICIAR para continuar, o Enter para cancelar: ").strip()
        if answer != "REINICIAR":
            print("Carga cancelada.")
            return False
    for name in selected:
        if not run_script(*scripts[name]):
            print("La secuencia se detuvo. Las cargas anteriores que terminaron no se deshacen.")
            return False
    print("Carga terminada para las bases seleccionadas.")
    return True


def population_menu():
    actions = {
        "1": ("MongoDB: agregar/actualizar desde JSON", lambda: populate(["Mongo"])),
        "2": ("Cassandra: reiniciar y cargar desde JSON", lambda: populate(["Cassandra"])),
        "3": ("Dgraph: reiniciar y cargar desde JSON", lambda: populate(["Dgraph"])),
        "4": ("Cargar las tres bases", lambda: populate(["Mongo", "Cassandra", "Dgraph"])),
    }
    run_menu("CARGA DE DATOS", actions)


def main():
    actions = {
        "1": ("MongoDB: elegir consulta", lambda: run_script("Mongo", "main.py", ["--menu"])),
        "2": ("Cassandra: elegir consulta", lambda: run_script("Cassandra", "main.py", ["--menu"])),
        "3": ("Dgraph: elegir consulta", lambda: run_script("Dgraph", "main.py", ["--menu"])),
        "4": ("Carga de datos", population_menu),
    }
    run_menu("SCOUTS - BASES DE DATOS", actions, exit_label="Salir")


if __name__ == "__main__":
    main()
