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
        out[m.group(1)] = dict(cores=cores, load=load, committed=committed, idle=max(0, int(round(cores - used))),
                               cpu_idle=max(0, int(round(cores - load))))     # FABLE-FLOW-0000 F6: measured, not requested
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


CPU_LOW_PCT = 70.0     # F6: measured CPU under this with launchable rows waiting -> name the blocking bucket


def line(status_text, items, cfg, top=5):
    """FLOW-FLEET-R1 11-22 (FABLE-FLOW-0000 F6, 2nd report: 'idle 0 of 624 threads (used 100 %)' while load was 390 of 736): the headline is
    MEASURED CPU (load average per host); the admission thread commitment is shown next to it.  CPU under 70 % with launchable rows waiting
    names the blocking bucket (the most common launch-gate / hold class)."""
    hosts = host_idle(status_text)
    cores = sum(h["cores"] for h in hosts.values())
    load = sum(h["load"] for h in hosts.values())
    cpu_idle = sum(h["cpu_idle"] for h in hosts.values())
    committed = sum(h["committed"] or 0 for h in hosts.values())
    per = " ".join(f"{h}=cpu {v['load']:.0f}/{v['cores']}" + (f" thr {v['committed']}" if v["committed"] is not None else "")
                   for h, v in sorted(hosts.items(), key=lambda kv: -kv[1]["cpu_idle"]))
    holds = hold_counts(items, cfg)
    sup = holds.pop("superseded", 0)
    ranked = ", ".join(f"{k}={n}" for k, n in holds.most_common(top)) or "none"
    pct = (100.0 * load / cores) if cores else 0.0
    cpct = (100.0 * committed / cores) if cores else 0.0
    waiting = Counter({k: n for k, n in holds.items() if WAITING_GATE_RE.match(k)})
    blocked = ""
    if cores and pct < CPU_LOW_PCT and sum(holds.values()):
        b, n = (waiting or holds).most_common(1)[0]
        blocked = (f" | BLOCKED: cpu {pct:.0f}% < {CPU_LOW_PCT:.0f}% with {sum(holds.values())} row(s) not launching "
                   f"({sum(waiting.values())} waiting for admission); top bucket {b}={n}")
    return (f"UNDER-USE cpu idle {cpu_idle} of {cores} cores (load {load:.0f}, used {pct:.0f}%), threads committed {committed} ({cpct:.0f}%): "
            f"{per or 'no host status'} | rows not launching {sum(holds.values())}: {ranked} | "
            f"superseded-event rows (not counted, retire or relaunch) {sup}{blocked}")


NEEDS_ACTION_TICKS = 3

# FABLE-FLOW-0230 U1 (FLOW-FLEET-R1 11-22): 187-194 rows not launching while 35-43 % of cores idle; SKIP-HELD 75 and WAIT-FORM 42 were one
# number each, with no key, owner or age.  held_detail() splits them by hold key (SKIP-HELD / hold_items: the die hold_items pattern; WAIT-FORM:
# the die, one key per die) with owner (owner= in the hold text, else the die lane), eta (eta= in the text) and age (oldest row held since);
# a key with no owner, past its eta, or older than STALE_HOLD_H without an eta is FLAGGED.
HOLD_OWNER_RE = re.compile(r"\bowner\s*[=:]\s*([A-Za-z0-9_.-]+)", re.I)
HOLD_ETA_RE = re.compile(r"\beta\s*[=:]\s*(\d{4}-\d\d-\d\d(?:[ T]\d\d:\d\d)?)", re.I)
SKIP_PAT_RE = re.compile(r"^SKIP-HELD: item held \((.*?)\): ?(.*)$", re.S)
STALE_HOLD_H = 24.0


def _eta(text):
    m = HOLD_ETA_RE.search(str(text or ""))
    if not m:
        return None
    v = m.group(1).replace("T", " ")
    try:
        return time.mktime(time.strptime(v, "%Y-%m-%d %H:%M" if " " in v else "%Y-%m-%d")) + (0 if " " in v else 86399)
    except ValueError:
        return None


