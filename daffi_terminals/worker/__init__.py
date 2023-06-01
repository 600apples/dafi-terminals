from argparse import Namespace
from daffi import Global
from daffi_terminals.worker.worker import Worker, RouterFetcher


def start_worker(args: Namespace):
    router_fetcher = RouterFetcher()
    Worker(router_fetcher=router_fetcher)
    Global(
        process_name=args.name,
        host=args.rpc_host, port=args.rpc_port,
        ssl_certificate=args.ssl_cert, ssl_key=args.ssl_key,
        on_node_connect=router_fetcher.on_worker_connect_cb,
    ).join()
