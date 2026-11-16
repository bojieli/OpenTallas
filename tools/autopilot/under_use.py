"""UNDER-USE (FABLE-FLOW-0445 class #2): one line per autopilot tick that says how much of the fleet is idle and which holds keep
eligible rows from launching.  Pure functions take the `ot-run --status` text, the kit-wave state and the kit-wave config; step()
does the reads and the log.  It never launches, cancels or writes state."""
import fnmatch
import json
import re
from collections import Counter
from pathlib import Path

HOST_RE = re.compile(r"([A-Za-z0-9_.-]+) admits (-?\d+) GB.*?load (\d+(?:\.\d+)?)/(\d+)\b")
THR_RE = re.compile(r"\bthreads (\d+)/(\d+)\b")
EXCLUDE = {"localhost"}          # by rule no heavy jobs on localhost: not an idle-capacity signal
ELIGIBLE = ("ENQUEUED",)         # waiting for a launch
HELD = ("ROUTE-HELD",)           # placed, route held


def host_idle(status_text, exclude=EXCLUDE):
    """-> {host: {"cores", "load", "committed", "idle"}}; idle = cores - max(load, committed threads when ot-run reports them)"""
    out = {}
    for part in (status_text or "").split("|"):
        m = HOST_RE.search(part)
        if not m or m.group(1) in exclude:
            continue
        cores, load = int(m.group(4)), float(m.group(3))
        t = THR_RE.search(part)
        committed = int(t.group(1)) if t else None
        used = max(load, committed or 0)
        out[m.group(1)] = dict(cores=cores, load=load, committed=committed, idle=max(0, int(round(cores - used))))
    return out


def kind(text):
    """leading token of a hold reason: 'WAVE-HOLDS-1115 2026-11-15 ...' -> 'WAVE-HOLDS-1115'"""
    m = re.match(r"\s*([A-Za-z0-9_.-]+)", str(text or ""))
    return m.group(1) if m else "unnamed"


def hold_counts(items, cfg):
    """-> Counter of 'kind' -> rows.  ENQUEUED rows of a die whose hold_items match = 'hold_items:<kind>'; ROUTE-HELD rows =
    'route_hold:<kind>'; any hold or reason text that names tree_switch / tree-switch is counted as 'tree_switch' instead."""
    dies = (cfg or {}).get("dies") or {}
    c = Counter()
    for rec in (items or {}).values():
        st = rec.get("status")
        if st not in ELIGIBLE + HELD:
            continue
        d = dies.get(rec.get("die")) or {}
        if st in HELD:
            why = str(rec.get("route_hold") or rec.get("reason") or "")
            k = "tree_switch" if re.search(r"tree[_-]switch", why, re.I) else "route_hold:" + kind(why)
            c[k] += 1
            continue
        item = str(rec.get("item") or "")
        why = next((str(w) for pat, w in (d.get("hold_items") or {}).items() if fnmatch.fnmatchcase(item, pat)), None)
        if why is None:
            c["enqueued_not_held"] += 1          # eligible, no hold: waits for a slot / host / max_inflight
        else:
            c["tree_switch" if re.search(r"tree[_-]switch", why, re.I) else "hold_items:" + kind(why)] += 1
    return c


def line(status_text, items, cfg, top=5):
    hosts = host_idle(status_text)
    cores = sum(h["cores"] for h in hosts.values())
    idle = sum(h["idle"] for h in hosts.values())
    per = " ".join(f"{h}={v['idle']}(load {v['load']:.0f}/{v['cores']}" + (f", thr {v['committed']}" if v["committed"] is not None else "") + ")"
                   for h, v in sorted(hosts.items(), key=lambda kv: -kv[1]["idle"]))
    holds = hold_counts(items, cfg)
    ranked = ", ".join(f"{k}={n}" for k, n in holds.most_common(top)) or "none"
    pct = (100.0 * (cores - idle) / cores) if cores else 0.0
    return (f"UNDER-USE idle {idle} of {cores} threads (used {pct:.0f}%): {per or 'no host status'} | "
            f"rows not launching {sum(holds.values())}: {ranked}")


def step(AP):
    """one UNDER-USE log line; never raises into the tick"""
    try:
        ap_dir = Path(AP.AP_DIR)
        rc, out, _ = AP.sh([AP.OT_RUN, "--status"], timeout=120)
        status = out if rc == 0 else ""
        try:
            items = (json.loads((ap_dir / "kit_wave_state.json").read_text()).get("items") or {})
        except (OSError, ValueError):
            items = {}
        try:
            cfg = json.loads((ap_dir / "kit_wave.json").read_text())
        except (OSError, ValueError):
            cfg = {}
        AP.log(line(status, items, cfg) if status else "UNDER-USE ot-run --status unavailable")
    except Exception as e:
        AP.log(f"UNDER-USE failed: {type(e).__name__}: {e}")
