import os
import uvicorn
import asyncio
import logging
from pathlib import Path
from threading import Event
from dataclasses import dataclass, asdict, field
from contextlib import asynccontextmanager
from queue import Queue
from typing import Dict, Optional
from fastapi import FastAPI, WebSocket, APIRouter
from fastapi.responses import FileResponse
from daffi import Global, FG
from daffi.exceptions import RemoteStoppedUnexpectedly
from daffi.decorators import fetcher, __body_unknown__, local
from daffi.registry import Callback
from fastapi.staticfiles import StaticFiles
from fastapi.websockets import WebSocketDisconnect

STOP_MARKER = b""
ROUTER_ROOT = Path(__file__).parent
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("router")


class NonUniqueNameDetected(Exception):
    ...


@dataclass
class Worker:
    host: str
    mac: str
    process_name: str
    id: str
    active: bool = field(repr=False)

    def serialize(self):
        return asdict(self)


class WebHandler:

    def __init__(self, web_host: str, web_port: int):
        self.web_host = web_host
        self.web_port = web_port

        self.ws_queues: Dict[int, Queue] = dict()
        self.director_sockets: Dict[int, WebSocket] = dict()

        self.workers: Dict[str, Worker] = dict()
        self.disconnect_worker_event = Event()

        self.app = FastAPI(lifespan=self.lifespan)
        self.static = StaticFiles(directory=ROUTER_ROOT / "static")
        self.app.mount("/static", self.static, name="static")

        api_router = APIRouter()
        # Web handlers:
        #     `/`         - index page (render html).
        #     `/director` - main socket. Manage interaction with UI.
        #     `/terminal` - terminal socket. Manage user input from keyboard.
        api_router.add_api_route("/", self.index, methods=["GET"])
        api_router.add_api_websocket_route("/director", self.director)
        api_router.add_api_websocket_route("/terminal", self.terminal)
        self.app.include_router(api_router)

    @fetcher
    @staticmethod
    async def read_from_terminal(term_id: int):
        """Read output data from remote terminal"""
        __body_unknown__(term_id)

    @asynccontextmanager
    async def lifespan(self, *_):
        # Initialize `Global` object before web.
        disconect_worker_obs_task = asyncio.create_task(self.on_worker_disconnect_observer())
        yield
        disconect_worker_obs_task.cancel()
        os._exit(0)

    async def index(self):
        return FileResponse(self.static.directory / "index.html", media_type="text/html")

    async def director(self, websocket: WebSocket):
        """Director socket handler"""
        await websocket.accept()
        director_id = websocket.__hash__()
        self.director_sockets[director_id] = websocket
        await websocket.send_json([w.serialize() for w in self.workers.values()])
        # Read director commands
        async for data in websocket.iter_json():
            if data["command"] == "delete_terminal":
                term_id = data["term_id"]
                self.workers.pop(term_id, None)
                await self.update_workers()
        self.director_sockets.pop(director_id, None)

    async def terminal(self, websocket: WebSocket):
        """Terminal socket handler"""
        await websocket.accept()
        term_id = websocket.__hash__()
        worker_id = websocket.query_params["worker_id"]
        queue = Queue()
        self.ws_queues[term_id] = queue

        read_term_task = asyncio.create_task(
            self.read_terminal_output(term_id=term_id, worker_id=worker_id, websocket=websocket)
        )
        try:
            async for payload in websocket.iter_bytes():
                queue.put_nowait(payload)
        except (WebSocketDisconnect, RuntimeError):
            ...
        queue.put_nowait(STOP_MARKER)
        read_term_task.cancel()

    async def read_terminal_output(self, term_id: int, worker_id: str, websocket: WebSocket):
        """Get output data from remote terminal and write it to websocket"""
        exec_modifier = FG(receiver=worker_id)
        try:
            read_term_iterator = await self.read_from_terminal.call(term_id=term_id, exec_modifier=exec_modifier)
        except Exception as e:
            logger.error(f"unexpected error during read from remote terminal: {e}")
        else:
            try:
                async for out in read_term_iterator.get_async():
                    await websocket.send_bytes(out)
            except RemoteStoppedUnexpectedly:
                if existing_worker := self.workers.get(worker_id):
                    existing_worker.active = False
                    await self.update_workers()
            await websocket.close()

    async def update_workers(self):
        """Send list of connected/disconnected workers through director socket."""
        workers = [w.serialize() for w in self.workers.values()]
        for director_socket in self.director_sockets.values():
            await director_socket.send_json(workers)

    def on_worker_disconnect(self, _, process_name: str):
        if worker := self.workers.get(process_name):
            worker.active = False
            logger.info(f"{worker} has been disconnected.")
            self.disconnect_worker_event.set()
            self.disconnect_worker_event = Event()

    async def on_worker_disconnect_observer(self):
        while True:
            await asyncio.get_running_loop().run_in_executor(None, self.disconnect_worker_event.wait)
            await self.update_workers()

    def run(self):
        uvicorn.run(self.app, port=self.web_port, host=self.web_host)


class Router(Callback):

    def __init__(
            self, rpc_host: str, rpc_port: int, ssl_cert: Optional[str],
            ssl_key: Optional[str], web_handler: WebHandler
    ):
        super().__init__()
        self.name = "TermRouter"
        self.rpc_host = rpc_host
        self.rpc_port = rpc_port
        self.ssl_cert = ssl_cert
        self.ssl_key = ssl_key

        self.web_handler = web_handler
        self.ws_queues = self.web_handler.ws_queues
        self.workers = self.web_handler.workers
        self.director_sockets = self.web_handler.director_sockets

    @local
    def run(self):
        Global(
            host=self.rpc_host, port=self.rpc_port, init_controller=True,
            ssl_certificate=self.ssl_cert, ssl_key=self.ssl_key,
            process_name=self.name, on_node_disconnect=self.web_handler.on_worker_disconnect
        )
        self.web_handler.run()

    def write_to_terminal(self, term_id: int):
        """
        The method involves retrieving information from user input through a websocket.
        It is a remote callback that continuously transfers data from
        a `router` application to a worker process that operates a pty terminal.
        """
        queue = self.ws_queues[term_id]
        while True:
            payload = queue.get()
            yield payload
            if payload == STOP_MARKER:
                del self.ws_queues[term_id]
                break

    async def on_worker_connect(self, host, mac, process_name, id):
        duplicate_name_detected = False
        worker = Worker(host=host, mac=mac, process_name=process_name, id=id, active=True)
        # Check if worker with such `process_name` already exists
        if existing_worker := self.workers.get(process_name):
            if existing_worker.id != worker.id and existing_worker.active:
                duplicate_name_detected = True
                worker = existing_worker
                existing_worker.active = False
        self.workers[process_name] = worker
        logger.info(f"{worker} has been connected.")
        await self.web_handler.update_workers()

        if duplicate_name_detected:
            raise NonUniqueNameDetected(f"Worker with name {process_name!r} already exists and is active."
                                        f" To fix this re-connect existing worker with name {process_name!r}"
                                        f" and make sure all workers have unique names.")
