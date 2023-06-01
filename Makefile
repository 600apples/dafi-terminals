start-router:
	@python3 daffi_terminals/main.py start-router --rpc-host=localhost --rpc-port=9999 --web-host=localhost --web-port=8888

start-worker:
	@python3 daffi_terminals/main.py start-worker --rpc-host=localhost --rpc-port=9999
