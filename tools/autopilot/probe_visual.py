"""probe_visual.py -- PROBE-THROUGH kits feed lanes/VISUAL-QUEUE.tsv (VIS-REOWN, COORD flow review 11-24 08:55).

COORD 08:04 ruling (2) turned past-SLA DRAFT / PRE-PASS rows of lanes/VIS-COVERAGE.tsv into PROBE-THROUGH: lbl_gate admits
their kits, so they place, route and sign off with no review on the way.  This module lists, for every PROBE-THROUGH type,
its newest kit that has reached place (a geom dir exists) and is not finished, so kit_wave.visual_queue_publish adds it to
lanes/VISUAL-QUEUE.tsv (same 8 columns; state WAIT-VISUAL-PROBE-PLACE or WAIT-VISUAL-PROBE-GRT).  Two sources:
  wave records    (kit_wave state items: geom_dir set, not SIGNED / FAIL / CANCELLED)
  private kits    (~/coord/autopilot/private_specs/<lane>/<spec>/result.json, newer than MAX_AGE_S, with geom_dir)
A type leaves the queue when its VIS-COVERAGE row leaves PROBE-THROUGH (the reviewer sets PROBE-PASS or FAIL).
The list is advisory: it never holds, cancels or launches anything (OWNER: probes never wait, review never blocks).
Stdlib only.
"""
import glob
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))) if os.path.dirname(os.path.abspath(__file__)) not in sys.path else None
import lbl_gate as LBL  # noqa: E402

MAX_AGE_S = 48 * 3600
GRT_STAGES = ("grt", "route", "finish", "signoff", "lec", "cts")      # cts: GRT renders follow; the kit is past place
DONE_VERDICTS = ("SIGNED",)
DONE_STATUS = ("SIGNED", "FAIL", "CANCELLED")
DIE_OF_VIS = {v: k for k, v in (("s81", "S81"), ("s81_head", "HEAD"), ("qwen_kvsys", "KV"), ("qwen_compute", "QC"))}


def probe_types(coord):
    """VIS-COVERAGE rows of the coord dir -> parsed rows (or [] when unreadable)"""
    try:
        with open(os.path.join(coord, LBL.REL), encoding="utf-8", errors="replace") as f:
            return LBL.parse(f.read())
    except OSError:
        return []


def is_probe_through(vis, die, item):
    st, _ = LBL.lookup(vis, item, die)
    return st == "PROBE-THROUGH"


def _row(die, item, family, attempt, state, kit, geom_dir):
    host = kit.partition(":")[0] if ":" in kit else (geom_dir.partition(":")[0] if ":" in geom_dir else "")
    return (die, item, family, str(attempt), state, f"{kit}/run/layout_review" if kit else "",
            f"{geom_dir}/auto_geom.png" if geom_dir else "", host)


def private_rows(coord, vis, now=None, family=lambda die, item: item):
    """newest private kit per (die, item) of a PROBE-THROUGH type that reached place and is not finished"""
    now = time.time() if now is None else now
    best = {}
    for r in glob.glob(os.path.join(coord, "autopilot", "private_specs", "*", "*", "result.json")):
        try:
            mt = os.path.getmtime(r)
            if now - mt > MAX_AGE_S:
                continue
            with open(r) as f:
                d = json.load(f)
        except (OSError, ValueError):
            continue
        die, item, gd = str(d.get("die") or ""), str(d.get("item") or ""), str(d.get("geom_dir") or "")
        if not (die and item and gd) or str(d.get("verdict") or "").upper() in DONE_VERDICTS:
            continue
        if not is_probe_through(vis, die, item):
            continue
        k = (die, item)
        if k in best and best[k][0] >= mt:
            continue
        stage = str(d.get("stage") or "").lower()
        state = "WAIT-VISUAL-PROBE-GRT" if stage in GRT_STAGES else "WAIT-VISUAL-PROBE-PLACE"
        if str(d.get("verdict") or "").upper() == "FAIL":
            state += "-FAILED"                                   # a failed probe is the most useful render to look at
        spec = os.path.basename(os.path.dirname(r))
        best[k] = (mt, _row(die, item, family(die, item), spec, state, str(d.get("kit") or ""), gd))
    return [v[1] for v in best.values()]


def wave_rows(items, vis, kit_location, family=lambda die, item: item, skip=()):
    """wave records of PROBE-THROUGH types with a place render that are still in flight (skip: (die, item) already listed)"""
    out = {}
    for rec in (items or {}).values():
        die, item = str(rec.get("die") or ""), str(rec.get("item") or "")
        if not die or (die, item) in skip or not rec.get("geom_dir"):
            continue
        if rec.get("status") in DONE_STATUS or rec.get("q_status") in DONE_STATUS:
            continue
        if not is_probe_through(vis, die, item):
            continue
        a = int(rec.get("attempt") or 0)
        if (die, item) in out and int(out[(die, item)][3]) >= a:
            continue
        state = "WAIT-VISUAL-PROBE-GRT" if rec.get("status") == "ENQUEUED" else "WAIT-VISUAL-PROBE-PLACE"
        out[(die, item)] = _row(die, item, family(die, item), a, state, kit_location(rec) or "", str(rec.get("geom_dir")))
    return list(out.values())


def rows_for_queue(coord, items, kit_location, family=lambda die, item: item, listed=(), now=None):
    """all probe rows for VISUAL-QUEUE.tsv; listed = {(die, item)} already in the queue (not repeated)"""
    vis = probe_types(coord)
    if not vis:
        return []
    listed = set(listed)
    w = wave_rows(items, vis, kit_location, family, skip=listed)
    seen = listed | {(r[0], r[1]) for r in w}
    p = [r for r in private_rows(coord, vis, now=now, family=family) if (r[0], r[1]) not in seen]
    return sorted(w + p)


if __name__ == "__main__":                                   # dry list on the hub: python3 -I probe_visual.py [coord]
    c = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/coord")
    for r in rows_for_queue(c, {}, lambda rec: ""):
        print("\t".join(r))
