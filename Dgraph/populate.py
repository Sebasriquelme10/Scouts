import json
from pathlib import Path
import pydgraph
from connect import get_client

SCHEMA = """
# --- Propiedades de Nodos ---
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

agent_id: string @index(exact) .
country: string .

# --- Aristas (Consultas 2.1 a 2.5) ---
belongs: [uid] @reverse .
played_in: [uid] @reverse .
represented_by: [uid] @reverse .
passed_to: [uid] .

# --- Tipos de Nodos (4 entidades requeridas para 2.1 - 2.5) ---
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
}

type Agent {
    agent_id
    name
    country
}
"""


def load_json(filename):
    data_dir = Path(__file__).resolve().parent.parent / "data"
    return json.loads((data_dir / filename).read_text(encoding="utf-8"))


def populate_dgraph():
    players_raw = load_json("players.json")
    relations_raw = load_json("graph_relations.json")
    teams_comp_raw = load_json("teams_and_competitions.json")
    matches_events_raw = load_json("matches_and_events.json")

    teams_list = (
        teams_comp_raw if isinstance(teams_comp_raw, list)
        else teams_comp_raw.get("teams", [])
    )
    comps_list = (
        [] if isinstance(teams_comp_raw, list)
        else teams_comp_raw.get("competitions", [])
    )
    comp_map = {c["competition_id"]: c["name"] for c in comps_list}

    matches_list = (
        matches_events_raw if isinstance(matches_events_raw, list)
        else matches_events_raw.get("matches", [])
    )

    client_stub, client = get_client()
    try:
        # 1. Reiniciar datos previos y aplicar esquema limpio (2.1 a 2.5)
        client.alter(pydgraph.Operation(drop_all=True))
        client.alter(pydgraph.Operation(schema=SCHEMA))

        mutations = []
        known_teams = set()
        known_matches = set()

        # 2. Nodos Team
        for t in teams_list:
            tid = t["team_id"]
            known_teams.add(tid)
            mutations.append({
                "uid": f"_:{tid}",
                "dgraph.type": "Team",
                "team_id": tid,
                "team_name": t.get("team_name", tid),
                "season": str(t.get("season", "")),
                "head_coach": t.get("head_coach", ""),
            })

        for b in relations_raw.get("belongs", []):
            tid = b["team_id"]
            if tid not in known_teams:
                known_teams.add(tid)
                mutations.append({
                    "uid": f"_:{tid}",
                    "dgraph.type": "Team",
                    "team_id": tid,
                    "team_name": tid,
                })

        # 3. Nodos Match
        for m in matches_list:
            mid = m["match_id"]
            known_matches.add(mid)
            comp_name = m.get("competition") or comp_map.get(m.get("competition_id", ""), "")
            node = {
                "uid": f"_:{mid}",
                "dgraph.type": "Match",
                "match_id": mid,
                "competition": comp_name,
            }
            if "date" in m:
                node["date"] = m["date"]
            mutations.append(node)

        for p_in in relations_raw.get("played_in", []):
            mid = p_in["match_id"]
            if mid not in known_matches:
                known_matches.add(mid)
                mutations.append({
                    "uid": f"_:{mid}",
                    "dgraph.type": "Match",
                    "match_id": mid,
                })

        # 4. Nodos Agent (listos para que Nacho conecte 'represented_by' en 2.3)
        for ag in relations_raw.get("agents", []):
            mutations.append({
                "uid": f"_:{ag['agent_id']}",
                "dgraph.type": "Agent",
                "agent_id": ag["agent_id"],
                "name": ag["name"],
                "country": ag.get("country", ""),
            })

        # 5. Nodos Player + aristas 2.1 (belongs) y 2.2 (played_in) con sus facetas
        belongs_by_player = {}
        for b in relations_raw.get("belongs", []):
            belongs_by_player.setdefault(b["player_id"], []).append({
                "uid": f"_:{b['team_id']}",
                "belongs|since": b["since"],
                "belongs|jersey_number": b["jersey_number"],
            })

        played_by_player = {}
        for p_in in relations_raw.get("played_in", []):
            played_by_player.setdefault(p_in["player_id"], []).append({
                "uid": f"_:{p_in['match_id']}",
                "played_in|starter": p_in["starter"],
                "played_in|minutes_played": p_in["minutes_played"],
            })

        for pl in players_raw:
            pid = pl["player_id"]
            player_node = {
                "uid": f"_:{pid}",
                "dgraph.type": "Player",
                "player_id": pid,
                "name": pl["name"],
                "nationality": pl.get("nationality", ""),
                "status": pl.get("status", "Available"),
                "positions": pl.get("positions", []),
            }
            if "birth_date" in pl:
                player_node["birth_date"] = pl["birth_date"]
            if pid in belongs_by_player:
                player_node["belongs"] = belongs_by_player[pid]
            if pid in played_by_player:
                player_node["played_in"] = played_by_player[pid]

            # ESPACIO PARA NACHO (2.3 y 2.4):
            # - 2.3: agregar arista 'represented_by' usando pl["agent_id"]
            # - 2.4: agregar arista 'passed_to' desde relations_raw.get("passed_to", [])
            mutations.append(player_node)

        txn = client.txn()
        try:
            txn.mutate(set_obj=mutations, commit_now=True)
            print("Esquema de Dgraph (2.1-2.5), nodos y relaciones 2.1 / 2.2 poblados correctamente.")
        finally:
            txn.discard()
    finally:
        client_stub.close()


if __name__ == "__main__":
    populate_dgraph()