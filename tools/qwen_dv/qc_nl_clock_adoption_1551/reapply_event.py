#!/usr/bin/env python3
"""DIE-QC-97 11-09: carry the QC NL clock-pin event (b1bd879f675, qc52 -> qc52n) onto a later QC plan lineage.

The current QC plan (plan_qc53v4nS_mem9_vml, sha 282ca18e) descends from qc52, not qc52n: its NL u_t30 keeps the old
pin table (ck M4 edge), no clock_entry_access and no IDLE_UCK, while the signed NL view has ck on M5 at the core centre
(cbx_q10__cl94a12200 DRT-0073 "No access point for u_bound.u_t30/ck").  This applies the SAME reviewed access_v4 patch
to any base: every 'test' op must hold on the base (same NL pin table, same tap u_t30.ck at the old xy), pins_file is
re-pointed plan-relative (cores/a0_nl_pins_ck1107.json, byte-identical to access_v4/a0_nl_pins.json, already beside the
QC plans), and nothing outside the two cbx_q10 types' NL core and tap changes.  Composes with other type-local events
(the NK event touches other hard cores and taps; a conflicting base fails a 'test' op).

usage: reapply_event.py BASE_PLAN OUT_PLAN [--record OUT_RECORD]"""
import argparse
import copy
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ADO = ROOT / "results/physical/qc_nl_clock_adoption_1551/access_v4"
NEW_PINS = "cores/a0_nl_pins_ck1107.json"
TYPES = ("cbx_q10__cl94a12200", "cbx_q10__cl89936551")
sha = lambda b: hashlib.sha256(b).hexdigest()


def walk(doc, path):
    ks = [k.replace("~1", "/").replace("~0", "~") for k in path.lstrip("/").split("/")]
    for k in ks[:-1]:
        doc = doc[int(k)] if isinstance(doc, list) else doc[k]
    return doc, (int(ks[-1]) if isinstance(doc, list) else ks[-1])


def apply(P, ops):
    N = copy.deepcopy(P)
    for op in ops:
        d, k = walk(N, op["path"])
        v = NEW_PINS if op["path"].endswith("/pins_file") and op["op"] == "replace" else op.get("value")
        if op["op"] == "test":
            if d[k] != v:
                raise ValueError(f"base differs from the reviewed event at {op['path']}: {d[k]!r} != {v!r}")
        elif op["op"] == "add":
            if k in d:
                raise ValueError(f"already present: {op['path']}")
            d[k] = v
        elif op["op"] == "replace":
            if k not in d:
                raise ValueError(f"missing: {op['path']}")
            d[k] = v
        else:
            raise ValueError(op)
    for tk in P["partition_types"]:
        if tk not in TYPES and P["partition_types"][tk] != N["partition_types"][tk]:
            raise ValueError(f"type outside the event changed: {tk}")
    if {k: v for k, v in P.items() if k != "partition_types"} != {k: v for k, v in N.items() if k != "partition_types"}:
        raise ValueError("top-level key changed")
    for tn in TYPES:
        a, b = P["partition_types"][tn], N["partition_types"][tn]
        hc = next(i for i, c in enumerate(a["hard_cores"]) if c.get("module") == "qfd_tile_nl_a0c")
        ti = next(i for i, x in enumerate(a["clock"]["taps"]) if x.get("name") == "u_t30.ck")
        a2, b2 = copy.deepcopy(a), copy.deepcopy(b)
        a2["hard_cores"][hc] = b2["hard_cores"][hc] = a2["clock"]["taps"][ti] = b2["clock"]["taps"][ti] = None
        if a2 != b2:
            raise ValueError(f"{tn}: change outside the NL core and its tap")
    return N


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("base", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--record", type=Path)
    a = ap.parse_args(argv)
    if a.out.exists():
        raise SystemExit(f"{a.out} exists: new output required")
    src = a.base.read_bytes()
    P = json.loads(src)
    ops = json.loads((ADO / "proposed_event.patch.json").read_text())
    N = apply(P, ops)
    pins = a.base.parent / NEW_PINS
    if not pins.is_file() or pins.read_bytes() != (ADO / "a0_nl_pins.json").read_bytes():
        raise SystemExit(f"{pins} missing or differs from access_v4/a0_nl_pins.json")
    if a.out.parent.resolve() != a.base.parent.resolve():
        o = a.out.parent / NEW_PINS
        if not o.is_file() or o.read_bytes() != pins.read_bytes():
            raise SystemExit(f"{o} missing or differs: stage the plan cores/ beside the output first")
    sep = (",", ":") if json.dumps(P, separators=(",", ":")).encode() + b"\n" == src else None
    out = (json.dumps(N, separators=sep) if sep else json.dumps(N, indent=1)).encode() + b"\n"
    a.out.write_bytes(out)
    rec = dict(schema="opentallas.qc_por_event.v1", event="QC NL clock pin adoption (b1bd879f675) carried onto a later lineage (DIE-QC-97 11-09)",
               base_plan=a.base.name, base_plan_sha256=sha(src), plan_output=a.out.name, plan_output_sha256=sha(out),
               types=list(TYPES), module="qfd_tile_nl_a0c", pins_file_new=NEW_PINS, pins_file_new_sha256=sha(pins.read_bytes()),
               patch_source="results/physical/qc_nl_clock_adoption_1551/access_v4/proposed_event.patch.json",
               patch_sha256=sha((ADO / "proposed_event.patch.json").read_bytes()),
               eq_gate="same as qc52n_nl_ck_event.json (signed NL re-sign LEC EQUIVALENT incl IDLE_UCK=1, COORD 11-07 15:23)",
               lef="kit stages the access abstract by construction (gen_phys.stage_clock_entry_lefs, clock_entry_lef.json)",
               preservation="every other partition type, every top-level key and every other entry of the two types byte-identical (checked)")
    if a.record:
        a.record.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(rec, indent=1))


if __name__ == "__main__":
    main()
