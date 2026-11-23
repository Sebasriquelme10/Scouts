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
    {
      red_agencias(func: eq(player_id, "p_01"))
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
    {
      var(func: eq(team_id, "t_01"))
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
    {
      partidos as var(func: eq(winner_team_id, "t_01"))
        @filter(type(Match)) {

        ~played_in
          @filter(type(Player))
          @facets(eq(team_id, "t_01")) {
          uno as math(1)
        }

        cantidad as sum(val(uno))
      }

      grupos_en_victorias(func: uid(partidos))
        @filter(ge(val(cantidad), 3)) {
        uid
        match_id
        date
        competition
        winner_team_id
        cantidad_jugadores: val(cantidad)

        ~played_in
          @filter(type(Player))
          @facets(eq(team_id, "t_01"))
          @facets(starter, minutes_played, team_id) {
          uid
          player_id
          name
        }
      }
    }
    """),
]


def run_dgraph_queries():
    client_stub, client = get_client()

    try:
        for titulo, consulta in CONSULTAS:
            txn = client.txn(read_only=True)

            try:
                respuesta = txn.query(consulta)

                print(f"\n=== {titulo} ===")
                print(json.dumps(
                    json.loads(respuesta.json),
                    indent=2,
                    ensure_ascii=False,
                ))
            finally:
                txn.discard()
    finally:
        client_stub.close()


if __name__ == "__main__":
    run_dgraph_queries()
