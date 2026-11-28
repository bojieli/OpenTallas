"""hub_post: one throttled hub line through coord/bin/post.sh (FLEET-OPS-R5 P-WAVE-ALLOWLIST-STALE, P-WAIT-STATE-SILENT).  Stdlib only.

post(lane, text, post_fn=None)  runs `bash <coord>/bin/post.sh LANE TEXT` on the hub (here when ~/coord/bin/post.sh exists, else over ssh to
                                the hub with the script on stdin); never raises; post_fn replaces it (tests)
due(book, key, now, every)      True and book[key] = now when the key was not posted within `every` seconds
int_r3_lane(die)                the die's INT-R3 lane (QC-INT-R3, KV-INT-R3, S81-INT-R3, HEAD-INT-R3)."""
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path

SIX_H = 6 * 3600
COORD = Path(os.environ.get("COORD_DIR") or Path.home() / "coord")


# Per-process wall budget for budgeted posts (a tick is one process): each real post.sh run takes 15-20 s on a loaded hub, so ~40 new
# wait-state keys in one kit-wave step spent 12 of the tick's 15 minutes and the 900 s TimeoutStartSec killed the tick (TICK-DEAD 11-27 15:36).
POST_BUDGET_S = float(os.environ.get("OT_HUB_POST_BUDGET_S") or 60)
_SPENT = [0.0]


def budget_ok(post_fn=None):
    """True while a budgeted caller may still start a real post this process; always True with a test post_fn."""
    return post_fn is not None or _SPENT[0] < POST_BUDGET_S


def post(lane, text, post_fn=None, hub="intel2", budgeted=False):
    if post_fn is not None:
        return post_fn(lane, text)
    if budgeted and _SPENT[0] >= POST_BUDGET_S:
        return False
    t0 = time.monotonic()
    try:
        return _post_real(lane, text, hub)
    finally:
        if budgeted:
            _SPENT[0] += time.monotonic() - t0


def _post_real(lane, text, hub):
    if "pytest" in sys.modules and not os.environ.get("OT_HUB_POST_REAL"):
        return False                          # a test never posts to the real hub
    try:
        if (COORD / "bin/post.sh").is_file():
            r = subprocess.run(["bash", str(COORD / "bin/post.sh"), lane, text], capture_output=True, text=True, timeout=120)
        else:
            script = f"bash ~/coord/bin/post.sh {shlex.quote(lane)} {shlex.quote(text)}\n"
            r = subprocess.run(["ssh", "-o", "ConnectTimeout=30", hub, "bash -s"], input=script, capture_output=True, text=True, timeout=180)
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def due(book, key, now, every=SIX_H):
    if key in book and now - float(book[key]) < every:
        return False
    book[key] = now
    return True


def int_r3_lane(die):
    d = str(die or "").lower()
    for sub, lane in (("head", "HEAD-INT-R3"), ("kv", "KV-INT-R3"), ("s81", "S81-INT-R3"), ("qc", "QC-INT-R3"), ("compute", "QC-INT-R3")):   # head first: s81_head is the HEAD die
        if sub in d:
            return lane
    return (d.upper().replace("_", "-") or "COORD") + "-INT-R3"