def held_detail(items, cfg, now=None):
    """-> [{bucket, die, key, n, owner, eta, age_h, flags, why}] for SKIP-HELD / hold_items rows and WAIT-FORM rows, largest first"""
    now = time.time() if now is None else now
    dies = (cfg or {}).get("dies") or {}
    g = {}
    for rec in (items or {}).values():
        st, die = rec.get("status"), rec.get("die")
        d = dies.get(die) or {}
        hold = str(rec.get("route_hold") or "")
        bucket = key = why = None
        m = SKIP_PAT_RE.match(hold) if st in HELD else None
        if m:
            bucket, key = "SKIP-HELD", m.group(1)
            why = str((d.get("hold_items") or {}).get(key) or m.group(2))
        elif st in HELD and hold.startswith("WAIT-FORM"):
            bucket, key, why = "WAIT-FORM", "visual verdict BAD/ISSUES, form unchanged", hold
        elif st in ELIGIBLE and not (d.get("event") and rec.get("event") and rec.get("event") != d.get("event")):
            item = str(rec.get("item") or "")
            hit = next(((pat, w) for pat, w in (d.get("hold_items") or {}).items() if fnmatch.fnmatchcase(item, pat)), None)
            if hit:
                bucket, key, why = "SKIP-HELD", hit[0], str(hit[1])
        if not bucket:
            continue
        e = g.setdefault((bucket, die, key), {"bucket": bucket, "die": die, "key": key, "n": 0, "why": why, "since": now})
        e["n"] += 1
        e["since"] = min(e["since"], float(rec.get("updated") or rec.get("started") or now) or now)
    out = []
    for e in g.values():
        m = HOLD_OWNER_RE.search(e["why"] or "")
        lane = (dies.get(e["die"]) or {}).get("lane") or ""
        owner = m.group(1) if m else ("" if e["bucket"] == "SKIP-HELD" else lane)
        eta = _eta(e["why"])
        age = max(0.0, (now - e["since"]) / 3600.0)
        flags = []
        if not owner:
            flags.append("NO-OWNER")
        if eta is not None and eta < now:
            flags.append("OVERDUE")
        if eta is None and age >= STALE_HOLD_H:
            flags.append(f"NO-ETA>{STALE_HOLD_H:g}h")
        out.append(dict(bucket=e["bucket"], die=e["die"], key=e["key"], n=e["n"], owner=owner or (lane and f"(die lane {lane})") or "", eta=eta,
                        age_h=round(age, 1), flags=flags, why=str(e["why"] or "")[:120]))
    return sorted(out, key=lambda x: (x["bucket"], -x["n"], -x["age_h"]))


HOLD_ROW_H = 24.0


def die_owner_lane(cfg, die):
    """the die owner lane of kit_wave.json (dies.<die>.die_owner, else the lane in owner_lane '(...)'), never a KIT-WAVE lane"""
    d = ((cfg or {}).get("dies") or {}).get(die) or {}
    if d.get("die_owner"):
        return str(d["die_owner"])
    m = re.search(r"\(([A-Z][A-Z0-9-]+)\)", str(d.get("owner_lane") or ""))
    return m.group(1) if m else f"{die} die owner (unnamed)"


