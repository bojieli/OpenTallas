"""Private multiplexed fleet transport; eight channels against measured MaxSessions=10.

A lost master fails the current operation, never replays it. The next operation
reconnects under the master lock. File leases also cover reconcile/CLI processes.
Authentication and host-key policy remain the user's existing SSH configuration.
"""
from contextlib import contextmanager
import fcntl
import hashlib
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import threading
import time

CHANNELS = 8
_LOCAL = {"local", "localhost"}
_REGISTRY_LOCK = threading.Lock()
_SEMAPHORES = {}


def _directory():
    # Keep Unix socket paths short, even when CL_STATE is a long test path.
    state = os.environ.get("CL_STATE", str(Path.home() / ".local/state/closure_loop"))
    key = hashlib.sha256(os.path.abspath(state).encode()).hexdigest()[:16]
    root = Path(tempfile.gettempdir()) / f"cl-ssh-{os.getuid()}-{key}"
    root.mkdir(mode=0o700, exist_ok=True)
    info = root.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
        raise RuntimeError(f"unsafe SSH control directory: {root}")
    return root


def _options(socket):
    return ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
            "-o", "ServerAliveInterval=30", "-o", "ControlPersist=60",
            "-o", f"ControlPath={socket}"]


def _ensure_master(host, root, key):
    socket = root / (key + ".sock")
    base = _options(socket)
    with (root / (key + ".master.lock")).open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        check = subprocess.run(base + ["-O", "check", host], capture_output=True, timeout=30)
        if check.returncode:
            # Only a failed mux check permits reconnect; no existing channel is killed.
            socket.unlink(missing_ok=True)
            result = subprocess.run(base + ["-o", "ControlMaster=yes", "-N", "-f", host],
                                    capture_output=True, timeout=30)
            if result.returncode:
                raise RuntimeError(f"ssh: master connection failed for {host}: {result.stderr!r}")
    # Prevent OpenSSH's automatic direct-auth fallback if the checked socket dies.
    # No request is automatically re-executed, since its side effects may be unknown.
    return base + ["-o", "ControlMaster=auto", "-o", "ProxyCommand=false", host]


@contextmanager
def command(host):
    """Lease one remote session and yield its argv prefix, or a local shell prefix."""
    if host in _LOCAL:
        yield ["bash", "-c"]
        return
    root = _directory()
    key = hashlib.sha256(host.encode()).hexdigest()[:20]
    with _REGISTRY_LOCK:
        sem = _SEMAPHORES.setdefault((str(root), host), threading.BoundedSemaphore(CHANNELS))
    with sem:
        lease = None
        try:
            while lease is None:
                for number in range(CHANNELS):
                    candidate = (root / f"{key}.{number}.lease").open("a")
                    try:
                        fcntl.flock(candidate, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    except BlockingIOError:
                        candidate.close()
                    else:
                        lease = candidate
                        break
                if lease is None:
                    time.sleep(0.05)
            yield _ensure_master(host, root, key)
        finally:
            if lease is not None:
                lease.close()
