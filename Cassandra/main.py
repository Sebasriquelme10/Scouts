from connect import get_session


def run_realtime_queries(match_id="M001", player_id="P010"):
    cluster, session = get_session()
    session.set_keyspace("scouts")
    try:
        print("=== 1. Eventos Play-by-Play (match_events) ===")
        rows = session.execute(
            "SELECT event_timestamp, player_name, team_name, event_type, details "
            "FROM match_events WHERE match_id = %s",
            (match_id,),
        )
        for r in rows:
            print(dict(r._asdict()))

        print("\n=== 2. Telemetría Biométrica (player_biometrics) ===")
        rows = session.execute(
            "SELECT timestamp, heart_rate, instant_speed_kmh, distance_covered_meters "
            "FROM player_biometrics WHERE match_id = %s AND player_id = %s",
            (match_id, player_id),
        )
        for r in rows:
            print(dict(r._asdict()))

        print("\n=== 3. Marcador en Vivo (live_scoreboard) ===")
        rows = session.execute(
            "SELECT match_period, match_minute, home_team_name, home_score, "
            "away_team_name, away_score, scoring_player_id "
            "FROM live_scoreboard WHERE match_id = %s",
            (match_id,),
        )
        for r in rows:
            print(dict(r._asdict()))

        print("\n=== 4. Estadísticas por Intervalos (player_interval_stats) ===")
        rows = session.execute(
            "SELECT player_name, team_name, match_period, interval_minute, "
            "goals, shots, passes, fouls "
            "FROM player_interval_stats WHERE match_id = %s AND player_id = %s",
            (match_id, player_id),
        )
        for r in rows:
            print(dict(r._asdict()))

        print("\n=== 5. Faltas e Infracciones (match_fouls) ===")
        rows = session.execute(
            "SELECT foul_timestamp, offending_player_name, drawn_by_player_name, card_type "
            "FROM match_fouls WHERE match_id = %s",
            (match_id,),
        )
        for r in rows:
            print(dict(r._asdict()))

        print("\n=== 6. Interrupciones VAR / Médicas (match_stoppages) ===")
        rows = session.execute(
            "SELECT start_timestamp, stoppage_type, duration_seconds, referee_decision "
            "FROM match_stoppages WHERE match_id = %s",
            (match_id,),
        )
        for r in rows:
            print(dict(r._asdict()))
    finally:
        cluster.shutdown()


if __name__ == "__main__":
    run_realtime_queries()