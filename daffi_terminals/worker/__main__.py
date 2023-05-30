import logging
from daffi import Global
from daffi_terminals.worker.worker import Worker

logging.basicConfig(level=logging.INFO)


if __name__ == "__main__":
    worker = Worker()
    Global(host="localhost", port=9999, on_node_connect=worker.router_fetcher.on_worker_connect).join()
