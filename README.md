## Daffi Terminals

Simple web based application designed to facilitate the connection to remote terminals.

## Preview
![sc.png](https://raw.githubusercontent.com/600apples/dafi-terminals/main/docs/sc.png)

### How it works

![how-it-works](https://raw.githubusercontent.com/600apples/dafi-terminals/main/docs/intro.png)


### Get started

1. Install this app, run command `pip install daffi-terminals`
2. Start a router, run command `dterm start-router --rpc-host=0.0.0.0 --rpc-port=9999 --web-host=0.0.0.0 --web-port=8888`
3. Connect worker to router, run command `dterm start-worker --rpc-host=0.0.0.0 --rpc-port=9999` (you can connect as many workers as you want)
3. Navigate [http://localhost:8888](http://localhost:8888/) in your browser

#### `start-router` arguments

| Argument | Description | Required  |
|----------|-------------|-----------|
| `--rpc-host` | host for communication between router and workers | Yes |
| `--rpc-port` | port for communication between router and workers | Yes |
| `--web-host` | host for serving web server | Yes |
| `--web-port` |  port for serving web server | Yes |
| `--ssl-cert` | ssl certificate for connection encryption between router and workers | No |
| `--ssl-key` | ssl key for connection encryption between router and workers | No |


#### `start-worker` arguments

| Argument | Description | Required  |
|----------|-------------|-----------|
| `--rpc-host` | router rpc host | Yes |
| `--rpc-port` | router rpc port | Yes |
| `--name` | worker name. This name must be unique across all workers. If not provided then random name will be assigned | No |
| `--ssl-cert` | ssl certificate for connection encryption between router and workers | No |
| `--ssl-key` | ssl key for connection encryption between router and workers | No |
