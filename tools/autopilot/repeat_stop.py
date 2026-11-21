"""repeat_stop.py -- REPEAT-STOP (FLOW-HEALTH-1 11-16, FABLE-FLOW-0513 class 3, COORD): one failure ledger per item across gen AND route.

  fingerprint   stage + class + the identifying object: DRT-0255 / 0206 -> net name + routeBox; post-CTS gate -> gate name + worst endpoint
                group; gen / kit -> exception type + the file or module named.  Item / type names, numbers and hosts are not part of it.
  3 identical fingerprints in a row           -> BLOCKED-REPEAT:<fp>
  6 attempts in 24 h, none reached a later stage than the item's best before them -> STALLED
  release       only when one of the item's OWN inputs hashes differently from the attempt that last produced the fingerprint, or on a named
                `unblock <item> <fp>` line.  A die-wide overlay or tools change alone never releases.
  OOM kill      first one: resubmit with place memory x1.5 (mem_x); a second identical OOM blocks.
Pure functions over a state dict (st["repeat_ledger"]); no I/O.  kit_wave.py wires them to the FAIL record, the queue-result record and the launch gate.
"""
import re
import time

import flow_guard as FG

IDENT_N = 3                 # identical fingerprints in a row
STALL_N = 6                 # attempts without a later stage ...
STALL_WINDOW_S = 24 * 3600  # ... within this window
OOM_FACTOR = 1.5
TOTAL_CAP = 6               # FLOW-NOADV-R4: failed attempts per item per plan event, any mix of fingerprints / OOM; then the row goes to its owner as PLAN
CAP_STATE = "BLOCKED-CAP"
TOOL_MIX_IDENT_N = 2        # a deterministic tool_mix error (INFRA class too) repeating on 2 attempts is a stop, not an infra retry
OOM_RE = re.compile(r"infra-oom|earlyoom|\bOOM\b|oom-kill|Out of memory|exit 137|rc[ =]+137|Error 24[17]", re.I)
NET_RE = re.compile(r"\bnet\s+([A-Za-z0-9_./\[\]\\$:-]+)")
BOX_RE = re.compile(r"routeBox\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)")
GATE_RE = re.compile(r"(FAIL_POSTCTS\s+\w+|OT_POSTCTS_GATE\s+\w+\s+\([^)]*\)|SETUP_TRIAGE|HOLD_STRUCTURAL)")
ENDPT_RE = re.compile(r"(pinreg\s+\w+|worst endpoint[s]?:?\s*[\w./\[\]$-]+|endpoint group\s+[\w./-]+)")
EXC_RE = re.compile(r"\b([A-Za-z_][\w.]*(?:Error|Exception))\b:?\s*(.{0,120})")
FILE_RE = re.compile(r"([\w.-]+\.(?:py|sv|svh|v|tcl|json|sdc|lib|lef|def|odb|f|mk))\b")


def lkey(die, item, event=None):
    """ledger key: item@event (FABLE-FLOW-2000 a: 69 live item names exist on several events; a stop / counter / hold of one event never hits another)"""
    return f"{die}|{item}@{event}" if event else f"{die}|{item}"


def lookup(st, die, item, event=None):
    """the item@event ledger row; a stop recorded before the key carried the event (legacy die|item) still holds until it is released"""
    L = st.get("repeat_ledger") or {}
    e = L.get(lkey(die, item, event))
    old = L.get(lkey(die, item)) if event else None
    return old if (not e or not e.get("state")) and old and old.get("state") else e


def led(st):
    return st.setdefault("repeat_ledger", {})


def is_oom(cls, why):
    return bool(OOM_RE.search(str(why or "")))


