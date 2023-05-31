from argparse import ArgumentParser
from daffi_terminals.router.router import Router, WebHandler


def start_router(parser: ArgumentParser):
    parser.add_argument("--rpc-host", help="Router rpc host (Interaction with workers)", required=True)
    parser.add_argument("--rpc-port", help="Router rpc port (Interaction with workers", type=int, required=True)
    parser.add_argument("--web-host", help="Router web host (Interaction with user)", required=True)
    parser.add_argument("--web-port", help="Router web port (Interaction with user", type=int, required=True)
    parser.add_argument("--ssl-cert", default=None, help="Path to ssl certificate")
    parser.add_argument("--ssl-key", default=None, help="Path to ssl private key")
    args = parser.parse_args()

    web_handler = WebHandler(web_host=args.web_host, web_port=args.web_port)
    router = Router(
        rpc_host=args.rpc_host, rpc_port=args.rpc_port,
        ssl_cert=args.ssl_cert, ssl_key=args.ssl_key, web_handler=web_handler
    )
    router.run()
