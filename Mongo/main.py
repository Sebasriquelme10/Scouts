import argparse
from pathlib import Path
import sys

# Permite ejecutar este archivo directamente y usar las utilidades de la raiz.
sys.path.append(str(Path(__file__).resolve().parents[1]))
from scouts_menu_utils import ask_text, ask_int, run_menu, show_json, season_default

from datetime import datetime, timedelta, timezone
from connect import get_mongo_db


def get_team_roster(db, team_id: str, season: str = None):
    query = {"team_id": team_id}
    if season:
        query["season"] = season
    return list(db.teams.find(query, {"_id": 0}))


def search_players(db, position: str, status: str = "Available", min_age: int = 16, max_age: int = 40):
    now = datetime.now(timezone.utc)
    max_birth = now.replace(year=now.year - min_age)
    min_birth = now.replace(year=now.year - max_age)

    query = {
        "positions": position,
        "status": status,
        "birth_date": {"$gte": min_birth, "$lte": max_birth},
    }
    return list(db.players.find(query, {"_id": 0}))


def get_expiring_contracts(db, days_ahead: int = 30):
    now = datetime.now(timezone.utc)
    limit = now + timedelta(days=days_ahead)

    pipeline = [
        {"$unwind": "$contracts"},
        {
            "$match": {
                "contracts.active": True,
                "contracts.contract_end": {"$gte": now, "$lte": limit},
            }
        },
        {"$sort": {"contracts.contract_end": 1}},
        {
            "$project": {
                "_id": 0,
                "player_id": 1,
                "name": 1,
                "team_id": "$contracts.team_id",
                "salary_per_year": "$contracts.salary_per_year",
                "contract_end": "$contracts.contract_end",
            }
        },
    ]
    return list(db.players.aggregate(pipeline))


def agg_top_scorers(db, season: str, limit: int = 10):
    pipeline = [
        {"$match": {"season": season}},
        {
            "$lookup": {
                "from": "players",
                "localField": "player_id",
                "foreignField": "player_id",
                "as": "player_info",
            }
        },
        {"$unwind": "$player_info"},
        {
            "$project": {
                "_id": 0,
                "player_id": 1,
                "name": "$player_info.name",
                "positions": "$player_info.positions",
                "games_played": 1,
                "goals": 1,
                "average_minutes": 1,
            }
        },
        {"$sort": {"goals": -1}},
        {"$limit": limit},
    ]
    return list(db.player_season_stats.aggregate(pipeline))


def agg_team_payroll(db):
    pipeline = [
        {"$unwind": "$contracts"},
        {"$match": {"contracts.active": True}},
        {
            "$group": {
                "_id": "$contracts.team_id",
                "active_players": {"$sum": 1},
                "total_annual_salary": {"$sum": "$contracts.salary_per_year"},
                "avg_salary": {"$avg": "$contracts.salary_per_year"},
            }
        },
        {"$sort": {"total_annual_salary": -1}},
    ]
    return list(db.players.aggregate(pipeline))


def _fmt_date(dt) -> str:
    if hasattr(dt, "strftime"):
        return dt.strftime("%Y-%m-%d")
    return str(dt)[:10]


def print_search_players(results: list[dict], title: str = "Búsqueda de jugadores"):
    print(f"\n {title} ({len(results)}) ")
    if not results:
        print("  No se encontraron jugadores con esos criterios.")
        return
    for p in results:
        pos = ", ".join(p.get("positions", []))
        traits = p.get("physical_traits", {})
        print(
            f"  • [{p.get('player_id')}] {p.get('name')} | Pos: {pos} | Estado: "
            f"{p.get('status')} | Nac: {_fmt_date(p.get('birth_date'))} | "
            f"{traits.get('height_cm', '-')} cm / {traits.get('weight_kg', '-')} kg"
        )


def print_expiring_contracts(results: list[dict], days_ahead: int):
    print(f"\n Contratos activos por vencer en {days_ahead} días ({len(results)})")
    if not results:
        print("  No hay contratos por vencer en ese rango.")
        return
    for c in results:
        salary = f"${c.get('salary_per_year', 0):,.0f}"
        print(
            f"  • {c.get('name')} ({c.get('player_id')}) | Equipo: "
            f"{c.get('team_id')} | Vence: {_fmt_date(c.get('contract_end'))} | "
            f"Salario anual: {salary}"
        )


def print_top_scorers(results: list[dict], season: str):
    print(f"\nTop Goleadores — Temporada {season} ")
    if not results:
        print("  Sin estadísticas registradas para esta temporada.")
        return
    for idx, r in enumerate(results, start=1):
        pos = ", ".join(r.get("positions", []))
        print(
            f"  {idx}. {r.get('name')} ({r.get('player_id')}) [{pos}] -> Goles: "
            f"{r.get('goals')} | PJ: {r.get('games_played')} | Prom. min: "
            f"{r.get('average_minutes')}"
        )


def print_team_roster(results: list[dict], team_id: str, season: str = None):
    label = f"{team_id} ({season})" if season else team_id
    print(f"\n--- Plantilla de Equipo — {label} ({len(results)}) ---")
    if not results:
        print("  No se encontraron registros de plantilla.")
        return
    for t in results:
        print(
            f"  • [{t.get('team_id')}] {t.get('team_name', t.get('team_id'))} | "
            f"Temporada: {t.get('season', '-')} | DT: {t.get('head_coach', '-')}"
        )


