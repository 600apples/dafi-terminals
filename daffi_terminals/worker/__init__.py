from argparse import ArgumentParser
from daffi import Global
from daffi_terminals.worker.worker import Worker


def start_worker(parser: ArgumentParser):
    parser.add_argument("--name", default=None, help="Worker name. If not provided default name will be generated")
    parser.add_argument("--rpc-host", help="Router host to connect", required=True)
    parser.add_argument("--rpc-port", help="Router port to connect", type=int, required=True)
    parser.add_argument("--ssl-cert", default=None, help="Path to ssl certificate")
    parser.add_argument("--ssl-key", default=None, help="Path to ssl private key")
    args = parser.parse_args()

    worker = Worker()
    Global(
        process_name=args.name,
        host=args.rpc_host, port=args.rpc_port,
        ssl_certificate=args.ssl_cert, ssl_key=args.ssl_key,
        on_node_connect=worker.router_fetcher.on_worker_connect,
    ).join()
