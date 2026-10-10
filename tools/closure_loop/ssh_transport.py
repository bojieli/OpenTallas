"""Private multiplexed fleet transport; eight channels against measured MaxSessions=10.

A lost master fails the current operation, never replays it. An explicit mux
session-open refusal permits one fresh connection because no remote session opened.
The next operation reconnects under the master lock. File leases also cover reconcile/CLI processes.
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
# Bulk transfers (source sync tarballs, 100s of MB) never ride the shared mux master: on a lossy path
# (localhost -> ot-epyc3 2026-10-10: 190 ms RTT, 20-40 % loss, ~200 KB/s up) one master's TCP send queue
# filled with tar data (Send-Q 1.98 MB) and every probe/poll multiplexed behind it timed out, while six
# 1800 s syncs held six of the eight channel leases and the main thread waited forever for a seventh.
BULK_CHANNELS = 2
_LOCAL = {"local", "localhost"}
_REGISTRY_LOCK = threading.Lock()
_SEMAPHORES = {}
_BULK_SEMAPHORES = {}


class LeaseTimeout(subprocess.TimeoutExpired):
    """No channel lease within the caller's deadline; no remote command was started."""


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
            "-o", "ServerAliveInterval=30", "-o", "ServerAliveCountMax=6", "-o", "ControlPersist=1800",
            "-o", f"ControlPath={socket}"]


def session_open_refused(result):
    """Only this pre-session rejection proves a remote command did not start."""
    return (result.returncode == 255 and not result.stdout
            and (result.stderr or "").strip() ==
            "mux_client_request_session: session request failed: Session open refused by peer")


def direct_command(host):
    """Fresh connection prefix; the caller must retain its existing channel lease."""
    return _options("none") + ["-o", "ControlMaster=no", host]


def _ensure_master(host, root, key):
    # A coordinator may opt new operations into a fresh socket generation while
    # old transfers keep their master.  Channel leases and their host key remain
    # unchanged, so generations share the same measured session admission.
    epoch = os.environ.get("CL_SSH_SOCKET_EPOCH", "")
    suffix = "." + hashlib.sha256(epoch.encode()).hexdigest()[:12] if epoch else ""
    socket = root / (key + suffix + ".sock")
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
def command(host, *, wait_s=None, bulk=False):
    """Lease one remote session and yield its argv prefix, or a local shell prefix.

    wait_s bounds the wait for a lease (None = unbounded); on expiry LeaseTimeout (a subprocess.TimeoutExpired) is
    raised before any remote command starts, so every caller's transient-ssh handling applies (FLEET r1 2026-10-10:
    the main thread parked 20+ min in write_status() on an EPYC3 pool held by six source syncs).

    bulk=True (drive-1010 2026-10-10): a bulk stream (source tar, record rsync, checkpoint migration) leases one of
    BULK_CHANNELS per host and runs on its own fresh connection.  Through the shared ControlMaster six source tars to
    EPYC3 (190 ms RTT, 20-40 % loss) moved 27-44 MB in 25 min and the master's Send-Q head-of-line blocked every
    probe and poll multiplexed behind them."""
    if host in _LOCAL:
        yield ["bash", "-c"]
        return
    deadline = None if wait_s is None else time.monotonic() + wait_s

    def remaining():
        return None if deadline is None else max(0.0, deadline - time.monotonic())
    root = _directory()
    if bulk:
        with _REGISTRY_LOCK:
            sem = _BULK_SEMAPHORES.setdefault((str(root), host), threading.BoundedSemaphore(BULK_CHANNELS))
        if not sem.acquire(timeout=remaining()):
            raise LeaseTimeout(["ssh", host, "<bulk lease>"], wait_s)
        try:
            yield direct_command(host)
        finally:
            sem.release()
        return
    key = hashlib.sha256(host.encode()).hexdigest()[:20]
    with _REGISTRY_LOCK:
        sem = _SEMAPHORES.setdefault((str(root), host), threading.BoundedSemaphore(CHANNELS))
    if not sem.acquire(timeout=remaining()):
        raise LeaseTimeout(["ssh", host, "<channel lease>"], wait_s)
    try:
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
                    if deadline is not None and time.monotonic() >= deadline:
                        raise LeaseTimeout(["ssh", host, "<file lease>"], wait_s)
                    time.sleep(0.05)
            yield _ensure_master(host, root, key)
        finally:
            if lease is not None:
                lease.close()
    finally:
        sem.release()
