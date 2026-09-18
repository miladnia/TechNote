import threading
import time
import webbrowser

from .server import Server


def open_in_background(server: Server):
    threading.Thread(
        target=_open_browser_when_ready,
        kwargs={"server": server},
        daemon=True,
    ).start()


def _open_browser_when_ready(server: Server):
    # Wait until server is up
    for _ in range(30):  # 3 seconds max
        if server.is_up():
            webbrowser.open(server.url)
            return
        time.sleep(0.1)
