import daemon

from main import start


with daemon.DaemonContext():
    start()
