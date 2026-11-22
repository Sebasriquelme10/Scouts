from cassandra.cluster import Cluster


def get_session(hosts=None, port=9042):
    if hosts is None:
        hosts = ["127.0.0.1"]
    cluster = Cluster(hosts, port=port)
    session = cluster.connect()
    return cluster, session