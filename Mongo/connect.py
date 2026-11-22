import os
from cassandra.cluster import Cluster
import pydgraph
from pymongo import MongoClient


def get_mongo_db(uri: str = None, db_name: str = None):
    mongo_uri = uri or os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    target_db = db_name or os.getenv("MONGO_DB", "scouts_db")
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    return client[target_db]


def get_cassandra_session(hosts: list = None, keyspace: str = None):
    contact_points = hosts or os.getenv("CASSANDRA_HOSTS", "127.0.0.1").split(",")
    target_ks = keyspace or os.getenv("CASSANDRA_KEYSPACE", "scouts_ks")
    cluster = Cluster(contact_points)
    session = cluster.connect()
    session.execute(
        f"""
        CREATE KEYSPACE IF NOT EXISTS {target_ks}
        WITH replication = {{'class': 'SimpleStrategy', 'replication_factor': 1}}
        """
    )
    session.set_keyspace(target_ks)
    return session


def get_dgraph_client(target: str = None):
    dgraph_target = target or os.getenv("DGRAPH_TARGET", "localhost:9080")
    stub = pydgraph.DgraphClientStub(dgraph_target)
    client = pydgraph.DgraphClient(stub)
    client.check_version()
    return client


def test_connections():
    status = {}
    for name, fn in [
        ("MongoDB", get_mongo_db),
        ("Cassandra", get_cassandra_session),
        ("Dgraph", get_dgraph_client),
    ]:
        try:
            conn = fn()
            status[name] = ("OK", conn)
            print(f"[OK] Conectado a {name}")
        except Exception as exc:
            status[name] = ("ERROR", None)
            print(f"[ERROR] {name}: {exc}")
    return status


if __name__ == "__main__":
    test_connections()