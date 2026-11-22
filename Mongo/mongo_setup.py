from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from connect import get_mongo_db

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _parse_iso(date_str: str) -> datetime:
    return datetime.fromisoformat(date_str.replace("Z", "+00:00"))


# ==========================================
# 1. ÍNDICES Y POBLADO COMPLETO
# ==========================================

def ensure_indexes(db):
    db.players.create_index([("positions", 1), ("status", 1), ("birth_date", 1)])
    db.players.create_index([("contracts.contract_end", 1)])
    db.teams.create_index([("team_id", 1), ("season", 1)], unique=True)
    db.player_season_stats.create_index([("player_id", 1), ("season", 1)], unique=True)
    db.standings.create_index([("competition_id", 1), ("season", 1)], unique=True)


def seed_all_mongo(db):
    players_data = json.loads((DATA_DIR / "players.json").read_text(encoding="utf-8"))
    tc_data = json.loads((DATA_DIR / "teams_and_competitions.json").read_text(encoding="utf-8"))
    me_data = json.loads((DATA_DIR / "matches_and_events.json").read_text(encoding="utf-8"))
    ss_data = json.loads((DATA_DIR / "season_and_standings.json").read_text(encoding="utf-8"))

    # 1. Players (convirtiendo fechas a datetime real)
    for p in players_data:
        doc = dict(p)
        doc["birth_date"] = _parse_iso(doc["birth_date"])
        for c in doc.get("contracts", []):
            c["contract_start"] = _parse_iso(c["contract_start"])
            c["contract_end"] = _parse_iso(c["contract_end"])
        db.players.update_one({"player_id": doc["player_id"]}, {"$set": doc}, upsert=True)

    # 2. Competitions
    for c in tc_data.get("competitions", []):
        db.competitions.update_one({"competition_id": c["competition_id"]}, {"$set": c}, upsert=True)

    # 3. Teams (soporta histórico por temporada)
    for t in tc_data.get("teams", []):
        db.teams.update_one(
            {"team_id": t["team_id"], "season": t["season"]},
            {"$set": t},
            upsert=True,
        )

    # 4. Matches
    for m in me_data.get("matches", []):
        doc = dict(m)
        doc["date"] = _parse_iso(doc["date"])
        db.matches.update_one({"match_id": doc["match_id"]}, {"$set": doc}, upsert=True)

    # 5. Player Season Stats
    for st in ss_data.get("player_season_stats", []):
        db.player_season_stats.update_one(
            {"player_id": st["player_id"], "season": st["season"]},
            {"$set": st},
            upsert=True,
        )

    # 6. Standings
    for sd in ss_data.get("standings", []):
        db.standings.update_one(
            {"competition_id": sd["competition_id"], "season": sd["season"]},
            {"$set": sd},
            upsert=True,
        )


# ==========================================
# 2. CONSULTAS POR REQUERIMIENTO FUNCIONAL
# ==========================================

# Req 1.1: Registro / Actualización de Perfil del Jugador
def upsert_player_profile(db, player_doc: dict):
    return db.players.update_one(
        {"player_id": player_doc["player_id"]},
        {"$set": player_doc},
        upsert=True,
    )


# Req 1.2: Gestión y Consulta de Plantillas de Equipos (por temporada / histórico)
def get_team_roster(db, team_id: str, season: str = None):
    query = {"team_id": team_id}
    if season:
        query["season"] = season
    return list(db.teams.find(query, {"_id": 0}))


# Req 1.3: Almacenamiento y Consulta de Resumen de Partido (Box Score)
def get_match_box_score(db, match_id: str):
    return db.matches.find_one({"match_id": match_id}, {"_id": 0})


# Req 1.4: Acumulados Estadísticos por Temporada
def get_player_season_stats(db, player_id: str, season: str):
    return db.player_season_stats.find_one(
        {"player_id": player_id, "season": season},
        {"_id": 0},
    )


# Req 1.5: Búsqueda y Filtrado de Jugadores (usa índice compuesto)
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


# Req 1.6: Consulta de Contratos Próximos a Expirar (observación del profesor)
def get_expiring_contracts(db, days_ahead: int = 365):
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


# Req 1.7: Reporte de Clasificación y Rendimiento del Equipo
def get_standings(db, competition_id: str, season: str):
    return db.standings.find_one(
        {"competition_id": competition_id, "season": season},
        {"_id": 0},
    )


# ==========================================
# 3. PIPELINES DE AGREGACIÓN ANALÍTICA
# ==========================================

# Pipeline A: Ranking de mejores anotadores / aportadores por temporada
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


# Pipeline B: Masa salarial activa y promedio por equipo
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
  print(f"\n--- {title} ({len(results)}) ---")
  if not results:
    print("  No se encontraron jugadores con esos criterios.")
    return
  for p in results:
    pos = ", ".join(p.get("positions", []))
    traits = p.get("physical_traits", {})
    print(
        f"  • [{p.get('player_id')}] {p.get('name')} | Pos: {pos} | Estado:"
        f" {p.get('status')} | Nac: {_fmt_date(p.get('birth_date'))} |"
        f" {traits.get('height_cm', '-')} cm / {traits.get('weight_kg', '-')} kg"
    )


def print_expiring_contracts(results: list[dict], days_ahead: int):
  print(f"\n--- Contratos activos por vencer en {days_ahead} días ({len(results)}) ---")
  if not results:
    print("  No hay contratos por vencer en ese rango.")
    return
  for c in results:
    salary = f"${c.get('salary_per_year', 0):,.0f}"
    print(
        f"  • {c.get('name')} ({c.get('player_id')}) | Equipo:"
        f" {c.get('team_id')} | Vence: {_fmt_date(c.get('contract_end'))} |"
        f" Salario anual: {salary}"
    )


def print_top_scorers(results: list[dict], season: str):
  print(f"\n--- Top Aportadores / Goleo — Temporada {season} ---")
  if not results:
    print("  Sin estadísticas registradas para esta temporada.")
    return
  for idx, r in enumerate(results, start=1):
    pos = ", ".join(r.get("positions", []))
    print(
        f"  {idx}. {r.get('name')} ({r.get('player_id')}) [{pos}] -> Goles:"
        f" {r.get('goals')} | PJ: {r.get('games_played')} | Prom. min:"
        f" {r.get('average_minutes')}"
    )


if __name__ == "__main__":
    db = get_mongo_db()
    ensure_indexes(db)
    seed_all_mongo(db)

    res_players = search_players(
      db, position="CM", status="Available", min_age=18, max_age=30
    )
    print_search_players(res_players)

    days = 365
    res_contracts = get_expiring_contracts(db, days_ahead=days)
    print_expiring_contracts(res_contracts, days_ahead=days)

    season = "2026-2027"
    res_scorers = agg_top_scorers(db, season=season)
    print_top_scorers(res_scorers, season=season)