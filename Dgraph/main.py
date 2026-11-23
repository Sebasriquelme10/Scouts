import json
from connect import get_client


def run_dgraph_queries():
    client_stub, client = get_client()
    try:
        # =====================================================================
        # CONSULTA 2.1: Relación de Pertenencia Jugador-Equipo (Player -> Team)
        # =====================================================================
        query_2_1 = """
        {
            player_team_membership(func: type(Player)) @filter(has(belongs)) {
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
        """
        txn = client.txn(read_only=True)
        res_2_1 = txn.query(query_2_1)
        print("=== 2.1. Relación de Pertenencia Jugador-Equipo ===")
        print(json.dumps(json.loads(res_2_1.json), indent=2, ensure_ascii=False))

        # =====================================================================
        # CONSULTA 2.2: Participación de Jugadores en Partidos (Player -> Match)
        # =====================================================================
        query_2_2 = """
        {
            player_match_participation(func: type(Player)) @filter(has(played_in)) {
                player_id
                name
                played_in @facets(starter, minutes_played) {
                    match_id
                    date
                    competition
                }
            }
        }
        """
        txn = client.txn(read_only=True)
        res_2_2 = txn.query(query_2_2)
        print("\n=== 2.2. Participación de Jugadores en Partidos ===")
        print(json.dumps(json.loads(res_2_2.json), indent=2, ensure_ascii=False))

        # =====================================================================
        # PENDIENTES PARA NACHO (Consultas 2.3, 2.4 y 2.5):
        # - 2.3: Red de Agentes y Representantes (Player -represented_by-> Agent)
        # - 2.4: Red de Pases e Interacción en Cancha (Player -passed_to-> Player)
        # - 2.5: Descubrimiento de Química en Alineaciones (>= 3 jugadores)
        # =====================================================================
    finally:
        client_stub.close()


if __name__ == "__main__":
    run_dgraph_queries()