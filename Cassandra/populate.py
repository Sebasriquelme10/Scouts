from pathlib import Path
from connect import get_session


def populate_cassandra():
    cluster, session = get_session()
    try:
        cql_path = Path(__file__).parent / "schema_and_seed.cql"
        raw_sql = cql_path.read_text(encoding="utf-8")

        # Filtrar comentarios y dividir sentencias por punto y coma
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
            if not stmt.upper().startswith("SELECT"):
                session.execute(stmt)

        print("Keyspace 'scouts', 6 tablas y datos de Cassandra poblados correctamente.")
    finally:
        cluster.shutdown()


if __name__ == "__main__":
    populate_cassandra()