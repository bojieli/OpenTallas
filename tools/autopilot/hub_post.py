"""hub_post: one throttled hub line through coord/bin/post.sh (FLEET-OPS-R5 P-WAVE-ALLOWLIST-STALE, P-WAIT-STATE-SILENT).  Stdlib only.

post(lane, text, post_fn=None)  runs `bash <coord>/bin/post.sh LANE TEXT` on the hub (here when ~/coord/bin/post.sh exists, else over ssh to
                                the hub with the script on stdin); never raises; post_fn replaces it (tests)
due(book, key, now, every)      True and book[key] = now when the key was not posted within `every` seconds
int_r3_lane(die)                the die's INT-R3 lane (QC-INT-R3, KV-INT-R3, S81-INT-R3, HEAD-INT-R3)."""
import os
import shlex
import subprocess
from pathlib import Path

SIX_H = 6 * 3600
COORD = Path(os.environ.get("COORD_DIR") or Path.home() / "coord")


def post(lane, text, post_fn=None, hub="intel2"):
    if post_fn is not None:
        return post_fn(lane, text)
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
    for sub, lane in (("kv", "KV-INT-R3"), ("s81", "S81-INT-R3"), ("head", "HEAD-INT-R3"), ("qc", "QC-INT-R3"), ("compute", "QC-INT-R3")):
        if sub in d:
            return lane
    return (d.upper().replace("_", "-") or "COORD") + "-INT-R3"
