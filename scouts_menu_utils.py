"""Entrada y salida compartidas por los menus de Scouts (solo biblioteca estandar)."""
import json
from datetime import date, datetime
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent


def season_default():
    try:
        data = json.loads((PROJECT_DIR / "data" / "teams_and_competitions.json").read_text(encoding="utf-8-sig"))
        return str(data["competitions"][0]["season"])
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        return "2026-2027"


def ask_text(label, default=""):
    suffix = f" [{default}]" if default else ""
    while True:
        value = input(f"{label}{suffix}: ").strip()
        if value:
            return value
        if default:
            return str(default)
        print("Escribe un valor.")


def ask_int(label, default, minimum=0, maximum=None):
    while True:
        value = input(f"{label} [{default}]: ").strip()
        try:
            number = int(value) if value else int(default)
        except ValueError:
            print("Escribe un numero entero.")
            continue
        if number < minimum or (maximum is not None and number > maximum):
            limit = f" y {maximum}" if maximum is not None else ""
            print(f"El valor debe estar entre {minimum}{limit}." if limit else f"El minimo es {minimum}.")
            continue
        return number


def show_json(title, result):
    print(f"\n=== {title} ===")
    if result is None or result == []:
        print("Sin resultados para esos parametros.")
    def serialize(value):
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        return str(value)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=serialize))


def run_menu(title, actions, exit_label="Volver"):
    while True:
        print(f"\n=== {title} ===")
        for key, (label, _) in actions.items():
            print(f"{key}. {label}")
        print(f"0. {exit_label}")
        try:
            choice = input("Selecciona una opcion: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if choice == "0":
            return
        if choice not in actions:
            print("Opcion no valida.")
            continue
        try:
            actions[choice][1]()
        except EOFError:
            print("\nEntrada finalizada.")
            return
        except KeyboardInterrupt:
            print("\nOperacion interrumpida. Regresas al menu.")
        except Exception as exc:
            print(f"\nNo se pudo completar la operacion: {exc}")
            print("Si es un error de conexion, comprueba que la base este iniciada.")
