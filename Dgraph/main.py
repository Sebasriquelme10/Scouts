import argparse
from pathlib import Path
import sys

# Permite ejecutar este archivo directamente y usar las utilidades de la raiz.
sys.path.append(str(Path(__file__).resolve().parents[1]))
from scouts_menu_utils import ask_text, ask_int, run_menu, show_json, season_default

import json
from connect import get_client


CONSULTAS = [
    ("2.1. Relación de Pertenencia Jugador-Equipo", """
    {
      player_team_membership(func: type(Player))
        @filter(has(belongs)) {
        player_id
        name
        positions

        belongs @facets(since, jersey_number) {
          team_id
          team_name
          season
        }
      }
    }
    """),

    ("2.2. Participación de Jugadores en Partidos", """
    {
      player_match_participation(func: type(Player))
        @filter(has(played_in)) {
        player_id
        name

        played_in @facets(starter, minutes_played) {
          match_id
          date
          competition
        }
      }
    }
    """),

    ("2.3. Red de Agentes y Representantes", """
    query agencias($jugador: string) {
      red_agencias(func: eq(player_id, $jugador))
        @filter(type(Player)) {
        uid
        player_id
        name

        represented_by {
          uid
          agent_id
          name

          ~represented_by @filter(type(Player)) {
            uid
            player_id
            name
          }
        }
      }
    }
    """),

    ("2.4. Red de Pases", """
    query pases($equipo: string) {
      var(func: eq(team_id, $equipo))
        @filter(type(Team)) {
        integrantes as ~belongs
      }

      red_pases(func: uid(integrantes))
        @filter(type(Player)) {
        uid
        player_id
        name

        passed_to
          @filter(uid(integrantes))
          @facets(successful_passes_count) {
          uid
          player_id
          name
        }
      }
    }
    """),

    ("2.5. Química en Alineaciones", """
    query quimica($equipo: string, $minimo: int) {
      partidos as var(func: eq(winner_team_id, $equipo))
        @filter(type(Match)) {

        ~played_in
          @filter(type(Player))
          @facets(eq(team_id, $equipo)) {
          uno as math(1)
        }

        cantidad as sum(val(uno))
      }

      grupos_en_victorias(func: uid(partidos))
        @filter(ge(val(cantidad), $minimo)) {
        uid
        match_id
        date
        competition
        winner_team_id
        cantidad_jugadores: val(cantidad)

        ~played_in
          @filter(type(Player))
          @facets(eq(team_id, $equipo))
          @facets(starter, minutes_played, team_id) {
          uid
          player_id
          name
        }
      }
    }
    """),
]



def run_dgraph_queries(consulta="todas", jugador="p_01", equipo="t_01", minimo=3):
    if minimo < 1:
        raise ValueError("El minimo de jugadores debe ser al menos 1.")
    codes = ["2.1", "2.2", "2.3", "2.4", "2.5"]
    if consulta != "todas" and consulta not in codes:
        raise ValueError("Consulta Dgraph desconocida.")
    selected = range(len(CONSULTAS)) if consulta == "todas" else [codes.index(consulta)]
    client_stub, client = get_client()
    try:
        for index in selected:
            variables = {}
            if index == 2:
                variables = {"$jugador": jugador}
            elif index == 3:
                variables = {"$equipo": equipo}
            elif index == 4:
                variables = {"$equipo": equipo, "$minimo": str(minimo)}
            title, query = CONSULTAS[index]
            txn = client.txn(read_only=True)
            try:
                response = txn.query(query, variables=variables)
                show_json(title, json.loads(response.json))
            finally:
                txn.discard()
    finally:
        client_stub.close()


def ask_and_run(code):
    jugador = ask_text("ID del jugador", "p_01") if code in ("2.3", "todas") else "p_01"
    equipo = ask_text("ID del equipo", "t_01") if code in ("2.4", "2.5", "todas") else "t_01"
    minimo = ask_int("Minimo de jugadores", 3, 1) if code in ("2.5", "todas") else 3
    run_dgraph_queries(code, jugador, equipo, minimo)


def menu():
    codes = ["2.1", "2.2", "2.3", "2.4", "2.5"]
    actions = {
        str(index + 1): (title, lambda code=code: ask_and_run(code))
        for index, (code, (title, _)) in enumerate(zip(codes, CONSULTAS))
    }
    actions["6"] = ("Ejecutar las cinco consultas", lambda: ask_and_run("todas"))
    print("Partidos, pases y agencias del dataset son simulados.")
    print("2.5 encuentra coincidencias en victorias como aproximacion para estudiar alineaciones.")
    run_menu("DGRAPH - CONSULTAS", actions)


def main():
    parser = argparse.ArgumentParser(description="Consultas Dgraph de Scouts")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--menu", action="store_true")
    mode.add_argument("--consulta", choices=["todas", "2.1", "2.2", "2.3", "2.4", "2.5"])
    parser.add_argument("--jugador", default="p_01")
    parser.add_argument("--equipo", default="t_01")
    parser.add_argument("--minimo", type=int, default=3)
    args = parser.parse_args()
    if args.menu:
        menu()
    else:
        if args.minimo < 1:
            parser.error("--minimo debe ser al menos 1")
        run_dgraph_queries(args.consulta or "todas", args.jugador, args.equipo, args.minimo)


if __name__ == "__main__":
    main()
