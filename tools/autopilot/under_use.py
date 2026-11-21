"""UNDER-USE (FABLE-FLOW-0445 class #2): one line per autopilot tick that says how much of the fleet is idle and which holds keep
eligible rows from launching.  Pure functions take the `ot-run --status` text, the kit-wave state and the kit-wave config; step()
does the reads and the log.  It never launches, cancels or writes state."""
import fnmatch
import json
import re
import time
from collections import Counter
from pathlib import Path

HOST_RE = re.compile(r"([A-Za-z0-9_.-]+) admits (-?\d+) GB.*?load (\d+(?:\.\d+)?)/(\d+)\b")
THR_RE = re.compile(r"\bthreads (\d+)/(\d+)\b")
EXCLUDE = {"localhost"}          # by rule no heavy jobs on localhost: not an idle-capacity signal
ELIGIBLE = ("ENQUEUED",)         # waiting for a launch
HELD = ("ROUTE-HELD",)           # placed, route held
SIGNED_Q = ("SIGNED", "SIGNED-LINKED", "SIGNED-UNVERSIONED", "ARCHIVED")


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


def row_classes(items, cfg):
    """-> {row key: class} for every eligible (ENQUEUED / ROUTE-HELD) row.  A row with no hold is split by the first launch gate it waits on:
    gate:disk_wait (gen disk), gate:q_<queue status> (the autopilot queue / ot-run admission state of its enqueued job), gate:no_queue_status."""
    dies = (cfg or {}).get("dies") or {}
    out = {}
    for key, rec in (items or {}).items():
        st = rec.get("status")
        if st not in ELIGIBLE + HELD:
            continue
        if str(rec.get("q_status") or "").upper() in SIGNED_Q or st in ("DEDUP-CREDITED",):
            continue        # WAVE-PILOT-FIX 11-18 (WAVE-FLOW-R2 census: 20 signed rows counted as waiting): a signed row is done, not waiting for a launch
        d = dies.get(rec.get("die")) or {}
        if st not in HELD and str(rec.get("q_status") or "").upper() == "SIGNED":
            continue                         # FABLE-FLOW-0010 H: a SIGNED job is a result, not a row waiting to launch; 66 of the 98 'superseded-event' rows were these
        if st in HELD:
            why = str(rec.get("route_hold") or rec.get("reason") or "")
            out[key] = "tree_switch" if re.search(r"tree[_-]switch", why, re.I) else "route_hold:" + kind(why)
            continue
        item = str(rec.get("item") or "")
        cur = d.get("event")
        if cur and rec.get("event") and rec.get("event") != cur:
            out[key] = "superseded"          # SUPERSEDED-1116: a row on an old event is not waiting; retire or relaunch it, never count it as non-launching
            continue
        why = next((str(w) for pat, w in (d.get("hold_items") or {}).items() if fnmatch.fnmatchcase(item, pat)), None)
        if why is not None:
            out[key] = "tree_switch" if re.search(r"tree[_-]switch", why, re.I) else "hold_items:" + kind(why)
        elif rec.get("disk_wait"):
            out[key] = "gate:disk_wait"
        else:
            out[key] = "gate:q_" + (str(rec.get("q_status") or "").lower() or "no_queue_status")
    return out


# FLOW-OPS-0900 11-21 (COORD ruling on fix 2 (3), owner rule "superseded re-signs go last, on spare capacity only"): a launch gate class that
# means a current-plan / plan-event row is waiting for admission.  Holds, running and failed rows are not waiting for capacity.
WAITING_GATE_RE = re.compile(r"^gate:(?:disk_wait|q_(?:no_queue_status|none|queued|pending|enqueued|submitted|wait[\w-]*))$")


