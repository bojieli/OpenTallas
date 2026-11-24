"""lbl_gate.py -- LOOK-BEFORE-LAUNCH admission check (LAUNCH-GUARD 11-23, OWNER 11-22 23:2x, COORD Fable flow review FIX 1).

Rule: a NEW launch of an unsigned type -- a relaunch of a failed attempt, or the first attempt of a plan-event row -- starts only when the type's
row in ~/coord/lanes/VIS-COVERAGE.tsv (column 9, row_status) says the family was looked at and fixed:

  allowed   PROBE-PASS, NONE-NEEDED, and the later states IN-EVENT, SIGNED (the header orders DRAFT|PRE-PASS|PROBE-PASS|IN-EVENT|SIGNED|NONE-NEEDED;
            LAUNCH-GUARD ruling: a state past PROBE-PASS is not held, the less restrictive reading), and PROBE-THROUGH (COORD 11-24 08:04 ruling (2),
            VIS-REOWN: a DRAFT row past the 30-min visual-review SLA launches as a probe now; OWNER: probes never wait, review never blocks)
  refused   DRAFT, PRE-PASS (and any other status) -> reason LBL-<status>
  no row    not held (the tracker lists every unsigned type from OWNERS-SWEEP; a type it does not list has no verdict to wait for) -> LBL-NOROW, logged

Never refused: probe kits (OT_PROBE_THROUGH=1 in the gen env, or a private goal place / geom / cts / grt), and anything already running (callers only
ask at a NEW admission).  The table is data driven: read from the coord hub, cached in memory and on disk, refreshed every REFRESH_S (5 min); when no
copy can be read at all the gate does not hold (LBL-NOTABLE, logged by the caller).

Matching an item to a row: the item name, then without a leading 'ot_', then its variant base (cut at '__cl' / '__pv'): sibling rows of that base
decide (any allowed sibling allows).  The VIS die column (HEAD/KV/QC/S81) is matched to the wave die when the caller passes one.
Stdlib only; pure functions apart from load().
"""
import os
import re
import subprocess
import time

REFRESH_S = 300
ALLOWED = ("PROBE-PASS", "NONE-NEEDED", "IN-EVENT", "SIGNED", "PROBE-THROUGH")
PROBE_GOALS = ("place", "geom", "cts", "grt")
REL = "lanes/VIS-COVERAGE.tsv"
CACHE = os.path.expanduser(os.environ.get("OT_LBL_CACHE", "~/.local/state/lbl/VIS-COVERAGE.tsv"))
DIE_MAP = {"s81": "S81", "s81_head": "HEAD", "head": "HEAD", "qwen_kvsys": "KV", "kv": "KV", "qwen_compute": "QC", "qc": "QC", "hbm": "HBM"}
_MEM = {"t": 0.0, "rows": None, "src": ""}


def parse(text):
    """VIS-COVERAGE text -> [(die, type, family, row_status)] (comment / header lines skipped)"""
    out = []
    for ln in (text or "").splitlines():
        if not ln.strip() or ln.startswith("#"):
            continue
        f = ln.split("\t")
        if len(f) < 9 or f[0] == "die":
            continue
        out.append((f[0].strip(), f[1].strip(), f[2].strip(), f[8].strip().upper()))
    return out


def _read_local():
    for base in (os.environ.get("OT_COORD_DIR"), os.path.expanduser("~/coord")):
        if base:
            try:
                with open(os.path.join(base, REL), encoding="utf-8", errors="replace") as f:
                    return f.read(), os.path.join(base, REL)
            except OSError:
                pass
    return None, ""


