import os
import sys
import fcntl
import tty
import uuid
import struct
import socket
import logging
from enum import Enum
from pathlib import Path
from threading import Thread
from multiprocessing import Pipe
from subprocess import check_output, CalledProcessError, DEVNULL

from daffi import Global
from daffi.utils import colors
from daffi.registry import Callback
from daffi.settings import BYTES_CHUNK
from daffi.exceptions import RemoteStoppedUnexpectedly
from daffi.decorators import fetcher, local, __body_unknown__

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("worker")


class Command(bytes, Enum):
    STOP = b""
    DATA = b"1"
    RESIZE = b"2"


@fetcher
def write_to_terminal(term_id):
    __body_unknown__(term_id)


@fetcher
def on_worker_connect(_, process_name: str):
    """
    Return common metadata information about worker.
    Handler is being executed every time on connection (despite of it is first connection or re-connection)
    """
    host = socket.gethostname()
    mac = ":".join(["{:02x}".format((uuid.getnode() >> ele) & 0xFF) for ele in range(0, 8 * 6, 8)][::-1])
    return host, mac, process_name


def on_worker_init(g: Global):
    """The Global object init handler is executed only once for the first connection to the Router."""
    arrow_sign = colors.intense_green("\u2B00")
    math_sign = colors.intense_magenta("\uF50E")
    print(
        f"{arrow_sign} Worker {g.process_name!r} has been connected successfully.\n"
        f"{math_sign} Happy exploring! {math_sign}"
    )


class Worker(Callback):
    def __post_init__(self):
        self.message_of_the_day = self.get_message_of_the_day()

    def read_from_terminal(self, term_id):
        exeargv = [os.getenv("SHELL", "sh")]
        host_env = os.environ.copy()
        # os.environ["TERM"] = "xterm"
        r, w = Pipe(duplex=False)

        interactive = sys.stdin.isatty()
        if interactive:
            ttyattr = tty.tcgetattr(0)
            # struct winsize 4 unsigned short. see ioctl_tty
            winsize = fcntl.ioctl(0, tty.TIOCGWINSZ, 8 * b" ")

        pid, fdm = os.forkpty()
        if pid == 0:
            # python's forkpty can't pass termios and winsize. do manually
            # see forkpty
            if interactive:
                tty.tcsetattr(0, tty.TCSANOW, ttyattr)
                fcntl.ioctl(0, tty.TIOCSWINSZ, winsize)
            # execute a new program, replacing the current process
            os.execvpe(exeargv[0], exeargv, host_env)
        # open as binary I/O. buffered and flush method support
        pid = os.fork()
        if pid == 0:
            self.serve_child_terminal(fdm=fdm, read_pipe=r)
        else:
            yield from self.serve_parent_terminal(fdm=fdm, term_id=term_id, write_pipe=w)

    @local
    def serve_parent_terminal(self, fdm, term_id, write_pipe):
        serve_user_input_th = Thread(target=self.serve_user_input, args=(term_id, write_pipe))
        serve_user_input_th.start()
        while True:
            try:
                # Read as much as possible according to max allowed daffi payload in one message.
                b = os.read(fdm, BYTES_CHUNK)
            except OSError:
                break
            yield b

    @local
    def serve_child_terminal(self, fdm, read_pipe):
        pty = os.fdopen(fdm, "wb")
        while True:
            b = read_pipe.recv()
            command, data = b[:1], b[1:]
            if command == Command.STOP:
                pty.write(b"\x04")  # Write Ctrl-D
                pty.flush()
                read_pipe.close()
                os._exit(0)

            elif command == Command.RESIZE:
                height, width = data.decode().split(",")
                winsize = struct.pack("HHHH", int(height), int(width), 0, 0)
                fcntl.ioctl(0, tty.TIOCSWINSZ, winsize)
            else:
                pty.write(data)
                pty.flush()

    @local
    def serve_user_input(self, term_id, write_pipe):
        try:
            for data in write_to_terminal(term_id).get():
                write_pipe.send(data)
                if data == Command.STOP:
                    write_pipe.close()
                    break
        except RemoteStoppedUnexpectedly as e:
            logger.error(str(e))
            write_pipe.send(Command.STOP.value)
            write_pipe.close()

    @local
    def get_message_of_the_day(self):
        """Get message of the day for terminal greeting"""
        out = b""
        # Not working as expected
        mot_scripts_dir = Path("/etc/update-motd.d")
        for script in sorted(mot_scripts_dir.iterdir()):
            try:
                out += check_output(["sh", script], stderr=DEVNULL)
            except CalledProcessError:
                out = b""
                break
        return out