def hold_owner_rows(detail, cfg, dies=None, now=None):
    """HOLD-OWNER-1122 (FABLE-FLOW-0350 U1: 59 hold keys with no owner or no term held 184 rows while 30-39 % of cores idled; the UNDER-USE
    flag was a report nothing acted on): a hold key with no release term (no eta=) for >= HOLD_ROW_H, or with no owner, held that long,
    becomes one OWNERS row (kind hold, state FIX) assigned to the die owner lane, with its row count, age and the hold text.  Parked dies
    are left out.  dies = the die names OWNERS.tsv knows (others skipped).  -> [row dict in ownership.TSV_COLS]"""
    now = time.time() if now is None else now
    out = []
    for x in detail or []:
        d = ((cfg or {}).get("dies") or {}).get(x["die"]) or {}
        if (dies is not None and x["die"] not in dies) or (isinstance(d, dict) and d.get("parked")):
            continue
        if x["age_h"] < HOLD_ROW_H or x["eta"] is not None:
            continue
        lane = die_owner_lane(cfg, x["die"])
        named = x["owner"] if x["owner"] and not str(x["owner"]).startswith("(") and "NO-OWNER" not in x["flags"] else ""
        out.append({"die": x["die"], "item": f"HOLD {x['bucket']} {x['key']}", "kind": "hold", "state": "FIX", "owner": lane, "live_job": "none",
                    "last_activity": f"{int(x['age_h'] * 60)}m",
                    "next_step": (f"{x['n']} row(s) held {x['age_h']} h with no release term" + (f" (hold names {named})" if named else " and no owner")
                                  + ": set owner=<lane> eta=<YYYY-mm-dd HH:MM> on the hold, or drop it (HOLD-ORPHAN release then applies)"),
                    "evidence": x["why"], "default_owner": lane, "replicas": x["n"], "members": ""})
    return out


def held_line(detail, top=8):
    """'UNDER-USE HELD SKIP-HELD 75: s81/hd_* 40 [owner X, 26.1 h, FLAGGED NO-OWNER] ...; WAIT-FORM 42: ...'"""
    if not detail:
        return "UNDER-USE HELD none"
    parts = []
    for b in ("SKIP-HELD", "WAIT-FORM"):
        rows = [x for x in detail if x["bucket"] == b]
        if not rows:
            continue
        parts.append(f"{b} {sum(x['n'] for x in rows)}: " + "; ".join(
            f"{x['die']}/{x['key']} {x['n']} [owner {x['owner'] or '-'}, {x['age_h']} h"
            + (f", eta {time.strftime('%m-%d %H:%M', time.localtime(x['eta']))}" if x["eta"] else "")
            + (f", FLAGGED {'+'.join(x['flags'])}" if x["flags"] else "") + "]" for x in rows[:top])
            + (f"; +{len(rows) - top} more key(s)" if len(rows) > top else ""))
    flagged = sum(1 for x in detail if x["flags"])
    return "UNDER-USE HELD " + " | ".join(parts) + f" | flagged keys {flagged}"


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
        try:                                             # FABLE-FLOW-0230 U1: held rows by key, owner, age; flagged keys posted once
            det = held_detail(items, cfg)
            AP.log(held_line(det))
            sp_ = ap_dir / "under_use_state.json"
            try:
                st_ = json.loads(sp_.read_text())
            except (OSError, ValueError):
                st_ = {}
            seen = st_.setdefault("held_flag_posted", {})
            new = [x for x in det if x["flags"] and seen.get(f"{x['bucket']}|{x['die']}|{x['key']}") != "+".join(x["flags"])
                   and not ((cfg.get("dies") or {}).get(x["die"]) or {}).get("parked")]
            if new:                                      # HOLD-OWNER-1122: an unowned hold goes to the die owner lane, not COORD only
                AP.coord_append("lanes/COORD-REVIEW-QUEUE.md",
                                f"- {time.strftime('%Y-%m-%d %H:%M %Z')} NEEDS-ACTION [AUTOPILOT -> " + ", ".join(sorted({
                                    (x['owner'] if x['owner'] and not str(x['owner']).startswith('(') and 'NO-OWNER' not in x['flags'] else die_owner_lane(cfg, x['die']))
                                    for x in new})) + ", COORD] "
                                + "HELD rows: " + "; ".join(f"{x['bucket']} {x['die']}/{x['key']} {x['n']} row(s) {x['age_h']} h {'+'.join(x['flags'])}" for x in new[:15])[:1500]
                                + " -- set owner= and eta= on the hold, or release it")
                for x in new:
                    seen[f"{x['bucket']}|{x['die']}|{x['key']}"] = "+".join(x["flags"])
                sp_.write_text(json.dumps(st_))
        except Exception as e:
            AP.log(f"UNDER-USE HELD skipped: {type(e).__name__}: {e}")
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
