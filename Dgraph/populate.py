import json
from pathlib import Path

import pydgraph
from connect import get_client


SCHEMA = """
player_id: string @index(exact) .
name: string @index(exact, term) .
birth_date: datetime .
nationality: string .
status: string @index(exact) .
positions: [string] .

team_id: string @index(exact) .
team_name: string @index(exact, term) .
season: string @index(exact) .
head_coach: string .

match_id: string @index(exact) .
date: datetime .
competition: string @index(exact) .
winner_team_id: string @index(exact) .

agent_id: string @index(exact) .
country: string .

belongs: [uid] @reverse .
played_in: [uid] @reverse .
represented_by: [uid] @reverse .
passed_to: [uid] .

type Player {
    player_id
    name
    birth_date
    nationality
    status
    positions
    belongs
    played_in
    represented_by
    passed_to
}

type Team {
    team_id
    team_name
    season
    head_coach
}

type Match {
    match_id
    date
    competition
    winner_team_id
}

type Agent {
    agent_id
    name
    country
}
"""


def load_json(filename):
    data_dir = Path(__file__).resolve().parent.parent / "data"
    return json.loads(
        (data_dir / filename).read_text(encoding="utf-8")
    )


def populate_dgraph():
    players_raw = load_json("players.json")
    relations_raw = load_json("graph_relations.json")
    teams_comp_raw = load_json("teams_and_competitions.json")
    matches_events_raw = load_json("matches_and_events.json")

    teams_list = (
        teams_comp_raw
        if isinstance(teams_comp_raw, list)
        else teams_comp_raw.get("teams", [])
    )

    comps_list = (
        []
        if isinstance(teams_comp_raw, list)
        else teams_comp_raw.get("competitions", [])
    )

    comp_map = {
        c["competition_id"]: c["name"]
        for c in comps_list
    }

    matches_list = (
        matches_events_raw
        if isinstance(matches_events_raw, list)
        else matches_events_raw.get("matches", [])
    )

    # Construir los datos antes de reiniciar la base.
    mutations = []
    known_teams = set()
    known_matches = set()

    # Equipos.
    for team in teams_list:
        tid = team["team_id"]
        known_teams.add(tid)

        mutations.append({
            "uid": f"_:{tid}",
            "dgraph.type": "Team",
            "team_id": tid,
            "team_name": team.get("team_name", tid),
            "season": str(team.get("season", "")),
            "head_coach": team.get("head_coach", ""),
        })

    for membership in relations_raw.get("belongs", []):
        tid = membership["team_id"]

        if tid not in known_teams:
            known_teams.add(tid)

            mutations.append({
                "uid": f"_:{tid}",
                "dgraph.type": "Team",
                "team_id": tid,
                "team_name": tid,
            })

    # Partidos y equipo ganador.
    for match in matches_list:
        mid = match["match_id"]
        known_matches.add(mid)

        competition = (
            match.get("competition")
            or comp_map.get(match.get("competition_id", ""), "")
        )

        node = {
            "uid": f"_:{mid}",
            "dgraph.type": "Match",
            "match_id": mid,
            "competition": competition,
        }

        if "date" in match:
            node["date"] = match["date"]

        score = match.get("final_score")

        if score is not None:
            home_score = score["home_score"]
            away_score = score["away_score"]

            if home_score > away_score:
                node["winner_team_id"] = match["home_team_id"]
            elif away_score > home_score:
                node["winner_team_id"] = match["away_team_id"]

        mutations.append(node)

    for participation in relations_raw.get("played_in", []):
        mid = participation["match_id"]

        if mid not in known_matches:
            known_matches.add(mid)

            mutations.append({
                "uid": f"_:{mid}",
                "dgraph.type": "Match",
                "match_id": mid,
            })

    # Agencias.
    for agent in relations_raw.get("agents", []):
        mutations.append({
            "uid": f"_:{agent['agent_id']}",
            "dgraph.type": "Agent",
            "agent_id": agent["agent_id"],
            "name": agent["name"],
            "country": agent.get("country", ""),
        })

    # Relación jugador-equipo.
    belongs_by_player = {}

    for membership in relations_raw.get("belongs", []):
        belongs_by_player.setdefault(
            membership["player_id"], []
        ).append({
            "uid": f"_:{membership['team_id']}",
            "belongs|since": membership["since"],
            "belongs|jersey_number": membership["jersey_number"],
        })

    # Participaciones, incluyendo el equipo de cada jugador.
    played_by_player = {}

    for participation in relations_raw.get("played_in", []):
        played_by_player.setdefault(
            participation["player_id"], []
        ).append({
            "uid": f"_:{participation['match_id']}",
            "played_in|starter": participation["starter"],
            "played_in|minutes_played": participation["minutes_played"],
            "played_in|team_id": participation["team_id"],
        })

    # Acumular pases por pareja de jugadores.
    pass_totals = {}

    for edge in relations_raw.get("passed_to", []):
        pair = (
            edge["from_player_id"],
            edge["to_player_id"],
        )

        pass_totals[pair] = (
            pass_totals.get(pair, 0)
            + int(edge["successful_passes_count"])
        )

    passes_by_player = {}

    for (source_id, target_id), total in pass_totals.items():
        passes_by_player.setdefault(source_id, []).append({
            "uid": f"_:{target_id}",
            "passed_to|successful_passes_count": total,
        })

    # Jugadores y todas sus relaciones.
    for player in players_raw:
        pid = player["player_id"]

        player_node = {
            "uid": f"_:{pid}",
            "dgraph.type": "Player",
            "player_id": pid,
            "name": player["name"],
            "nationality": player.get("nationality", ""),
            "status": player.get("status", "Available"),
            "positions": player.get("positions", []),
        }

        if "birth_date" in player:
            player_node["birth_date"] = player["birth_date"]

        if pid in belongs_by_player:
            player_node["belongs"] = belongs_by_player[pid]

        if pid in played_by_player:
            player_node["played_in"] = played_by_player[pid]

        agent_id = player.get("agent_id")

        if agent_id:
            player_node["represented_by"] = [
                {"uid": f"_:{agent_id}"}
            ]

        if pid in passes_by_player:
            player_node["passed_to"] = passes_by_player[pid]

        mutations.append(player_node)

    client_stub, client = get_client()

    try:
        # Reiniciar exclusivamente la instancia de pruebas.
        client.alter(pydgraph.Operation(drop_all=True))
        client.alter(pydgraph.Operation(schema=SCHEMA))

        txn = client.txn()

        try:
            txn.mutate(set_obj=mutations, commit_now=True)
            print(
                "Dgraph cargado correctamente: equipos, partidos, "
                "agencias, jugadores, pertenencias, participaciones y pases."
            )
        finally:
            txn.discard()
    finally:
        client_stub.close()


if __name__ == "__main__":
    populate_dgraph()
