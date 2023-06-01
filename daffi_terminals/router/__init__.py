from argparse import Namespace
from daffi_terminals.router.router import Router, WebHandler


def start_router(args: Namespace):
    web_handler = WebHandler(web_host=args.web_host, web_port=args.web_port)
    router = Router(
        rpc_host=args.rpc_host, rpc_port=args.rpc_port,
        ssl_cert=args.ssl_cert, ssl_key=args.ssl_key, web_handler=web_handler
    )
    router.run()
