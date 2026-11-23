from pathlib import Path
import subprocess
import sys

BASE_DIR = Path(__file__).resolve().parent


def run_script(folder_name: str, script_name: str):
    module_dir = BASE_DIR / folder_name
    script_path = module_dir / script_name
    if not script_path.exists():
        print(f"[AVISO] No se encontró {script_path}")
        return
    print(f"\n--- Ejecutando {folder_name}/{script_name} ---")
    subprocess.run([sys.executable, str(script_path)], cwd=str(module_dir), check=False)


def show_menu():
    print("\n=== SCOUTS - MENÚ DE BASES DE DATOS ===")
    print("1. MongoDB: Setup / Poblar (mongo_setup.py)")
    print("2. MongoDB: Consultas (main.py)")
    print("3. Cassandra: Poblar (populate.py)")
    print("4. Cassandra: Consultas (main.py)")
    print("5. Dgraph: Poblar (populate.py)")
    print("6. Dgraph: Consultas (main.py)")
    print("7. Poblar las 3 bases en orden")
    print("0. Salir")


def main():
    while True:
        show_menu()
        choice = input("Selecciona una opción: ").strip()

        if choice == "1":
            run_script("Mongo", "mongo_setup.py")
        elif choice == "2":
            run_script("Mongo", "main.py")
        elif choice == "3":
            run_script("Cassandra", "populate.py")
        elif choice == "4":
            run_script("Cassandra", "main.py")
        elif choice == "5":
            run_script("Dgraph", "populate.py")
        elif choice == "6":
            run_script("Dgraph", "main.py")
        elif choice == "7":
            run_script("Mongo", "mongo_setup.py")
            run_script("Cassandra", "populate.py")
            run_script("Dgraph", "populate.py")
        elif choice == "0":
            print("Saliendo...")
            break
        else:
            print("[ERROR] Opción no válida.")


if __name__ == "__main__":
    main()