def fingerprint(stage, cls, why):
    """stage|class|object  (see the module doc)"""
    why = str(why or "")
    stage = str(stage or "").split()[0] if str(stage or "").strip() else "?"
    cls = str(cls or "")
    obj = ""
    m = re.search(r"DRT-0(?:255|206|073)", why)
    if m:
        net = NET_RE.search(why)
        box = BOX_RE.search(why)
        obj = f"{m.group(0)} net {net.group(1) if net else '?'} box {' '.join(box.groups()) if box else '?'}"
    elif GATE_RE.search(why) and re.search(r"POSTCTS|post-cts|SETUP_TRIAGE|HOLD_STRUCTURAL", why, re.I):
        g = GATE_RE.search(why).group(1)
        e = ENDPT_RE.search(why)
        obj = f"{re.sub(r'[0-9]+', 'N', g)} {e.group(1) if e else ''}".strip()
    elif is_oom(cls, why):
        obj = "OOM"
    elif cls == "PLAN" and " @" in why:
        # FLOW-0035: a PLAN-class failure is named by its plan cause (the text before " @<stage>:"), not by the tool noise after it: qkd_pv_fin_s8_pin alternated two evidence texts
        # ("import json,sys;..." / "CORE_VIEW FAIL <id>@") for the same cause, so 3 identical fingerprints in a row never happened (attempt 25)
        obj = re.sub(r"\s+", " ", why.split(" @", 1)[0])[:100]
    else:
        e = EXC_RE.search(why)
        f = FILE_RE.findall(why)
        if e:
            obj = e.group(1) + " " + (f[0] if f else re.sub(r"\s+", " ", re.sub(r"\d+", "N", e.group(2)))[:60])
        else:
            obj = FG.norm_class(cls, why)[:100]
    return f"{stage}|{cls}|{obj}"[:200]


def ident(fp):
    """the fingerprint without its class label: stage|obj (FLOW-NOADV-R2 11-20: a relabel of the same cause keeps the streak)"""
    parts = str(fp).split("|", 2)
    if len(parts) < 3:
        return str(fp)
    return parts[0] + "|" + re.sub(r"^[A-Z][A-Z0-9_-]*: ", "", parts[2])


def _best_rank(attempts, before=None):
    ranks = [a["rank"] for a in attempts if before is None or a["t"] < before]
    return max(ranks) if ranks else -1


def record(st, die, item, attempt, stage, cls, why, inputs=None, t=None, ok=False, event=None, ident_n=None, attempts_hint=0):
    """one attempt outcome -> event dict or None (see _record); plus the TOTAL_CAP stop: distinct failed attempts of one plan event, any mix of
    fingerprints / OOM kills, block the row as a PLAN item for its owner (a repeat / stall verdict of the same attempt wins)."""
    ev = _record(st, die, item, attempt, stage, cls, why, inputs=inputs, t=t, ok=ok, event=event, ident_n=ident_n)
    if ev and ident_n and ev["event"] == "BLOCKED-REPEAT":
        led(st)[lkey(die, item, event)]["tool_mix"] = True       # kit_wave's INFRA release keeps this stop: the error is deterministic, not a host fault
    if ok or event is None:
        return ev
    e = led(st)[lkey(die, item, event)]
    tot = e.get("tot")
    if not isinstance(tot, dict) or tot.get("event") != (event or ""):
        tot = e["tot"] = {"event": event or "", "n": []}
    if attempt not in tot["n"]:
        tot["n"].append(attempt)
    n_tot = max(len(tot["n"]), int(attempts_hint or 0))      # a row that already ran many attempts before the cap existed counts by its attempt number
    if n_tot >= TOTAL_CAP and not e["state"]:
        return _block(e, CAP_STATE, "cap|%d attempts" % n_tot, e["att"][-1],
                      why=f"{n_tot} failed attempts in plan event {event or '?'} (mixed errors): PLAN item for the owner")
    return ev


