import argparse
from pathlib import Path
import sys

# Permite ejecutar este archivo directamente y usar las utilidades de la raiz.
sys.path.append(str(Path(__file__).resolve().parents[1]))
from scouts_menu_utils import ask_text, ask_int, run_menu, show_json, season_default

from connect import get_session

CONSULTAS = [
    ("Eventos Play-by-Play",
     "SELECT event_timestamp, player_name, team_name, event_type, details FROM match_events WHERE match_id = %s",
     False),
    ("Telemetria biometrica",
     "SELECT timestamp, heart_rate, instant_speed_kmh, distance_covered_meters FROM player_biometrics WHERE match_id = %s AND player_id = %s",
     True),
    ("Marcador en vivo",
     "SELECT match_period, match_minute, home_team_name, home_score, away_team_name, away_score, scoring_player_id FROM live_scoreboard WHERE match_id = %s",
     False),
    ("Estadisticas por intervalos",
     "SELECT player_name, team_name, match_period, interval_minute, goals, shots, passes, fouls FROM player_interval_stats WHERE match_id = %s AND player_id = %s",
     True),
    ("Faltas e infracciones",
     "SELECT foul_timestamp, offending_player_name, drawn_by_player_name, card_type FROM match_fouls WHERE match_id = %s",
     False),
    ("Interrupciones VAR / medicas",
     "SELECT start_timestamp, stoppage_type, duration_seconds, referee_decision FROM match_stoppages WHERE match_id = %s",
     False),
]


def run_realtime_queries(match_id="m_01", player_id="p_01", consulta="todas"):
    if consulta != "todas" and str(consulta) not in {str(i) for i in range(1, 7)}:
        raise ValueError("Consulta Cassandra desconocida.")
    indices = range(len(CONSULTAS)) if consulta == "todas" else [int(consulta) - 1]
    cluster, session = get_session()
    try:
        session.set_keyspace("scouts")
        for index in indices:
            title, query, needs_player = CONSULTAS[index]
            params = (match_id, player_id) if needs_player else (match_id,)
            rows = session.execute(query, params)
            show_json(f"{index + 1}. {title}", [dict(row._asdict()) for row in rows])
    finally:
        cluster.shutdown()


def ask_and_run(code):
    match_id = ask_text("ID del partido", "m_01")
    needs_player = code == "todas" or CONSULTAS[int(code) - 1][2]
    player_id = ask_text("ID del jugador", "p_01") if needs_player else "p_01"
    run_realtime_queries(match_id, player_id, code)


def menu():
    actions = {
        str(index + 1): (title, lambda code=str(index + 1): ask_and_run(code))
        for index, (title, _, _) in enumerate(CONSULTAS)
    }
    actions["7"] = ("Ejecutar las seis consultas", lambda: ask_and_run("todas"))
    run_menu("CASSANDRA - CONSULTAS", actions)


def main():
    parser = argparse.ArgumentParser(description="Consultas Cassandra de Scouts")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--menu", action="store_true")
    mode.add_argument("--consulta", choices=["todas", "1", "2", "3", "4", "5", "6"])
    parser.add_argument("--partido", default="m_01")
    parser.add_argument("--jugador", default="p_01")
    args = parser.parse_args()
    if args.menu:
        menu()
    else:
        run_realtime_queries(args.partido, args.jugador, args.consulta or "todas")


if __name__ == "__main__":
    main()
