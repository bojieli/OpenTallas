"""rt_floor: the runtime floor for NEW launches (FABLE-FLOW-0230 T1, FLOW-FLEET-R1 11-22).

210 of 335 rt processes ran below the 6d2e187f0d floor; 5 lanes STARTED work on a below-floor rt after the floor was posted, because the floor was
a sentence in posts.  The floor is now data: kit_wave.json `min_rt` (sha, 7+ hex), else $OT_MIN_RT, else the file <rt root>/MIN_RT.  An rt snapshot
is at or above the floor when it IS the floor or its rt/<sha12>.manifest.json 'made' time is not older than the floor's (rt snapshots are made
only from main, in order, by ot-tools-follow).  Below the floor a new launch is refused with the re-pin command; a sealed or pinned plan tree
that must keep its rt declares it (--rt-floor-exempt WHY), which is recorded, never silent.  Unknown (a manifest missing on this host) is a note,
never a refusal.  Stdlib only."""
import datetime
import json
import os
from pathlib import Path

RT_ROOT = Path(os.environ.get("OT_RT_ROOT") or "/srv/opentallas-scratch2/claude/rt")


def floor_of(cfg=None, rt_root=None):
    """-> (floor sha or '', source)"""
    v = str(((cfg or {}).get("min_rt")) or "").strip()
    if v:
        return v, "kit_wave.json min_rt"
    v = os.environ.get("OT_MIN_RT", "").strip()
    if v:
        return v, "$OT_MIN_RT"
    try:
        v = (Path(rt_root or RT_ROOT) / "MIN_RT").read_text().split()[0].strip()
        return v, str(Path(rt_root or RT_ROOT) / "MIN_RT")
    except (OSError, IndexError):
        return "", ""


def _made(sha, rt_root):
    f = Path(rt_root) / f"{str(sha)[:12]}.manifest.json"
    if not f.is_file() and 7 <= len(str(sha)) < 12:      # a short floor (6d2e187f0d): the one manifest with that prefix
        hits = sorted(Path(rt_root).glob(f"{sha}*.manifest.json"))
        f = hits[0] if len(hits) == 1 else f
    try:
        m = json.loads(f.read_text())
        return datetime.datetime.fromisoformat(str(m["made"])).timestamp(), str(m.get("sha") or sha)
    except (OSError, ValueError, KeyError, TypeError):
        return None, str(sha)


def current_sha12(rt_root=None):
    try:
        return os.path.basename(os.readlink(Path(rt_root or RT_ROOT) / "current"))[:12]
    except OSError:
        return ""


def check(sha, cfg=None, exempt="", rt_root=None, what="launch"):
    """-> dict(verdict OK|EXEMPT|UNKNOWN|BELOW|NO-FLOOR, floor, sha, why, repin).  BELOW is the only refusal."""
    rt_root = rt_root or RT_ROOT
    floor, src = floor_of(cfg, rt_root)
    out = {"floor": floor, "floor_source": src, "sha": str(sha or ""), "exempt": str(exempt or "")}
    if not floor:
        return dict(out, verdict="NO-FLOOR", why="no min_rt set")
    if not sha:
        return dict(out, verdict="UNKNOWN", why="no rt pin (the tree's own tools)")
    s, f = str(sha), str(floor)
    if s.startswith(f[:12]) or f.startswith(s[:12]):
        return dict(out, verdict="OK", why="is the floor")
    ts, _ = _made(s, rt_root)
    tf, _ = _made(f, rt_root)
    if ts is None or tf is None:
        return dict(out, verdict="UNKNOWN", why=f"rt manifest missing on this host ({'rt ' + s[:12] if ts is None else 'floor ' + f[:12]})")
    if ts >= tf:
        return dict(out, verdict="OK", why="made after the floor")
    cur = current_sha12(rt_root)
    repin = f"--rt {cur or '<rt/current sha12>'}"
    if str(exempt or "").strip():
        return dict(out, verdict="EXEMPT", why=f"rt {s[:12]} is below floor {f[:12]}; declared exempt: {str(exempt).strip()[:200]}", repin=repin)
    return dict(out, verdict="BELOW", repin=repin,
                why=(f"RT-FLOOR refused: {what} pins rt {s[:12]}, below the floor {f[:12]} ({src}). Re-pin: re-run with {repin} "
                     "(rt/current), or for a sealed / pinned plan tree that must keep this rt declare it with --rt-floor-exempt 'WHY'"))
