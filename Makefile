start-router:
	@dterm start-router --rpc-host=localhost --rpc-port=9999 --web-host=localhost --web-port=8888

start-worker:
	@dterm start-worker --rpc-host=localhost --rpc-port=9999