def _record(st, die, item, attempt, stage, cls, why, inputs=None, t=None, ok=False, event=None, ident_n=None):
    """one attempt outcome (ok=True: it got past its stage, e.g. ENQUEUE).  -> event dict or None:
    {'event': 'BLOCKED-REPEAT'|'STALLED'|'OOM-RESUBMIT', 'fp': ..., ...}.  An attempt is recorded once per (attempt, stage, fp)."""
    t = time.time() if t is None else t
    key = lkey(die, item, event)
    e = led(st).setdefault(key, {"att": [], "state": "", "mem_x": 1.0, "oom": 0})
    fp = "ok" if ok else fingerprint(stage, cls, why)
    rank = FG.stage_rank(str(stage or "").split()[0]) + (1 if ok else 0)
    if any(a["n"] == attempt and a["stage"] == stage and a["fp"] == fp for a in e["att"]):
        return None
    e["att"].append({"n": attempt, "t": t, "stage": stage, "rank": rank, "cls": cls, "fp": fp, "inputs": dict(inputs or {}), "oom": (not ok) and is_oom(cls, why)})
    del e["att"][:-40]
    if ok or e["state"]:
        return None
    last = e["att"][-1]
    if last["oom"]:
        e["oom"] += 1
        same = [a for a in e["att"] if a["oom"]]
        if e["oom"] == 1:
            e["mem_x"] = OOM_FACTOR
            return {"event": "OOM-RESUBMIT", "fp": fp, "mem_x": e["mem_x"]}
        # COORD 11-19 (FLOW-1803 4): an OOM is the host's / the memory budget's verdict, never a repeat failure: it raises the memory factor and retries, it never blocks the row
        if e["oom"] >= 2 and e["mem_x"] < OOM_FACTOR * 2:
            e["mem_x"] = round(e["mem_x"] * OOM_FACTOR, 2)
            return {"event": "OOM-RESUBMIT", "fp": fp, "mem_x": e["mem_x"]}
        return None
    n_id = ident_n or IDENT_N
    tail = [ident(a["fp"]) if a["fp"] != "ok" else "ok" for a in e["att"][-n_id:]]
    if len(tail) == n_id and len(set(tail)) == 1 and tail[0] != "ok":
        return _block(e, "BLOCKED-REPEAT", fp, last, why=f"{n_id} identical fingerprints in a row")
    win = [a for a in e["att"] if t - a["t"] <= STALL_WINDOW_S and not a["oom"]]
    if len(win) >= STALL_N:
        win = win[-STALL_N:]
        before = _best_rank(e["att"], before=win[0]["t"])
        if max(a["rank"] for a in win) <= before or (before < 0 and len({a["rank"] for a in win}) == 1):
            return _block(e, "STALLED", fp, last, why=f"{STALL_N} attempts in 24 h, none reached a later stage than {before}")
    return None


def _block(e, state, fp, last, why):
    e["state"], e["fp"], e["inputs"], e["why"] = state, fp, dict(last.get("inputs") or {}), why
    e["blocked_at"] = last["t"]
    return {"event": state, "fp": fp, "why": why}


def gate(st, die, item, current_inputs, unblocks=(), event=None):
    """launch gate -> (blocked, why, released_by).  Released by a changed own input hash or a named `unblock <item> <fp>` line."""
    e = lookup(st, die, item, event)
    if not e or not e.get("state"):
        return False, "", ""
    fp = e.get("fp", "")
    if (item, fp) in set(unblocks) or any(u[0] == item and (u[1] == "*" or fp.startswith(u[1])) for u in unblocks):
        release(e, "unblock line")
        return False, "", "unblock"
    if e["state"] == CAP_STATE:                 # an input change does not release a cap stop: only a new plan event or an unblock line
        if event and (e.get("tot") or {}).get("event") != event:
            release(e, "plan event changed")
            return False, "", "event"
        return True, f"{CAP_STATE}:{fp} ({e.get('why')}); released only by a new plan event or an `unblock {item} cap` line", ""
    old = e.get("inputs") or {}
    changed = sorted(k for k, v in (current_inputs or {}).items() if k in old and old[k] != v)
    changed += sorted(k for k in (current_inputs or {}) if k not in old and old and (current_inputs or {}).get(k))
    if changed:
        release(e, "input changed: " + ",".join(changed[:4]))
        return False, "", "inputs:" + ",".join(changed[:4])
    return True, f"{e['state']}:{fp} ({e.get('why')}); released only by a changed own input or an `unblock {item} <fp>` line", ""


def release(e, why):
    e["released"], e["released_fp"] = why, e.get("fp", "")
    e["state"], e["fp"] = "", ""
    e["oom"] = 0
    e.pop("tool_mix", None)
    if why in ("plan event changed", "unblock line"):
        e["tot"] = {}
    e["att"] = [a for a in e["att"]][-1:]          # the streak starts again; the last attempt stays for the stage-rank history
    if e["att"]:
        e["att"][0]["fp"] = "released"


def mem_x(st, die, item, event=None):
    e = lookup(st, die, item, event) or {}
    return float(e.get("mem_x") or 1.0)


def parse_unblocks(text):
    """`unblock <item> <fp-prefix | *>` lines of the queue -> [(item, fp)]"""
    return [(m.group(1), m.group(2)) for m in re.finditer(r"(?m)\bunblock\s+(\S+)\s+(\S+)", text or "")]


def state_of(st, die, item, event=None):
    e = lookup(st, die, item, event) or {}
    return (e.get("state") or "", e.get("fp") or "")
