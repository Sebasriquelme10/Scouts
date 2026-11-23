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
    print(f"\ Top Goleadores — Temporada {season} ")
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


def run_queries():
    db = get_mongo_db()

    res_players = search_players(db, position="CM", status="Available", min_age=18, max_age=30)
    print_search_players(res_players)

    days = 365
    res_contracts = get_expiring_contracts(db, days_ahead=days)
    print_expiring_contracts(res_contracts, days_ahead=days)

    season = "2026-2027"
    res_scorers = agg_top_scorers(db, season=season)
    print_top_scorers(res_scorers, season=season)

    roster = get_team_roster(db, team_id="t_01", season=season)
    print_team_roster(roster, team_id="t_01", season=season)

    payroll = agg_team_payroll(db)
    print_team_payroll(payroll)


if __name__ == "__main__":
    run_queries()