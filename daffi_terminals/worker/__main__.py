import logging
from daffi import Global
from daffi_terminals.worker.worker import on_worker_init, on_worker_connect

logging.basicConfig(level=logging.INFO)


if __name__ == "__main__":
    Global(host="localhost", port=9999, on_init=on_worker_init, on_node_connect=on_worker_connect).join()
