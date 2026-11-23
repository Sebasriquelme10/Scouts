import pydgraph


def get_client(host="localhost", grpc_port=9080):
    client_stub = pydgraph.DgraphClientStub(f"{host}:{grpc_port}")
    client = pydgraph.DgraphClient(client_stub)
    return client_stub, client