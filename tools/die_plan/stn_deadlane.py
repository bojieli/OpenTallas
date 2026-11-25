#!/usr/bin/env python3
"""stn_deadlane.py -- STN-DEADLANE (KV-OWN-PV-R2 11-25, COORD): internal-station rows on a lane that carries 0 bits.

KV A5t8 bind3 stopped in native_istations.annotate: 'native stations pv_N_2 (kv3_pv_v2n).o_astk_E..owner_response_data:
expected one outgoing lane'.  The plan still had lane L55 for that bus, but the bind gave it 0 items (on A5t7 it only carried
forwarded vport_WN_3 out_v_lo bits; on A5t8 forward() routes them elsewhere), so the lane went to lanes_unused, never into
links, and the type's internal_stations row on that bus had no outgoing link.  The bind stops at the FIRST such row, so a die
with 14 types carrying the row fails one rebind at a time.

This tool finds them all in ONE run with the bind's own rule: it runs the bind head (bind._bind_through_landings: map_cells,
analyse, build_buses: the same lane items / links / out_bus the strict bind builds) and stops at native_istations.annotate,
which it replaces by a collector.  For every partition of a type with internal_stations rows (native or kit-built) and every
OUT-bus row (conn bus:<oname>, oname an 'out' bus of the type) it records the outgoing links of that partition with that oname:

  DEAD      0 links (the plan lane, if any, carried 0 bound bits: lanes_unused)   -> the bind's 'expected one outgoing lane'
  MULTI     >1 links                                                           -> the same bind error
  OK        exactly 1

A row is DEAD-TYPE when it is DEAD on every partition of its type (and of its split variants that share the row): removing
the row is latency-neutral (no bits ride it).  A row DEAD on some partitions only is DEAD-PARTIAL: a shared type cannot drop it;
it needs a per-instance decision (type split or a carrying lane) and is listed, not fixed.

    stn_deadlane.py PLAN --asbuilt AB --elab ELABDIR --out OUT [--ops OPS.json] [--row NAME] [--types RE]

ELABDIR holds the elab's asbuilt.json (bind.py elab --out); it is read, never written (asbuilt.json is linked into OUT).
Writes OUT/stn_deadlane.json and, with --ops, a plan_ops.v1 row (row_gate.py ops: / compose apply) that removes every
DEAD-TYPE row.  Prints one line per finding: 'STN-DEADLANE DEAD-TYPE <type> <bus> parts=..', '.. DEAD-PARTIAL ..', '.. MULTI ..'.
Exit 0 = no findings, 1 = findings, 2 = the head failed before annotate.  Report-only: it never changes a plan in place."""
import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


class _Stop(Exception):
    pass


def collect(b, types_re=None):
    """-> [{part, type, bus, links, lanes, state}] for every out-bus internal_stations row of every partition"""
    rows = []
    rx = re.compile(types_re) if types_re else None
    for part, p in sorted(b.parts.items()):
        tn = p.get("type")
        t = b.types.get(tn) or {}
        if rx and not rx.fullmatch(tn or ""):
            continue
        outs = {x["name"] for x in t.get("buses", []) if x.get("dir") == "out"}
        seen = set()
        for e in t.get("internal_stations", []):
            conn = e.get("conn", "")
            if not conn.startswith("bus:"):
                continue
            name = conn[4:]
            if name not in outs or name in seen:
                continue
            seen.add(name)
            m = [L for L in b.out_bus.get(part, []) if L.get("oname") == name]
            rows.append(dict(part=part, type=tn, bus=name, links=len(m), lanes=sorted({str(L.get("lane")) for L in m}),
                             state="OK" if len(m) == 1 else ("DEAD" if not m else "MULTI")))
    return rows


def classify(rows):
    """-> {(type, bus): {state, parts, dead_parts}}; DEAD-TYPE when every partition of the type is DEAD on the bus"""
    by = {}
    for r in rows:
        k = (r["type"], r["bus"])
        g = by.setdefault(k, dict(parts=[], dead=[], multi=[]))
        g["parts"].append(r["part"])
        if r["state"] == "DEAD":
            g["dead"].append(r["part"])
        elif r["state"] == "MULTI":
            g["multi"].append(r["part"])
    out = {}
    for k, g in sorted(by.items()):
        if g["multi"]:
            st = "MULTI"
        elif g["dead"] and len(g["dead"]) == len(g["parts"]):
            st = "DEAD-TYPE"
        elif g["dead"]:
            st = "DEAD-PARTIAL"
        else:
            continue
        out[k] = dict(state=st, parts=g["parts"], dead_parts=g["dead"], multi_parts=g["multi"])
    return out


