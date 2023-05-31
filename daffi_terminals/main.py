import logging
from argparse import ArgumentParser
from daffi_terminals.router import start_router
from daffi_terminals.worker import start_worker

logging.basicConfig(level=logging.INFO)

if __name__ == '__main__':
    parser = ArgumentParser()
    subparsers = parser.add_subparsers()
    subparsers.required = True
    subparsers.dest = 'command'
    router_parser = subparsers.add_parser("start-router", help="Start router")
    worker_parser = subparsers.add_parser("start-worker", help="Start worker")

    if parser.parse_args().command == "start-router":
        start_router(router_parser)
    else:
        start_worker(worker_parser)