def print_team_payroll(results: list[dict]):
    print("\n Masa Salarial Activa por Equipo ")
    if not results:
        print("  No hay contratos activos registrados.")
        return
    for row in results:
        total = f"${row.get('total_annual_salary', 0):,.0f}"
        avg = f"${row.get('avg_salary', 0):,.0f}"
        print(
            f"  • Equipo: {row.get('_id')} | Jugadores activos: {row.get('active_players')} | "
            f"Total anual: {total} | Promedio: {avg}"
        )



from mongo_setup import get_match_box_score, get_player_season_stats, get_standings

TITLES = {
    "1": "Plantilla de un equipo (1.2)",
    "2": "Resumen de un partido (1.3)",
    "3": "Estadisticas de un jugador por temporada (1.4)",
    "4": "Buscar jugadores por posicion, estado y edad (1.5)",
    "5": "Contratos proximos a vencer (1.6)",
    "6": "Clasificacion de una competicion (1.7)",
    "7": "Top goleadores por temporada",
    "8": "Masa salarial por equipo",
}


def run_queries(consulta="todas", team_id="t_01", match_id="m_01",
                player_id="p_01", competition_id="c_01", season=None,
                position="CM", status="Available", min_age=18, max_age=30,
                days_ahead=365, limit=10):
    if consulta != "todas" and str(consulta) not in TITLES:
        raise ValueError("Consulta MongoDB desconocida.")
    if not 0 <= min_age <= max_age <= 120:
        raise ValueError("Las edades deben cumplir: 0 <= minima <= maxima <= 120.")
    if days_ahead < 0 or limit < 1:
        raise ValueError("Dias debe ser >= 0 y limite debe ser >= 1.")
    season = season or season_default()
    selected = list(TITLES) if consulta == "todas" else [str(consulta)]
    db = get_mongo_db()
    try:
        for code in selected:
            if code == "1":
                result = get_team_roster(db, team_id, season)
            elif code == "2":
                result = get_match_box_score(db, match_id)
            elif code == "3":
                result = get_player_season_stats(db, player_id, season)
            elif code == "4":
                result = search_players(db, position, status, min_age, max_age)
            elif code == "5":
                result = get_expiring_contracts(db, days_ahead)
            elif code == "6":
                result = get_standings(db, competition_id, season)
            elif code == "7":
                result = agg_top_scorers(db, season, limit)
            else:
                result = agg_team_payroll(db)
            show_json(TITLES[code], result)
    finally:
        db.client.close()


def ask_and_run(code):
    values = {"consulta": code}
    def selected(*codes):
        return code == "todas" or code in codes
    if selected("1"):
        values["team_id"] = ask_text("ID del equipo", "t_01")
    if selected("2"):
        values["match_id"] = ask_text("ID del partido", "m_01")
    if selected("3"):
        values["player_id"] = ask_text("ID del jugador", "p_01")
    if selected("6"):
        values["competition_id"] = ask_text("ID de la competicion", "c_01")
    if selected("1", "3", "6", "7"):
        values["season"] = ask_text("Temporada", season_default())
    if selected("4"):
        values["position"] = ask_text("Posicion", "CM")
        values["status"] = ask_text("Estado", "Available")
        values["min_age"] = ask_int("Edad minima", 18, 0, 120)
        values["max_age"] = ask_int("Edad maxima", max(30, values["min_age"]), values["min_age"], 120)
    if selected("5"):
        values["days_ahead"] = ask_int("Dias hasta vencer", 365, 0)
    if selected("7"):
        values["limit"] = ask_int("Cantidad de goleadores", 10, 1)
    run_queries(**values)


def menu():
    actions = {
        code: (title, lambda code=code: ask_and_run(code))
        for code, title in TITLES.items()
    }
    actions["9"] = ("Ejecutar las ocho consultas", lambda: ask_and_run("todas"))
    print("Las fechas de nacimiento y el rol CM del dataset son simulados.")
    run_menu("MONGODB - CONSULTAS", actions)


def main():
    parser = argparse.ArgumentParser(description="Consultas MongoDB de Scouts")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--menu", action="store_true")
    mode.add_argument("--consulta", choices=["todas", *TITLES])
    parser.add_argument("--equipo", default="t_01")
    parser.add_argument("--partido", default="m_01")
    parser.add_argument("--jugador", default="p_01")
    parser.add_argument("--competicion", default="c_01")
    parser.add_argument("--temporada", default=None)
    parser.add_argument("--posicion", default="CM")
    parser.add_argument("--estado", default="Available")
    parser.add_argument("--edad-min", type=int, default=18)
    parser.add_argument("--edad-max", type=int, default=30)
    parser.add_argument("--dias", type=int, default=365)
    parser.add_argument("--limite", type=int, default=10)
    args = parser.parse_args()
    if args.menu:
        menu()
    else:
        if not 0 <= args.edad_min <= args.edad_max <= 120 or args.dias < 0 or args.limite < 1:
            parser.error("Revisa las edades, dias y limite.")
        run_queries(args.consulta or "todas", args.equipo, args.partido, args.jugador,
                    args.competicion, args.temporada, args.posicion, args.estado,
                    args.edad_min, args.edad_max, args.dias, args.limite)


if __name__ == "__main__":
    main()
