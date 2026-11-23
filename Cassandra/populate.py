import json
from datetime import datetime
from pathlib import Path
from connect import get_session


def parse_ts(ts_str):
    return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))


def load_json(filename):
    data_dir = Path(__file__).resolve().parent.parent / "data"
    return json.loads((data_dir / filename).read_text(encoding="utf-8"))


def populate_cassandra():
    players_raw = load_json("players.json")
    teams_comp_raw = load_json("teams_and_competitions.json")
    matches_data = load_json("matches_and_events.json")

    
    players_map = {p["player_id"]: p["name"] for p in players_raw}
    teams_list = (
        teams_comp_raw if isinstance(teams_comp_raw, list)
        else teams_comp_raw.get("teams", [])
    )
    teams_map = {t["team_id"]: t["team_name"] for t in teams_list}
    matches_map = {m["match_id"]: m for m in matches_data.get("matches", [])}

    cluster, session = get_session()
    try:
        # 1. Crear keyspace y las 6 tablas desde schema_and_seed.cql
        cql_path = Path(__file__).parent / "schema_and_seed.cql"
        raw_sql = cql_path.read_text(encoding="utf-8")
        cleaned_lines = [
            line for line in raw_sql.splitlines()
            if not line.strip().startswith("--")
        ]
        statements = [
            stmt.strip()
            for stmt in "\n".join(cleaned_lines).split(";")
            if stmt.strip()
        ]
        for stmt in statements:
            upper = stmt.upper()
            if upper.startswith(("DROP", "CREATE", "USE")):
                session.execute(stmt)

        # 2. Poblar Tabla 1: match_events
        for ev in matches_data.get("match_events", []):
            pid = ev["player_id"]
            tid = ev["team_id"]
            details = {str(k): str(v) for k, v in ev.get("details", {}).items()}
            session.execute(
                """
                INSERT INTO scouts.match_events (
                    match_id, event_timestamp, event_id, player_id, player_name,
                    team_id, team_name, event_type, details
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    ev["match_id"],
                    parse_ts(ev["event_timestamp"]),
                    ev["event_id"],
                    pid,
                    ev.get("player_name", players_map.get(pid, pid)),
                    tid,
                    ev.get("team_name", teams_map.get(tid, tid)),
                    ev["event_type"],
                    details,
                ),
            )

        # 3. Poblar Tabla 2: player_biometrics
        for bio in matches_data.get("player_biometrics", []):
            session.execute(
                """
                INSERT INTO scouts.player_biometrics (
                    match_id, player_id, timestamp, heart_rate,
                    instant_speed_kmh, distance_covered_meters
                ) VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    bio["match_id"],
                    bio["player_id"],
                    parse_ts(bio["timestamp"]),
                    int(bio["heart_rate"]),
                    float(bio["instant_speed_kmh"]),
                    float(bio["distance_covered_meters"]),
                ),
            )

        # 4. Poblar Tabla 3: live_scoreboard
        for sb in matches_data.get("live_scoreboard", []):
            match_info = matches_map.get(sb["match_id"], {})
            home_id = sb.get("home_team_id", match_info.get("home_team_id", ""))
            away_id = sb.get("away_team_id", match_info.get("away_team_id", ""))
            session.execute(
                """
                INSERT INTO scouts.live_scoreboard (
                    match_id, match_period, match_minute, update_timestamp,
                    home_team_id, home_team_name, away_team_id, away_team_name,
                    home_score, away_score, scoring_player_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    sb["match_id"],
                    int(sb.get("match_period", sb.get("quarter_period", 1))),
                    int(sb.get("match_minute", 0)),
                    parse_ts(sb["update_timestamp"]),
                    home_id,
                    teams_map.get(home_id, home_id),
                    away_id,
                    teams_map.get(away_id, away_id),
                    int(sb["home_score"]),
                    int(sb["away_score"]),
                    sb["scoring_player_id"],
                ),
            )

        # 5. Poblar Tabla 4: player_interval_stats (Sin COUNTER)
        for st in matches_data.get("player_interval_stats", []):
            pid = st["player_id"]
            tid = st["team_id"]
            session.execute(
                """
                INSERT INTO scouts.player_interval_stats (
                    match_id, player_id, interval_timestamp, player_name,
                    team_id, team_name, match_period, interval_minute,
                    goals, shots, passes, fouls
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    st["match_id"],
                    pid,
                    parse_ts(st["interval_timestamp"]),
                    st.get("player_name", players_map.get(pid, pid)),
                    tid,
                    st.get("team_name", teams_map.get(tid, tid)),
                    int(st["match_period"]),
                    int(st["interval_minute"]),
                    int(st["goals"]),
                    int(st["shots"]),
                    int(st["passes"]),
                    int(st["fouls"]),
                ),
            )

        # 6. Poblar Tabla 5: match_fouls
        for fl in matches_data.get("match_fouls", []):
            off_id = fl["offending_player_id"]
            drw_id = fl["drawn_by_player_id"]
            session.execute(
                """
                INSERT INTO scouts.match_fouls (
                    match_id, foul_timestamp, foul_id,
                    offending_player_id, offending_player_name,
                    drawn_by_player_id, drawn_by_player_name, card_type
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    fl["match_id"],
                    parse_ts(fl["foul_timestamp"]),
                    fl["foul_id"],
                    off_id,
                    fl.get("offending_player_name", players_map.get(off_id, off_id)),
                    drw_id,
                    fl.get("drawn_by_player_name", players_map.get(drw_id, drw_id)),
                    fl["card_type"],
                ),
            )

        # 7. Poblar Tabla 6: match_stoppages
        for sp in matches_data.get("match_stoppages", []):
            session.execute(
                """
                INSERT INTO scouts.match_stoppages (
                    match_id, start_timestamp, stoppage_type,
                    duration_seconds, referee_decision
                ) VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    sp["match_id"],
                    parse_ts(sp["start_timestamp"]),
                    sp["stoppage_type"],
                    int(sp["duration_seconds"]),
                    sp["referee_decision"],
                ),
            )

        print("Keyspace 'scouts' y 6 tablas pobladas dinámicamente desde /data/*.json.")
    finally:
        cluster.shutdown()


if __name__ == "__main__":
    populate_cassandra()