def _read_hub(hub):
    try:
        p = subprocess.run(["ssh", "-n", "-o", "ControlPath=none", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", hub, f"cat ~/coord/{REL}"],
                           capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    return p.stdout if p.returncode == 0 and p.stdout.strip() else None


def _write_cache(text):
    try:
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        tmp = f"{CACHE}.{os.getpid()}"
        with open(tmp, "w") as f:
            f.write(text)
        os.replace(tmp, CACHE)
    except OSError:
        pass


def load(reader=None, hub=None, now=None, refresh_s=REFRESH_S):
    """-> (rows or None, source).  reader() -> text is the only source when given (the wave / autopilot pass their read_coord).  Otherwise (run-item on any host),
    after the memory cache (refresh_s): the local coord file, the disk cache when it is younger than refresh_s, the hub over ssh, the disk cache of any age."""
    now = time.time() if now is None else now
    if _MEM["rows"] is not None and now - _MEM["t"] < refresh_s:
        return _MEM["rows"], _MEM["src"]
    text, src = None, ""
    if reader is not None:                               # the caller's coord view is the only source (the wave / autopilot read origin/coord/state)
        try:
            text = reader() or None
        except Exception:
            text = None
        rows = parse(text) if text else None
        _MEM.update(t=now, rows=rows, src="reader" if rows is not None else "")
        return rows, _MEM["src"]
    if text is None:
        text, src = _read_local()
    if text is None:
        try:
            if now - os.path.getmtime(CACHE) < refresh_s:
                text, src = open(CACHE).read(), CACHE
        except OSError:
            pass
    if text is None:
        text = _read_hub(hub or os.environ.get("OT_HUB_NAME") or "intel2")
        src = f"{hub or os.environ.get('OT_HUB_NAME') or 'intel2'}:~/coord/{REL}" if text else ""
    if text is None:
        try:
            text, src = open(CACHE).read(), CACHE + " (stale)"
        except OSError:
            pass
    if text is None:
        _MEM.update(t=now, rows=None, src="")
        return None, ""
    rows = parse(text)
    if src and not src.startswith(CACHE):
        _write_cache(text)
    _MEM.update(t=now, rows=rows, src=src)
    return rows, src


def reset_cache():
    _MEM.update(t=0.0, rows=None, src="")


def variant_base(name):
    return re.split(r"__(?:cl|pv)[0-9a-f]{6,}", name, maxsplit=1)[0]


def lookup(rows, item, die=None):
    """-> (status, matched type) or (None, '') when no row covers the item"""
    vd = DIE_MAP.get(str(die or "").lower())
    rs = [r for r in rows if not vd or r[0].upper() == vd] or ([] if vd else rows)
    names = [item] + ([item[3:]] if item.startswith("ot_") else [])
    for n in names:
        hit = [r for r in rs if r[1] == n]
        if hit:
            return hit[-1][3], hit[-1][1]
    for n in names:
        b = variant_base(n)
        sib = [r for r in rs if r[1] == b or r[1].startswith(b + "__")]
        if sib:
            ok = [r for r in sib if r[3] in ALLOWED]
            r = (ok or sib)[-1]
            return r[3], r[1] + (" (variant sibling)" if r[1] != n else "")
    return None, ""


def is_probe(env=None, goal=None):
    """a probe kit: OT_PROBE_THROUGH=1 in its gen env, or a private goal that stops before sign-off"""
    if str((env or {}).get("OT_PROBE_THROUGH", "")).strip() == "1":
        return "OT_PROBE_THROUGH=1"
    if goal and str(goal).strip().lower() in PROBE_GOALS:
        return f"goal {str(goal).strip().lower()}"
    return ""


def check(item, die=None, env=None, goal=None, rows=None, reader=None, hub=None, now=None):
    """-> (refused: bool, reason 'LBL-<status>' / 'LBL-NOROW' / 'LBL-NOTABLE' / 'LBL-PROBE' / 'LBL-<status>-OK', detail)"""
    pr = is_probe(env, goal)
    if pr:
        return False, "LBL-PROBE", f"probe kit ({pr}): never held"
    if rows is None:
        rows, src = load(reader=reader, hub=hub, now=now)
        if rows is None:
            return False, "LBL-NOTABLE", f"{REL} unreadable here and on the hub: not held"
    status, typ = lookup(rows, item, die)
    if status is None:
        return False, "LBL-NOROW", f"no {REL} row for {item}: not held"
    if status in ALLOWED:
        return False, f"LBL-{status}-OK", f"{REL} {typ} {status}"
    return True, f"LBL-{status or 'BLANK'}", (f"{REL} row {typ} is {status or 'blank'}: no relaunch / first attempt until its family row is PROBE-PASS or NONE-NEEDED "
                                              f"(LOOK-BEFORE-LAUNCH, OWNER 11-22; probe kits OT_PROBE_THROUGH=1 / goal place|geom|grt run)")