def spare_admission(status_text, items, cfg, jobs=()):
    """-> (spare, why): True only when the gen hosts have idle threads AND no current-plan kit-wave row and no autopilot queue row waits to be
    admitted.  Unknown host status = not spare (the lowest-priority work waits)."""
    hosts = host_idle(status_text)
    if not hosts:
        return False, "ot-run --status unreadable"
    idle = sum(h["idle"] for h in hosts.values())
    if idle <= 0:
        return False, "0 idle threads on %d gen hosts" % len(hosts)
    waiting = Counter(c for c in row_classes(items, cfg).values() if WAITING_GATE_RE.match(c))
    if waiting:
        return False, "%d current-plan row(s) wait for admission (%s)" % (sum(waiting.values()), ", ".join("%s=%d" % kv for kv in waiting.most_common(3)))
    queued = sum(1 for j in (jobs or ()) if isinstance(j, dict) and j.get("status") is None)
    if queued:
        return False, "%d autopilot queue row(s) not yet submitted" % queued
    return True, "%d idle threads, no row waiting" % idle


def hold_counts(items, cfg):
    """-> Counter of 'kind' -> rows.  ENQUEUED rows of a die whose hold_items match = 'hold_items:<kind>'; ROUTE-HELD rows =
    'route_hold:<kind>'; any hold or reason text that names tree_switch / tree-switch is counted as 'tree_switch' instead."""
    return Counter(row_classes(items, cfg).values())


def line(status_text, items, cfg, top=5):
    hosts = host_idle(status_text)
    cores = sum(h["cores"] for h in hosts.values())
    idle = sum(h["idle"] for h in hosts.values())
    per = " ".join(f"{h}={v['idle']}(load {v['load']:.0f}/{v['cores']}" + (f", thr {v['committed']}" if v["committed"] is not None else "") + ")"
                   for h, v in sorted(hosts.items(), key=lambda kv: -kv[1]["idle"]))
    holds = hold_counts(items, cfg)
    sup = holds.pop("superseded", 0)
    ranked = ", ".join(f"{k}={n}" for k, n in holds.most_common(top)) or "none"
    pct = (100.0 * (cores - idle) / cores) if cores else 0.0
    return (f"UNDER-USE idle {idle} of {cores} threads (used {pct:.0f}%): {per or 'no host status'} | "
            f"rows not launching {sum(holds.values())}: {ranked} | superseded-event rows (not counted, retire or relaunch) {sup}")


NEEDS_ACTION_TICKS = 3


def track(state, classes, now):
    """state {"rows": {key: [class, ticks]}, "posted": {class: t}}; a row in the same non-hold gate class for NEEDS_ACTION_TICKS ticks
    -> returns {class: n rows} not yet posted (the caller posts one NEEDS-ACTION per class and marks it posted)"""
    rows = state.setdefault("rows", {})
    posted = state.setdefault("posted", {})
    for k in [k for k in rows if k not in classes]:
        del rows[k]
    for k, c in classes.items():
        rows[k] = [c, rows[k][1] + 1 if k in rows and rows[k][0] == c else 1]
    for c in [c for c in posted if not any(v[0] == c for v in rows.values())]:
        del posted[c]                                   # class cleared: a recurrence posts again
    due = Counter(v[0] for v in rows.values() if v[1] >= NEEDS_ACTION_TICKS and v[0].startswith("gate:") and v[0] not in posted)
    for c in due:
        posted[c] = now
    return dict(due)


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
        try:
            sp = ap_dir / "under_use_state.json"
            try:
                state = json.loads(sp.read_text())
            except (OSError, ValueError):
                state = {}
            due = track(state, row_classes(items, cfg), time.time())
            sp.write_text(json.dumps(state))
            for c, n in sorted(due.items()):
                AP.coord_append("lanes/COORD-REVIEW-QUEUE.md",
                                f"- {time.strftime('%Y-%m-%d %H:%M %Z')} NEEDS-ACTION [AUTOPILOT -> COORD] UNDER-USE: {n} row(s) "
                                f"waited {NEEDS_ACTION_TICKS}+ ticks at launch gate '{c}' with no hold naming it")
        except Exception as e:
            AP.log(f"UNDER-USE needs-action skipped: {type(e).__name__}: {e}")
    except Exception as e:
        AP.log(f"UNDER-USE failed: {type(e).__name__}: {e}")