def ops_for(raw, found, row="KV-OWN-PV-R2-STN-DEADLANE"):
    """plan_ops.v1 replace ops removing every DEAD-TYPE row (one op per type: its internal_stations list)"""
    dead = {}
    for (tn, bus), f in found.items():
        if f["state"] == "DEAD-TYPE":
            dead.setdefault(tn, set()).add("bus:" + bus)
    ops = []
    for tn, conns in sorted(dead.items()):
        st = raw["partition_types"][tn].get("internal_stations", [])
        keep = [s for s in st if s.get("conn") not in conns]
        ops.append(dict(op="replace", path=f"/partition_types/{tn}/internal_stations", old=st, value=keep,
                        note=f"drop {len(st) - len(keep)} row(s) on 0-bit lanes: {sorted(conns)}"))
    return dict(schema="plan_ops.v1", row=row, ops=ops)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan")
    ap.add_argument("--asbuilt", required=True)
    ap.add_argument("--elab", required=True, help="elab output dir holding asbuilt.json (read only)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--ops")
    ap.add_argument("--row", default="KV-OWN-PV-R2-STN-DEADLANE")
    ap.add_argument("--types")
    ap.add_argument("--mem", default="48")
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    src = Path(a.elab) / "asbuilt.json"
    if not src.is_file():
        print(f"STN-DEADLANE not checked: no {src} (run bind.py elab first)")
        return 2
    dst = out / "asbuilt.json"
    if not dst.exists():
        os.symlink(src.resolve(), dst)
    import bind
    import native_istations as NI
    bind._AB_OVERRIDE["path"] = a.asbuilt
    box = {}

    def _collect(b):
        box["rows"] = collect(b, a.types)
        raise _Stop()

    NI.annotate = _collect
    ns = argparse.Namespace(plan=a.plan, out=str(out), asbuilt=a.asbuilt, strict=True, all_gaps=True, mem=a.mem, types=None,
                            cmd="bind")
    try:
        bind._bind_through_landings(ns)
    except _Stop:
        pass
    except Exception as exc:  # noqa: BLE001 a head error before annotate: report, no verdict
        print(f"STN-DEADLANE not checked: bind head failed before annotate: {type(exc).__name__}: {str(exc)[:300]}")
        return 2
    if "rows" not in box:
        print("STN-DEADLANE not checked: the bind head ended without reaching native_istations.annotate")
        return 2
    raw = json.loads(Path(a.plan).read_text())
    found = classify(box["rows"])
    rep = dict(schema="opentallas.die_plan.stn_deadlane.v1", plan=str(a.plan),
               plan_sha=hashlib.sha256(Path(a.plan).read_bytes()).hexdigest()[:12],
               rows=box["rows"], findings=[dict(type=k[0], bus=k[1], **v) for k, v in found.items()])
    (out / "stn_deadlane.json").write_text(json.dumps(rep, indent=1) + "\n")
    for (tn, bus), f in found.items():
        print(f"STN-DEADLANE {f['state']} {tn} {bus} parts={','.join(f['dead_parts'] or f['multi_parts'])}"
              f" of {len(f['parts'])}")
    if a.ops:
        doc = ops_for(raw, found, a.row)
        doc["base_sha"] = rep["plan_sha"]
        Path(a.ops).write_text(json.dumps(doc, indent=1) + "\n")
        print(f"STN-DEADLANE ops {a.ops}: {len(doc['ops'])} type(s)")
    print(f"STN-DEADLANE summary: {sum(1 for f in found.values() if f['state'] == 'DEAD-TYPE')} DEAD-TYPE, "
          f"{sum(1 for f in found.values() if f['state'] == 'DEAD-PARTIAL')} DEAD-PARTIAL, "
          f"{sum(1 for f in found.values() if f['state'] == 'MULTI')} MULTI over {len(box['rows'])} rows")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
